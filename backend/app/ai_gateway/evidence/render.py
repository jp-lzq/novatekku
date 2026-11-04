"""Short text lines that state the price evidence in the answer language.

The AI core can put these lines into its prompt as-is, and the same text is
shown to admins in the preview endpoint.  Every number comes straight from
build_price_evidence(); nothing is rounded beyond yen.
"""

from __future__ import annotations

LABELS = {
    "ja": {
        "best": "最高", "runner_up": "2位", "stores": "{n}店", "retail": "定価比", "week": "7日前比",
        "month": "30日前比", "slope": "傾き {value}/週", "up": "上昇", "down": "下落", "flat": "横ばい",
        "hk": "香港", "us": "アメリカ", "vs_japan": "日本比", "total": "合計", "phones": "{n}台",
        "single_store": "1店でまとめて売るなら {store} {total}",
        "unknown_model": "{model}: NOVA の対象外の機種です",
        "no_prices": "{model}: 現在この機種の買取価格はありません",
        "capacity_not_quoted": "{model} {capacity}: この容量の価格はありません（他の容量を表示）",
        "follow_up": "前の質問の機種で {capacity} を答えてください",
        "excluded": "{model} ×{n} は容量が分からないため合計に含めていません",
        "excluded_no_price": "{model} ×{n} は価格がないため合計に含めていません",
        "excluded_capacity": "{model} {capacity} ×{n} はこの容量の価格がないため合計に含めていません",
        "not_shown": "ほかに {models} もありますが、一度に扱うのは 4 機種までです",
    },
    "zh": {
        "best": "最高", "runner_up": "第2", "stores": "{n}家店", "retail": "比官网价", "week": "比7天前",
        "month": "比30天前", "slope": "每周 {value}", "up": "上涨", "down": "下跌", "flat": "持平",
        "hk": "香港", "us": "美国", "vs_japan": "比日本", "total": "合计", "phones": "{n}台",
        "single_store": "全部卖给一家店的话 {store} {total}",
        "unknown_model": "{model}：不在 NOVA 的收录范围内",
        "no_prices": "{model}：目前没有这个机型的回收价",
        "capacity_not_quoted": "{model} {capacity}：这个容量没有报价（列出其他容量）",
        "follow_up": "请按上一个问题的机型回答 {capacity}",
        "excluded": "{model} ×{n} 因为不知道容量，没有算进合计",
        "excluded_no_price": "{model} ×{n} 没有报价，没有算进合计",
        "excluded_capacity": "{model} {capacity} ×{n} 这个容量没有报价，没有算进合计",
        "not_shown": "还有 {models}，一次最多处理 4 个机型",
    },
    "en": {
        "best": "best", "runner_up": "2nd", "stores": "{n} stores", "retail": "vs Apple price", "week": "vs 7 days ago",
        "month": "vs 30 days ago", "slope": "slope {value}/week", "up": "rising", "down": "falling", "flat": "flat",
        "hk": "Hong Kong", "us": "United States", "vs_japan": "vs Japan", "total": "total", "phones": "{n} phones",
        "single_store": "selling everything to one store: {store} {total}",
        "unknown_model": "{model}: not a model NOVA covers",
        "no_prices": "{model}: no buyback price for this model right now",
        "capacity_not_quoted": "{model} {capacity}: no price for this capacity (other capacities listed)",
        "follow_up": "answer {capacity} for the model of the previous question",
        "excluded": "{model} ×{n} is not in the total because its capacity is unknown",
        "excluded_no_price": "{model} ×{n} is not in the total because it has no price",
        "excluded_capacity": "{model} {capacity} ×{n} is not in the total because that capacity has no price",
        "not_shown": "also asked: {models}; at most 4 models are handled at once",
    },
}

CURRENCY_SIGN = {"JPY": "¥", "HKD": "HK$", "USD": "$"}


def yen(value: int | None, signed: bool = False) -> str:
    if value is None:
        return "-"
    sign = ("+" if value > 0 else "-" if value < 0 else "±") if signed else ("-" if value < 0 else "")
    return f"{sign}¥{abs(int(value)):,}"


