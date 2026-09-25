"""Question preprocessing for NOVA AI.

Everything here is deterministic: it reads the current prices from the
database, recognises model / capacity / quantity in the question and selects
the price rows the AI core needs.  Wording and model calls live in the core.
"""

import re

from sqlalchemy.orm import Session

from app.ai_gateway.core import AIRequest
from app.db.store_metadata import get_store_metadata
from app.pricing.current_prices import latest_prices_query
from app.pricing.iphone_lineup import lineup_context
from app.pricing.market_average import build_market_average_batch


def build_price_context(db: Session) -> list:
    prices = latest_prices_query(db).all()
    market_by_product = {
        item["product_id"]: item
        for item in build_market_average_batch(
            db,
            product_ids=sorted({p.product_id for p in prices}),
        )
    }
    accepted_store_ids = {
        product_id: {price["store_id"] for price in market.get("accepted_prices", [])}
        for product_id, market in market_by_product.items()
    }

    data = []
    for p in prices:
        market = market_by_product.get(p.product_id) or {}
        accepted_ids = accepted_store_ids.get(p.product_id)
        if accepted_ids and p.store_id not in accepted_ids:
            continue
        data.append({
            "product": p.product.name,
            "model": p.product.model,
            "capacity": p.product.capacity,
            "store": p.store.name,
            "price": p.price,
            "profit": p.profit,
            "retail_price": p.product.retail_price,
            "market_average": market.get("market_average"),
            "market_median": market.get("median_price"),
            "market_confidence": market.get("confidence_label"),
            "market_store_count": market.get("accepted_store_count"),
            "market_spread": market.get("spread"),
            "store_url": p.store.website_url or get_store_metadata(p.store.name).get("website_url"),
            "store_phone": get_store_metadata(p.store.name).get("phone"),
            "store_address": get_store_metadata(p.store.name).get("address"),
            "store_summary": get_store_metadata(p.store.name).get("summary"),
            "is_sponsored": get_store_metadata(p.store.name).get("is_sponsored", False),
        })

    return data


def build_simple_price_context(db: Session) -> list:
    prices = latest_prices_query(db).all()
    market_by_product = {
        item["product_id"]: item
        for item in build_market_average_batch(
            db,
            product_ids=sorted({p.product_id for p in prices}),
        )
    }
    accepted_store_ids = {
        product_id: {price["store_id"] for price in market.get("accepted_prices", [])}
        for product_id, market in market_by_product.items()
    }

    grouped: dict[str, dict] = {}
    for p in prices:
        accepted_ids = accepted_store_ids.get(p.product_id)
        if accepted_ids and p.store_id not in accepted_ids:
            continue
        model = p.product.model if p.product else None
        capacity = p.product.capacity if p.product and p.product.capacity else None
        product_label = f"{model} {capacity}".strip() if model else None
        store_name = p.store.name if p.store else None
        if not product_label or not store_name:
            continue
        grouped.setdefault(product_label, {"product_id": p.product_id, "items": []})
        grouped[product_label]["items"].append((store_name, p.price))

    data = []
    for product_label, payload in grouped.items():
        items = payload["items"]
        top5 = sorted(items, key=lambda item: item[1], reverse=True)[:5]
        compact = ",".join(f"{store}:{price}" for store, price in top5)
        market = market_by_product.get(payload["product_id"])
        if market and market.get("market_average"):
            compact = (
                f"{compact},市場平均:{market.get('market_average')},"
                f"中央値:{market.get('median_price')},信頼:{market.get('confidence_label')}"
            )
        data.append(f"{product_label}:[{compact}]")
    return data


