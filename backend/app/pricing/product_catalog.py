"""NOVA標準商品庫と店舗別カラー価格の正規化。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
import unicodedata
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.pricing.iphone_lineup import LINEUP

from app.db.models import (
    OfficialProductMapping,
    OfficialStoreProduct,
    Price,
    PriceCollectionSource,
    Product,
    ProductVariant,
    ProductVariantIdentifier,
    Store,
    StoreProductPrice,
)


@dataclass(frozen=True)
class ColorSpec:
    code: str
    ja: str
    en: str
    zh: str
    aliases: tuple[str, ...] = ()


def _color(code: str, ja: str, en: str, zh: str, *aliases: str) -> ColorSpec:
    return ColorSpec(code, ja, en, zh, aliases)


STANDARD_MODEL_COLORS: dict[str, tuple[ColorSpec, ...]] = {
    "iPhone 14": (
        _color("midnight", "ミッドナイト", "Midnight", "午夜色", "midnight", "black", "ブラック", "黑", "黒"),
        _color("starlight", "スターライト", "Starlight", "星光色", "starlight", "white", "ホワイト", "星光"),
        _color("blue", "ブルー", "Blue", "蓝色", "blue", "青", "藍"),
        _color("purple", "パープル", "Purple", "紫色", "purple", "紫"),
        _color("product-red", "(PRODUCT)RED", "(PRODUCT)RED", "红色", "productred", "red", "レッド", "红", "赤"),
        _color("yellow", "イエロー", "Yellow", "黄色", "yellow", "黄"),
    ),
    "iPhone 14 Plus": (),
    "iPhone 14 Pro": (
        _color("space-black", "スペースブラック", "Space Black", "深空黑色", "spaceblack", "black", "ブラック", "深空黑", "黒", "黑"),
        _color("silver", "シルバー", "Silver", "银色", "silver", "银", "銀", "白"),
        _color("gold", "ゴールド", "Gold", "金色", "gold", "金"),
        _color("deep-purple", "ディープパープル", "Deep Purple", "暗紫色", "deeppurple", "purple", "パープル", "深紫", "紫"),
    ),
    "iPhone 14 Pro Max": (),
    "iPhone 15": (
        _color("black", "ブラック", "Black", "黑色", "black", "黒", "黑"),
        _color("blue", "ブルー", "Blue", "蓝色", "blue", "青", "藍"),
        _color("green", "グリーン", "Green", "绿色", "green", "緑", "绿"),
        _color("yellow", "イエロー", "Yellow", "黄色", "yellow", "黄"),
        _color("pink", "ピンク", "Pink", "粉色", "pink", "粉", "桃"),
    ),
    "iPhone 15 Plus": (),
    "iPhone 15 Pro": (
        _color("black-titanium", "ブラックチタニウム", "Black Titanium", "黑色钛金属", "blacktitanium", "black", "ブラック", "黒", "黑"),
        _color("white-titanium", "ホワイトチタニウム", "White Titanium", "白色钛金属", "whitetitanium", "white", "ホワイト", "白"),
        _color("blue-titanium", "ブルーチタニウム", "Blue Titanium", "蓝色钛金属", "bluetitanium", "blue", "ブルー", "青", "蓝"),
        _color("natural-titanium", "ナチュラルチタニウム", "Natural Titanium", "原色钛金属", "naturaltitanium", "natural", "灰"),
    ),
    "iPhone 15 Pro Max": (),
    "iPhone 16": (
        _color("black", "ブラック", "Black", "黑色", "black", "黒", "黑"),
        _color("white", "ホワイト", "White", "白色", "white", "whie", "白"),
        _color("pink", "ピンク", "Pink", "粉色", "pink", "粉", "桃"),
        _color("teal", "ティール", "Teal", "青绿色", "teal", "青緑", "青绿"),
        _color("ultramarine", "ウルトラマリン", "Ultramarine", "群青色", "ultramarine", "群青"),
    ),
    "iPhone 16 Plus": (),
    "iPhone 16 Pro": (
        _color("black-titanium", "ブラックチタニウム", "Black Titanium", "黑色钛金属", "blacktitanium", "black", "ブラック", "黒", "黑"),
        _color("white-titanium", "ホワイトチタニウム", "White Titanium", "白色钛金属", "whitetitanium", "white", "ホワイト", "白"),
        _color("natural-titanium", "ナチュラルチタニウム", "Natural Titanium", "原色钛金属", "naturaltitanium", "natural", "灰"),
        _color("desert-titanium", "デザートチタニウム", "Desert Titanium", "沙漠色钛金属", "deserttitanium", "desert", "デザート", "砂"),
    ),
    "iPhone 16 Pro Max": (),
    "iPhone 16e": (
        _color("black", "ブラック", "Black", "黑色", "black", "黒", "黑"),
        _color("white", "ホワイト", "White", "白色", "white", "whie", "白"),
    ),
    "iPhone 17": (
        _color("black", "ブラック", "Black", "黑色", "black", "黒", "黑"),
        _color("white", "ホワイト", "White", "白色", "white", "whie", "白"),
        _color("mist-blue", "ミストブルー", "Mist Blue", "雾蓝色", "mistblue", "blue", "ブルー", "雾蓝", "霧青"),
        _color("sage", "セージ", "Sage", "鼠尾草绿色", "sage", "green", "グリーン", "鼠尾草"),
        _color("lavender", "ラベンダー", "Lavender", "薰衣草紫色", "lavender", "purple", "パープル", "薰衣草"),
    ),
    "iPhone 17 Air": (
        _color("space-black", "スペースブラック", "Space Black", "深空黑色", "spaceblack", "black", "ブラック", "深空黑", "黒", "黑"),
        _color("cloud-white", "クラウドホワイト", "Cloud White", "云白色", "cloudwhite", "white", "ホワイト", "云白", "白"),
        _color("light-gold", "ライトゴールド", "Light Gold", "浅金色", "lightgold", "gold", "ゴールド", "浅金", "金"),
        _color("sky-blue", "スカイブルー", "Sky Blue", "天蓝色", "skyblue", "blue", "ブルー", "天蓝", "空青"),
    ),
    "iPhone 17 Pro": (
        _color("silver", "シルバー", "Silver", "银色", "silver", "银", "銀", "白"),
        _color("deep-blue", "ディープブルー", "Deep Blue", "深蓝色", "deepblue", "blue", "ブルー", "深蓝", "青"),
        _color("cosmic-orange", "コズミックオレンジ", "Cosmic Orange", "星宇橙色", "cosmicorange", "orange", "オレンジ", "橙"),
    ),
    "iPhone 17 Pro Max": (),
    "iPhone 17e": (
        _color("black", "ブラック", "Black", "黑色", "black", "黒", "黑"),
        _color("white", "ホワイト", "White", "白色", "white", "whie", "白"),
        _color("soft-pink", "ソフトピンク", "Soft Pink", "柔粉色", "softpink", "pink", "ピンク", "粉", "桃"),
    ),
}

# 同じ世代・同じシリーズのカラーを共有する機種。
STANDARD_MODEL_COLORS["iPhone 14 Plus"] = STANDARD_MODEL_COLORS["iPhone 14"]
STANDARD_MODEL_COLORS["iPhone 14 Pro Max"] = STANDARD_MODEL_COLORS["iPhone 14 Pro"]
STANDARD_MODEL_COLORS["iPhone 15 Plus"] = STANDARD_MODEL_COLORS["iPhone 15"]
STANDARD_MODEL_COLORS["iPhone 15 Pro Max"] = STANDARD_MODEL_COLORS["iPhone 15 Pro"]
STANDARD_MODEL_COLORS["iPhone 16 Plus"] = STANDARD_MODEL_COLORS["iPhone 16"]
STANDARD_MODEL_COLORS["iPhone 16 Pro Max"] = STANDARD_MODEL_COLORS["iPhone 16 Pro"]
STANDARD_MODEL_COLORS["iPhone 17 Pro Max"] = STANDARD_MODEL_COLORS["iPhone 17 Pro"]
for _model in LINEUP["models"]:
    STANDARD_MODEL_COLORS[_model["name"]] = tuple(
        _color(color["code"], color["ja"], color["en"], color["zh"], *color["aliases"])
        for color in LINEUP["colors"]
    )
MATCHER_VERSION = "catalog-v2"
PRICE_INDEX_LOCK_ID = 7_841_700_021


def acquire_price_index_lock(db: Session) -> None:
    """標準価格索引の入れ替えをPostgreSQL上で直列化する。"""
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": PRICE_INDEX_LOCK_ID},
        )


def normalize_capacity(value: str | None) -> str:
    text = str(value or "").strip().upper().replace(" ", "")
    if text in {"1024", "1024GB"}:
        return "1TB"
    if text in {"2048", "2048GB"}:
        return "2TB"
    if text.endswith("GB") and text[:-2].isdigit():
        return text[:-2]
    return text


def _compact(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"[\s\-_/()\[\]{}（）【】・.]", "", text)


def infer_color_code(model: str, product_name: str) -> str | None:
    """店舗の商品名から、その機種で有効な標準カラーを返す。"""
    compact = _compact(product_name)
    candidates: list[tuple[int, str]] = []
    for spec in STANDARD_MODEL_COLORS.get(model, ()):
        aliases = (spec.ja, spec.en, spec.zh, spec.code, *spec.aliases)
        for alias in aliases:
            normalized = _compact(alias)
            if normalized and normalized in compact:
                candidates.append((len(normalized), spec.code))
    if not candidates:
        return None
    # 「ブルー」より「ディープブルー」のように、長い一致を優先する。
    return max(candidates)[1]


def infer_offer_condition(product_name: str) -> str:
    """公式商品名から、表示用の開封状態を失わず取り出す。"""
    text = unicodedata.normalize("NFKC", str(product_name or "")).lower()
    if any(token in text for token in ("未開封", "未开封", "unopened", "sealed")):
        return "unopened"
    if any(token in text for token in ("開封済", "開封", "开封", "opened", "open box")):
        return "opened"
    if any(token in text for token in ("新品", "new")):
        return "new"
    return "unspecified"


def _jan_candidates(value: str | None) -> tuple[str, ...]:
    """商品名やJAN欄から、重複しない13桁JAN候補を抽出する。"""
    candidates = re.findall(r"(?<!\d)\d{13}(?!\d)", unicodedata.normalize("NFKC", str(value or "")))
    return tuple(dict.fromkeys(candidates))


def _apple_part_numbers(value: str | None) -> tuple[str, ...]:
    """Appleの国内型番（例: MFY94J/A）を正規化して抽出する。"""
    text = unicodedata.normalize("NFKC", str(value or "")).upper()
    candidates = re.findall(r"(?<![A-Z0-9])([A-Z0-9]{4,12}J/A)(?![A-Z0-9])", text)
    return tuple(dict.fromkeys(candidates))


def _base_products(db: Session) -> dict[tuple[str, str], Product]:
    result: dict[tuple[str, str], Product] = {}
    rows = db.query(Product).filter(Product.model.like("iPhone%"), Product.condition == "新品").all()
    for product in rows:
        model = " ".join(product.model.split())
        capacity = normalize_capacity(product.capacity)
        if model not in STANDARD_MODEL_COLORS or not capacity:
            continue
        key = (model, capacity)
        current = result.get(key)
        if current is None or (current.color and not product.color):
            result[key] = product
    return result


def ensure_standard_variants(
    db: Session, catalog_items: Iterable[object] = (), *, models: set[str] | None = None,
) -> dict[tuple[int, str], ProductVariant]:
    """標準カラー商品を不足分だけ作り、取得済みJANを一度だけ記録する。"""
    catalog_items = list(catalog_items)
    products = _base_products(db)
    if models is not None:
        products = {key: product for key, product in products.items() if key[0] in models}
    for item in catalog_items:
        model = " ".join(str(getattr(item, "model", "") or "").split())
        capacity = normalize_capacity(getattr(item, "capacity", ""))
        if models is not None and model not in models:
            continue
        if model not in STANDARD_MODEL_COLORS or not capacity or (model, capacity) in products:
            continue
        product = Product(
            name=f"{model} {capacity}",
            brand="Apple",
            model=model,
            capacity=capacity,
            color="",
            carrier="SIMフリー",
            condition="新品",
        )
        db.add(product)
        db.flush()
        products[(model, capacity)] = product

    existing = {
        (row.product_id, row.color_code): row
        for row in db.query(ProductVariant).all()
    }
    for (model, _capacity), product in products.items():
        for order, spec in enumerate(STANDARD_MODEL_COLORS[model]):
            key = (product.id, spec.code)
            if key in existing:
                continue
            variant = ProductVariant(
                product_id=product.id,
                color_code=spec.code,
                color_name_ja=spec.ja,
                color_name_en=spec.en,
                color_name_zh=spec.zh,
                sort_order=order,
            )
            db.add(variant)
            existing[key] = variant
    db.flush()

    rows = list(db.query(OfficialStoreProduct).filter(OfficialStoreProduct.jan_code.is_not(None)).all())
    rows.extend(catalog_items)
    jan_owner = {
        row.jan_code: row
        for row in db.query(ProductVariant).filter(ProductVariant.jan_code.is_not(None)).all()
    }
    for item in rows:
        jan_code = re.sub(r"\D", "", str(getattr(item, "jan_code", "") or ""))
        if len(jan_code) != 13:
            continue
        product = products.get((
            " ".join(str(getattr(item, "model", "") or "").split()),
            normalize_capacity(getattr(item, "capacity", "")),
        ))
        if not product:
            continue
        color_code = infer_color_code(product.model, str(getattr(item, "product_name", "") or ""))
        variant = existing.get((product.id, color_code or ""))
        if not variant or jan_code in jan_owner:
            continue
        if not variant.jan_code:
            variant.jan_code = jan_code
            jan_owner[jan_code] = variant
    db.flush()
    return existing


def rebuild_product_variant_identifiers(db: Session) -> dict[str, int]:
    """標準JANと、公式商品から確定できるApple型番索引を作る。"""
    variants = list(db.query(ProductVariant).all())
    variants_by_jan = {variant.jan_code: variant for variant in variants if variant.jan_code}
    identifiers = {
        (row.identifier_type, row.identifier_value): row
        for row in db.query(ProductVariantIdentifier).all()
    }
    created_jan = 0
    created_part_number = 0
    conflicts = 0

    for variant in variants:
        if not variant.jan_code:
            continue
        key = ("jan", variant.jan_code)
        current = identifiers.get(key)
        if current and current.product_variant_id != variant.id:
            conflicts += 1
            continue
        if current:
            continue
        identifier = ProductVariantIdentifier(
            product_variant_id=variant.id,
            identifier_type="jan",
            identifier_value=variant.jan_code,
            source="variant_catalog",
        )
        db.add(identifier)
        identifiers[key] = identifier
        created_jan += 1

    # Apple型番は、同じ行に確定JANがある場合だけ自動学習する。
    for row in db.query(OfficialStoreProduct).filter(OfficialStoreProduct.jan_code.is_not(None)).all():
        jan_candidates = _jan_candidates(row.jan_code)
        matched_variants = {variants_by_jan[jan].id: variants_by_jan[jan] for jan in jan_candidates if jan in variants_by_jan}
        if len(matched_variants) != 1:
            continue
        variant = next(iter(matched_variants.values()))
        for part_number in _apple_part_numbers(row.product_name):
            key = ("apple_part_number", part_number)
            current = identifiers.get(key)
            if current and current.product_variant_id != variant.id:
                conflicts += 1
                continue
            if current:
                continue
            identifier = ProductVariantIdentifier(
                product_variant_id=variant.id,
                identifier_type="apple_part_number",
                identifier_value=part_number,
                source="official_jan",
            )
            db.add(identifier)
            identifiers[key] = identifier
            created_part_number += 1
    db.flush()
    return {
        "jan_identifiers_created": created_jan,
        "part_number_identifiers_created": created_part_number,
        "identifier_conflicts": conflicts,
    }


def rebuild_official_product_mappings(db: Session, store_id: int | None = None) -> dict[str, int]:
    """公式商品を標準カラー商品へ永続的に対応付ける。

    JANがある商品はJANを最優先し、JANが商品名に含まれる場合も利用する。
    カラー名がある商品は三言語の別名で対応し、カラー明細がない商品は
    その機種・容量の全カラーへ同一価格として展開する。
    """
    variants = ensure_standard_variants(db)
    identifier_detail = rebuild_product_variant_identifiers(db)
    products = _base_products(db)
    variant_rows = list(variants.values())
    variants_by_jan = {row.jan_code: row for row in variant_rows if row.jan_code}
    variants_by_part_number = {
        identifier.identifier_value: db.get(ProductVariant, identifier.product_variant_id)
        for identifier in db.query(ProductVariantIdentifier).filter(
            ProductVariantIdentifier.identifier_type == "apple_part_number",
        ).all()
    }
    variants_by_product: dict[int, list[ProductVariant]] = {}
    for variant in variant_rows:
        variants_by_product.setdefault(variant.product_id, []).append(variant)
    for rows in variants_by_product.values():
        rows.sort(key=lambda row: (row.sort_order, row.id))

    official_query = db.query(OfficialStoreProduct)
    if store_id is not None:
        official_query = official_query.filter(OfficialStoreProduct.store_id == store_id)
    official_rows = official_query.order_by(OfficialStoreProduct.id.asc()).all()
    official_ids = [row.id for row in official_rows]
    if official_ids:
        db.query(OfficialProductMapping).filter(
            OfficialProductMapping.official_product_id.in_(official_ids),
        ).delete(synchronize_session=False)

    mapped_sources = 0
    variant_mappings = 0
    default_sources = 0
    unmapped_sources = 0
    method_counts: dict[str, int] = {}
    for row in official_rows:
        model = " ".join(str(row.model or "").split())
        capacity = normalize_capacity(row.capacity)
        product = products.get((model, capacity))

        source_jans = _jan_candidates(row.jan_code)
        source_variants = [variants_by_jan[jan] for jan in source_jans if jan in variants_by_jan]
        method = "jan" if source_variants else ""
        if not source_variants:
            embedded_jans = _jan_candidates(row.product_name)
            source_variants = [variants_by_jan[jan] for jan in embedded_jans if jan in variants_by_jan]
            if source_variants:
                method = "embedded_jan"
        if not source_variants:
            part_numbers = _apple_part_numbers(row.product_name)
            source_variants = [
                variants_by_part_number[part_number]
                for part_number in part_numbers
                if variants_by_part_number.get(part_number) is not None
            ]
            if source_variants:
                method = "apple_part_number"
        if source_variants:
            # JANは名称より信頼できるため、JAN側の標準商品を採用する。
            product = db.get(Product, source_variants[0].product_id)
        elif product:
            color_code = infer_color_code(product.model, row.product_name)
            color_variant = variants.get((product.id, color_code or ""))
            if color_variant:
                source_variants = [color_variant]
                method = "color_name"
            else:
                source_variants = variants_by_product.get(product.id, [])
                method = "all_colors"

        # 同じJANが名称と専用欄の両方にある場合も1商品として扱う。
        unique_variants = {variant.id: variant for variant in source_variants}
        source_variants = list(unique_variants.values())
        if not product or not source_variants:
            unmapped_sources += 1
            continue

        is_default = method == "all_colors"
        confidence = {
            "jan": 100,
            "embedded_jan": 100,
            "apple_part_number": 98,
            "color_name": 90,
            "all_colors": 70,
        }[method]
        offer_condition = infer_offer_condition(row.product_name)
        for variant in source_variants:
            db.add(OfficialProductMapping(
                official_product_id=row.id,
                product_id=variant.product_id,
                product_variant_id=variant.id,
                mapping_method=method,
                confidence=confidence,
                matcher_version=MATCHER_VERSION,
                offer_condition=offer_condition,
                is_default_color_price=1 if is_default else 0,
            ))
            variant_mappings += 1
        mapped_sources += 1
        default_sources += 1 if is_default else 0
        method_counts[method] = method_counts.get(method, 0) + 1
    db.flush()
    return {
        "source_products": len(official_rows),
        "mapped_source_products": mapped_sources,
        "variant_mappings": variant_mappings,
        "default_source_products": default_sources,
        "unmapped_source_products": unmapped_sources,
        **identifier_detail,
        **{f"mapping_{method}": count for method, count in sorted(method_counts.items())},
    }


def normalize_official_store_prices(
    db: Session,
    *,
    store: Store,
    run_id: int,
    items: Iterable[object],
    collected_at: datetime,
    replace: bool,
) -> dict[str, int]:
    """公式取得行を標準商品へ対応付け、現在価格として保存する。"""
    if not replace:
        return {"normalized_prices_saved": 0, "colored_prices_saved": 0, "default_prices_saved": 0}

    # 呼び出し互換性のためitemsを受け取るが、正規化元は永続マッピングに統一する。
    list(items)
    db.query(StoreProductPrice).filter(
        StoreProductPrice.store_id == store.id,
        StoreProductPrice.source_type == "official",
    ).delete(synchronize_session=False)

    mapping_rows = db.query(OfficialProductMapping, OfficialStoreProduct).join(
        OfficialStoreProduct,
        OfficialStoreProduct.id == OfficialProductMapping.official_product_id,
    ).filter(
        OfficialStoreProduct.store_id == store.id,
    ).all()
    selected: dict[tuple[int, int | None], tuple[OfficialProductMapping, OfficialStoreProduct]] = {}
    for mapping, item in mapping_rows:
        variant_id = None if mapping.is_default_color_price else mapping.product_variant_id
        key = (mapping.product_id, variant_id)
        current = selected.get(key)
        if current is None or item.price > current[1].price:
            selected[key] = (mapping, item)

    colored = 0
    defaults = 0
    for mapping, item in selected.values():
        variant_id = None if mapping.is_default_color_price else mapping.product_variant_id
        db.add(StoreProductPrice(
            store_id=store.id,
            product_id=mapping.product_id,
            product_variant_id=variant_id,
            source_type="official",
            price=item.price,
            source_name=item.product_name,
            source_url=item.source_url,
            run_id=run_id,
            collected_at=collected_at,
        ))
        if variant_id:
            colored += 1
        else:
            defaults += 1
    return {
        "normalized_prices_saved": len(selected),
        "colored_prices_saved": colored,
        "default_prices_saved": defaults,
    }


def rebuild_standard_price_index(db: Session) -> dict[str, int]:
    """既存の公式商品スナップショットと表価格から標準価格表を再構築する。"""
    acquire_price_index_lock(db)
    ensure_standard_variants(db)
    mapping_detail = rebuild_official_product_mappings(db)
    db.query(StoreProductPrice).delete(synchronize_session=False)

    official_saved = 0
    store_ids = [row[0] for row in db.query(OfficialStoreProduct.store_id).distinct().all()]
    for store_id in store_ids:
        store = db.get(Store, store_id)
        rows = db.query(OfficialStoreProduct).filter(OfficialStoreProduct.store_id == store_id).all()
        if not store or not rows:
            continue
        latest = max(rows, key=lambda row: row.collected_at)
        detail = normalize_official_store_prices(
            db,
            store=store,
            run_id=latest.run_id,
            items=rows,
            collected_at=latest.collected_at,
            replace=True,
        )
        official_saved += detail["normalized_prices_saved"]

    sheet_rows = db.query(Price, PriceCollectionSource).join(
        PriceCollectionSource, PriceCollectionSource.price_id == Price.id
    ).filter(
        PriceCollectionSource.source_type == "sheet",
    ).order_by(
        PriceCollectionSource.collected_at.desc(),
        Price.id.desc(),
    ).all()
    seen: set[tuple[int, int]] = set()
    sheet_saved = 0
    for price, source in sheet_rows:
        key = (price.store_id, price.product_id)
        if key in seen:
            continue
        seen.add(key)
        db.add(StoreProductPrice(
            store_id=price.store_id,
            product_id=price.product_id,
            product_variant_id=None,
            source_type="sheet",
            price=price.price,
            source_name="Google Sheets",
            source_url=source.source_url or price.url,
            run_id=source.run_id,
            collected_at=source.collected_at or price.scraped_at,
        ))
        sheet_saved += 1
    db.commit()
    return {
        "official": official_saved,
        "sheet": sheet_saved,
        "official_product_mappings": mapping_detail["variant_mappings"],
        "unmapped_official_products": mapping_detail["unmapped_source_products"],
    }