def money(value: int | None, currency: str) -> str:
    if value is None:
        return "-"
    return f"{CURRENCY_SIGN.get(currency, currency + ' ')}{int(value):,}"


def percent(value: float | None) -> str:
    return "" if value is None else f" ({value:+.1f}%)"


def capacity_label(capacity: str) -> str:
    return f"{capacity}GB" if capacity.isdigit() else capacity


def _quote_line(model: str, entry: dict, text: dict) -> str:
    quotes = entry.get("quotes") or {}
    parts = [f"{model} {capacity_label(entry['capacity'])}:"]
    if quotes.get("best_price"):
        parts.append(f"{text['best']} {yen(quotes['best_price'])} ({quotes['best_store']})")
        if quotes.get("runner_up_price"):
            parts.append(f"{text['runner_up']} {yen(quotes['runner_up_price'])}")
        parts.append(text["stores"].format(n=quotes["store_count"]))
        if quotes.get("best_vs_retail") is not None:
            parts.append(f"{text['retail']} {yen(quotes['best_vs_retail'], True)}{percent(quotes.get('best_vs_retail_percent'))}")
    trend = entry.get("trend") or {}
    if trend.get("change_7d"):
        change = trend["change_7d"]
        parts.append(f"{text['week']} {yen(change['change'], True)}{percent(change['percent'])} {text.get(trend['direction'], '')}".rstrip())
    if trend.get("change_30d"):
        change = trend["change_30d"]
        parts.append(f"{text['month']} {yen(change['change'], True)}{percent(change['percent'])}")
    if trend.get("slope_per_week") is not None:
        parts.append(text["slope"].format(value=yen(trend["slope_per_week"], True)))
    for market in entry.get("overseas") or []:
        line = f"{text[market['market']]} {money(market['price'], market['currency'])}"
        if market.get("price_jpy") is not None:
            line += f" = {yen(market['price_jpy'])}"
        if market.get("vs_japan") is not None:
            line += f" {text['vs_japan']} {yen(market['vs_japan'], True)}{percent(market.get('vs_japan_percent'))}"
        parts.append(line)
    return " / ".join([parts[0] + " " + parts[1]] + parts[2:]) if len(parts) > 1 else parts[0]


def render_evidence(evidence: dict, language: str = "ja") -> list[str]:
    text = LABELS.get(language, LABELS["en"])
    lines: list[str] = []
    for item in evidence.get("items") or []:
        notes = item.get("notes") or []
        if "unknown_model" in notes or "no_prices" in notes:
            key = "unknown_model" if "unknown_model" in notes else "no_prices"
            lines.append(text[key].format(model=item["model"]))
            continue
        if "capacity_not_quoted" in notes and item.get("requested_capacity"):
            lines.append(text["capacity_not_quoted"].format(model=item["model"],
                                                            capacity=capacity_label(item["requested_capacity"])))
        for entry in item.get("capacities") or []:
            lines.append(_quote_line(item["model"], entry, text))
    bulk = evidence.get("bulk")
    if bulk:
        line = f"{text['total']} {yen(bulk['total'])} ({text['phones'].format(n=bulk['phones'])})"
        if bulk.get("single_store"):
            single = bulk["single_store"]
            line += " / " + text["single_store"].format(store=single["store"], total=yen(single["total"]))
        lines.append(line)
        for item in bulk.get("excluded") or []:
            if item.get("reason") == "capacity_not_quoted" and item.get("capacity"):
                lines.append(text["excluded_capacity"].format(model=item["model"], capacity=capacity_label(item["capacity"]),
                                                              n=item["quantity"]))
                continue
            key = "excluded" if item.get("reason") == "capacity_missing" else "excluded_no_price"
            lines.append(text[key].format(model=item["model"], n=item["quantity"]))
    if evidence.get("devices_not_shown"):
        lines.append(text["not_shown"].format(models=", ".join(evidence["devices_not_shown"])))
    if not evidence.get("items") and evidence.get("follow_up_capacity"):
        lines.append(text["follow_up"].format(capacity=capacity_label(evidence["follow_up_capacity"])))
    return lines