def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("promax", "pro max")
    text = re.sub(r"iphone\s*(\d{2})", r"iphone \1", text)
    text = re.sub(r"(\d)\s*tb", lambda m: f"{int(m.group(1)) * 1024}gb", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_capacity(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip().lower().replace(" ", "")
    if text.endswith("tb"):
        tb = text[:-2]
        if tb.isdigit():
            return str(int(tb) * 1024)
    if text.endswith("gb"):
        text = text[:-2]
    if text.isdigit():
        return text
    return None


def extract_variant(text: str) -> str | None:
    if "pro max" in text:
        return "pro max"
    if "plus" in text:
        return "plus"
    if "mini" in text:
        return "mini"
    if re.search(r"\bpro\b", text):
        return "pro"
    if re.search(r"\be\b", text):
        return "e"
    return None


def extract_generation(text: str) -> str | None:
    match = re.search(r"(?:iphone\s*)?(\d{2})", text)
    return match.group(1) if match else None


def extract_capacity(text: str) -> str | None:
    match = re.search(r"\b(128|256|512|1024|2048)\s*(?:gb)?\b", text)
    if match:
        return normalize_capacity(match.group(1))
    match = re.search(r"\b(1|2)\s*tb\b", text)
    if match:
        return normalize_capacity(f"{match.group(1)}tb")
    return None


def item_matches_spec(item: dict, generation: str | None, variant: str | None, capacity: str | None) -> bool:
    model = normalize_text(str(item.get("model") or item.get("product") or ""))
    item_generation = extract_generation(model)
    item_variant = extract_variant(model)
    item_capacity = normalize_capacity(item.get("capacity"))

    if generation and item_generation != generation:
        return False
    if variant:
        if variant == "pro" and item_variant != "pro":
            return False
        if variant != "pro" and item_variant != variant:
            return False
    if capacity and item_capacity != capacity:
        return False
    return True


def parse_bulk_request(message: str) -> list[dict]:
    text = normalize_text(message)
    pattern = re.compile(
        r"(?:iphone\s*)?(\d{2})\s*(pro max|pro|plus|mini|e)?\s*(128|256|512|1024|2048|1tb|2tb)?\s*(?:gb)?\s*[*x×]\s*(\d+)",
        re.I,
    )
    items = []
    for generation, variant, capacity, quantity in pattern.findall(text):
        items.append(
            {
                "generation": generation,
                "variant": (variant or "").strip().lower() or None,
                "capacity": normalize_capacity(capacity),
                "quantity": int(quantity),
            }
        )
    return items


def build_focused_simple_price_data(message: str, full_price_data: list[dict], fallback_price_data: list[dict]) -> list[dict]:
    bulk_items = parse_bulk_request(message)
    if bulk_items:
        grouped: dict[str, list[tuple[str, int]]] = {}
        seen = set()
        for spec in bulk_items:
            for item in full_price_data:
                if item_matches_spec(
                    item,
                    spec.get("generation"),
                    spec.get("variant"),
                    spec.get("capacity"),
                ):
                    key = (
                        item.get("model"),
                        item.get("capacity"),
                        item.get("store"),
                        item.get("price"),
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    product_label = f"{item.get('model')} {item.get('capacity')}".strip()
                    store_name = item.get("store")
                    price = int(item.get("price") or 0)
                    if product_label and store_name:
                        grouped.setdefault(product_label, [])
                        grouped[product_label].append((store_name, price))
        if grouped:
            data = []
            for product_label, items in grouped.items():
                top5 = sorted(items, key=lambda item: item[1], reverse=True)[:5]
                compact = ",".join(f"{store}:{price}" for store, price in top5)
                data.append(f"{product_label}:[{compact}]")
            return data

    grouped: dict[str, list[tuple[str, int]]] = {}
    for item in fallback_price_data:
        model = item.get("model")
        capacity = item.get("capacity")
        product_label = f"{model} {capacity}".strip() if model else item.get("product")
        store_name = item.get("store")
        price = int(item.get("price") or 0)
        if not product_label or not store_name:
            continue
        grouped.setdefault(product_label, [])
        grouped[product_label].append((store_name, price))
    data = []
    for product_label, items in grouped.items():
        top5 = sorted(items, key=lambda item: item[1], reverse=True)[:5]
        compact = ",".join(f"{store}:{price}" for store, price in top5)
        data.append(f"{product_label}:[{compact}]")
    return data


def quote_bulk_request(message: str, full_price_data: list[dict]) -> dict | None:
    """Price "model × quantity" requests at the best store for each model."""
    bulk_items = parse_bulk_request(message)
    if not bulk_items:
        return None

    rows = []
    grand_total = 0
    for spec in bulk_items:
        matches = [
            item for item in full_price_data
            if item_matches_spec(
                item,
                spec.get("generation"),
                spec.get("variant"),
                spec.get("capacity"),
            )
        ]
        if not matches:
            continue
        best = max(matches, key=lambda item: int(item.get("price") or 0))
        quantity = int(spec.get("quantity") or 1)
        unit_price = int(best.get("price") or 0)
        subtotal = unit_price * quantity
        grand_total += subtotal
        product_label = f"{best.get('model')} {best.get('capacity')}".strip()
        rows.append(
            {
                "product": product_label,
                "store": best.get("store"),
                "unit_price": unit_price,
                "quantity": quantity,
                "subtotal": subtotal,
            }
        )

    if not rows:
        return None
    return {"rows": rows, "total": grand_total}


def is_catalog_question(message: str) -> bool:
    text = normalize_text(message)
    patterns = [
        r"iphone.*(有什么种类|有哪些种类|有哪些型号|有哪些款|种类|型号)",
        r"iphone.*(種類|型番|モデル|ラインナップ)",
        r"what.*types of iphone",
        r"iphone.*(types|models|lineup)",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def build_catalog_context(price_data: list[dict]) -> list[dict]:
    catalog = {}
    for item in price_data:
        model = item.get("model")
        if not model:
            continue
        model_entry = catalog.setdefault(model, {"capacities": set(), "stores": set()})
        if item.get("capacity"):
            model_entry["capacities"].add(str(item.get("capacity")))
        if item.get("store"):
            model_entry["stores"].add(str(item.get("store")))

    rows = []
    for model, data in sorted(catalog.items()):
        rows.append(
            {
                "model": model,
                "capacities": sorted(data["capacities"], key=lambda x: int(normalize_capacity(x) or 0)),
                "store_count": len(data["stores"]),
            }
        )
    return rows


def filter_price_context_for_message(message: str, price_data: list[dict], session_history: list[dict] | None = None) -> list[dict]:
    history_text = " ".join(
        item.get("content", "")
        for item in (session_history or [])
        if item.get("role") == "user" and item.get("content")
    )
    text = normalize_text(f"{history_text} {message}")
    generation = extract_generation(text)
    variant = extract_variant(text)
    capacity = extract_capacity(text)

    if not generation and not variant and not capacity:
        return price_data

    filtered = []
    for item in price_data:
        if item_matches_spec(item, generation, variant, capacity):
            filtered.append(item)

    return filtered or price_data


def requires_local_price_context(message: str, session_history: list[dict] | None = None) -> bool:
    recent_user_text = " ".join(
        str(item.get("content") or "")
        for item in (session_history or [])[-4:]
        if item.get("role") == "user"
    )
    text = normalize_text(f"{recent_user_text} {message}")
    price_patterns = [
        r"价格|价钱|报价|回收|店铺|哪家|均价|中位价|利润|合计|多少钱|卖|出售|出手",
        r"価格|買取|店舗|相場|平均|中央値|利益|合計|いくら|何円|売却|売る|売り|売れ|手放|下取り",
        r"buyback|trade[ -]?in|price|quote|store|shop|market average|median|profit|worth|sell|selling|resale",
    ]
    return any(re.search(pattern, text, re.I) for pattern in price_patterns)


def detect_language(text: str) -> str:
    if re.search(r"[぀-ヿ]", text):
        return "ja"
    if re.search(r"[一-鿿]", text):
        return "zh"
    return "en"


def resolve_response_language(preferred_language: str | None, message: str, conversation_history: list[dict]) -> str:
    if preferred_language in {"zh", "ja", "en"}:
        return preferred_language

    detected = detect_language(message)
    if detected:
        return detected

    for item in reversed(conversation_history):
        content = item.get("content")
        if not content:
            continue
        detected = detect_language(str(content))
        if detected:
            return detected

    return "en"


def prepare_request(
    db: Session,
    message: str,
    preferred_language: str | None,
    conversation_history: list[dict],
) -> AIRequest:
    """Turn one user question into the data package sent to the AI core."""
    full_price_data = build_price_context(db)
    matched_price_data = filter_price_context_for_message(message, full_price_data, conversation_history)
    return AIRequest(
        message=message,
        language=resolve_response_language(preferred_language, message, conversation_history),
        message_language=detect_language(message),
        history=list(conversation_history),
        price_rows=full_price_data,
        matched_rows=matched_price_data,
        price_lines=build_simple_price_context(db),
        focused_price_lines=build_focused_simple_price_data(message, full_price_data, matched_price_data),
        price_context_required=requires_local_price_context(message, conversation_history),
        catalog=build_catalog_context(full_price_data),
        catalog_question=is_catalog_question(message),
        bulk_quote=quote_bulk_request(message, full_price_data),
        lineup=lineup_context(),
    )
