"""Short text lines that state the price evidence in the answer language.

The AI core can put these lines into its prompt as-is, and the same text is
shown to admins in the preview endpoint.  Every number comes straight from
build_price_evidence(); nothing is rounded beyond yen.
"""

from __future__ import annotations

LABELS = {
    "ja": {
        "store_compare": "店舗比較", "rank_of": "{rank}位/{n}店", "rank": "{rank}位",
        "store_wins": "{winner}が {other}より {gap} 高い", "store_tie": "同額",
        "store_unquoted": "{store}: この機種・容量の価格はありません",
        "store_better_elsewhere": "最高は {store} {price}（{gap} 高い）",
        "target": "目標 {target}", "target_reached": "達成 {n}店: {stores}",
        "target_missed": "達成店なし: 最高 {price}（{store}）、あと {gap}",
        "target_best": "最高 {price}（{store}）目標比 {diff}", "target_more": "ほか{n}店",
        "target_trend": "7日前比 {change} {direction}",
        "color_best": "{color}: 最高 {price} ({store})", "color_shared": "全色同額の店",
        "color_behind": "最高色の{top}より {gap}", "color_top": "{n}色中1位",
        "color_unquoted": "{color}: この色の価格はありません", "color_range": "色別: {items}",
        "global": "世界比較", "jp": "日本",
        "advice_japan_best": "日本が一番高いので日本で売るのがおすすめ",
        "advice_overseas_small": "{market}が {gap}{pct} 高いが、送料・手数料・為替で消える差なので日本で売るのが現実的",
        "advice_overseas_clear": "{market}が {gap}{pct} 高い。現地で売れる人には有利だが、送料・手数料・関税・為替を差し引いて判断",
        "advice_japan_only": "海外の比較できる価格がないため日本の価格で判断",
        "advice_falling": "日本の価格は下落中なので早めの売却がおすすめ",
        "advice_rising": "日本の価格は上昇中",
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
        "store_compare": "店铺比较", "rank_of": "第{rank}/{n}家", "rank": "第{rank}",
        "store_wins": "{winner}比{other}高 {gap}", "store_tie": "同价",
        "store_unquoted": "{store}：这个机型和容量没有报价",
        "store_better_elsewhere": "最高的是 {store} {price}（高 {gap}）",
        "target": "目标 {target}", "target_reached": "达到的有{n}家：{stores}",
        "target_missed": "没有店达到：最高 {price}（{store}），还差 {gap}",
        "target_best": "最高 {price}（{store}）比目标 {diff}", "target_more": "另有{n}家",
        "target_trend": "比7天前 {change} {direction}",
        "color_best": "{color}：最高 {price}（{store}）", "color_shared": "所有颜色同价的店",
        "color_behind": "比最高的{top}低 {gap}", "color_top": "{n}种颜色里第1",
        "color_unquoted": "{color}：这个颜色没有报价", "color_range": "分颜色：{items}",
        "global": "全球比较", "jp": "日本",
        "advice_japan_best": "日本最高，建议在日本卖",
        "advice_overseas_small": "{market}高 {gap}{pct}，但这点差价会被运费、手续费和汇率吃掉，在日本卖更实际",
        "advice_overseas_clear": "{market}高 {gap}{pct}。人在当地能卖的话更划算，但要扣掉运费、手续费、关税和汇率再判断",
        "advice_japan_only": "没有可比较的海外价格，按日本价格判断",
        "advice_falling": "日本价格在下跌，建议早点卖",
        "advice_rising": "日本价格在上涨",
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
        "store_compare": "store comparison", "rank_of": "#{rank} of {n}", "rank": "#{rank}",
        "store_wins": "{winner} pays {gap} more than {other}", "store_tie": "same price",
        "store_unquoted": "{store}: no price for this model and capacity",
        "store_better_elsewhere": "the best is {store} {price} ({gap} more)",
        "target": "target {target}", "target_reached": "{n} store(s) reach it: {stores}",
        "target_missed": "no store reaches it: best {price} ({store}), {gap} short",
        "target_best": "best {price} ({store}) {diff} vs target", "target_more": "{n} more",
        "target_trend": "{change} vs 7 days ago, {direction}",
        "color_best": "{color}: best {price} ({store})", "color_shared": "a store paying the same for every colour",
        "color_behind": "{gap} vs the top colour {top}", "color_top": "top of {n} colours",
        "color_unquoted": "{color}: no price for this colour", "color_range": "by colour: {items}",
        "global": "global comparison", "jp": "Japan",
        "advice_japan_best": "Japan pays the most, so selling in Japan is recommended",
        "advice_overseas_small": "{market} pays {gap}{pct} more, but shipping, fees and the exchange rate eat a gap that small, so Japan is the practical choice",
        "advice_overseas_clear": "{market} pays {gap}{pct} more; worth it for someone who can sell there, after shipping, fees, customs and the exchange rate",
        "advice_japan_only": "no comparable overseas price, so judge by the Japanese price",
        "advice_falling": "Japanese prices are falling, so selling soon is recommended",
        "advice_rising": "Japanese prices are rising",
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
        if market.get("best_store"):
            line += f" ({market['best_store']})"
        if market.get("price_jpy") is not None:
            line += f" = {yen(market['price_jpy'])}"
        if market.get("vs_japan") is not None:
            line += f" {text['vs_japan']} {yen(market['vs_japan'], True)}{percent(market.get('vs_japan_percent'))}"
        parts.append(line)
    return " / ".join([parts[0] + " " + parts[1]] + parts[2:]) if len(parts) > 1 else parts[0]


def _color_name(names: dict | None, code: str | None, language: str) -> str:
    return (names or {}).get(language) or code or ""


def color_line(colors: dict, text: dict, language: str) -> str | None:
    """The asked colour's best price and its gap to the top colour, or the colour range when none was asked."""
    requested = colors.get("requested")
    if requested:
        name = _color_name(requested.get("names"), requested["code"], language)
        if not requested.get("quoted"):
            return text["color_unquoted"].format(color=name)
        line = text["color_best"].format(color=name, price=yen(requested["best_price"]), store=requested["best_store"])
        if requested.get("source") == "all_colors":
            line += f" [{text['color_shared']}]"
        if requested.get("behind_top"):
            top = _color_name(requested.get("top_color_names"), requested.get("top_color"), language)
            line += " / " + text["color_behind"].format(top=top, gap=yen(-requested["behind_top"], True))
        elif requested.get("rank") == 1 and requested.get("color_count", 0) > 1:
            line += " / " + text["color_top"].format(n=requested["color_count"])
        return line
    if colors.get("color_spread"):
        ranked = colors["colors"]
        items = [f"{_color_name(color['names'], color['code'], language)} {yen(color['best_price'])}" for color in ranked[:6]]
        return text["color_range"].format(items=", ".join(items))
    return None


def advice_text(comparison: dict, text: dict) -> str:
    """The recommendation of a global comparison as one sentence (plus the Japanese trend when it matters)."""
    market = comparison.get("best_overseas_market")
    sentence = text[f"advice_{comparison['advice']}"].format(
        market=text.get(market, market or ""), gap=yen(comparison.get("overseas_gap")),
        pct=percent(comparison.get("overseas_gap_percent")))
    direction = comparison.get("japan_direction")
    if direction == "down" and comparison["advice"] != "overseas_clear":
        sentence += " / " + text["advice_falling"]
    elif direction == "up":
        sentence += " / " + text["advice_rising"]
    return sentence


def _global_line(model: str, entry: dict, text: dict) -> str:
    comparison = entry["global"]
    ranked = []
    for market in comparison["ranking"]:
        name = text.get(market["market"], market["market"])
        store = f" ({market['store']})" if market.get("store") else ""
        ranked.append(f"{market['rank']}) {name} {yen(market['price_jpy'])}{store}")
    return f"{model} {capacity_label(entry['capacity'])} {text['global']}: " + " ".join(ranked) + " → " + advice_text(comparison, text)


def store_compare_lines(comparison: dict, text: dict) -> list[str]:
    """The asked stores for each phone: price, place, who pays more, and the stores without a quote."""
    lines: list[str] = []
    for item in comparison.get("items") or []:
        parts = []
        for index, store in enumerate(item["stores"]):
            place = (text["rank_of"].format(rank=store["rank"], n=item["store_count"]) if index == 0
                     else text["rank"].format(rank=store["rank"]))
            parts.append(f"{store['store']} {yen(store['price'])} ({place})")
        line = f"{item['model']} {capacity_label(item['capacity'])} {text['store_compare']}: " + " / ".join(parts or ["-"])
        if item.get("winner"):
            runner = item["stores"][1]
            line += " → " + text["store_wins"].format(winner=item["winner"], other=runner["store"], gap=yen(item["gap"]))
        elif item.get("tie"):
            line += " → " + text["store_tie"]
        if item.get("gap_to_best"):
            line += " / " + text["store_better_elsewhere"].format(store=item["best_store"], price=yen(item["best_price"]),
                                                                  gap=yen(item["gap_to_best"]))
        lines.append(line)
        lines += [text["store_unquoted"].format(store=store) for store in item.get("unquoted") or []]
    return lines


def target_lines(assessment: dict, text: dict) -> list[str]:
    """For each phone: the stores reaching the target, or how far the best price is short of it."""
    lines: list[str] = []
    for item in assessment.get("items") or []:
        head = f"{item['model']} {capacity_label(item['capacity'])} {text['target'].format(target=yen(item['target']))}: "
        if item["reached"]:
            stores = ", ".join(f"{store['store']} {yen(store['price'])}" for store in item["stores"])
            if item["reached_count"] > len(item["stores"]):
                stores += " " + text["target_more"].format(n=item["reached_count"] - len(item["stores"]))
            body = text["target_reached"].format(n=item["reached_count"], stores=stores)
            body += " / " + text["target_best"].format(price=yen(item["best_price"]), store=item["best_store"],
                                                       diff=yen(item["best_vs_target"], True))
        else:
            body = text["target_missed"].format(price=yen(item["best_price"]), store=item["best_store"],
                                                gap=yen(item["shortfall"]))
        if item.get("change_7d") is not None and item.get("direction"):
            body += " / " + text["target_trend"].format(change=yen(item["change_7d"], True),
                                                        direction=text.get(item["direction"], ""))
        lines.append(head + body)
    return lines


def render_evidence(evidence: dict, language: str = "ja") -> list[str]:
    text = LABELS.get(language, LABELS["en"])
    language = language if language in LABELS else "en"
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
            if entry.get("colors") and len(item.get("capacities") or []) == 1:
                line = color_line(entry["colors"], text, language)
                if line:
                    lines.append(line)
            if entry.get("global") and evidence.get("intent") == "overseas_market":
                lines.append(_global_line(item["model"], entry, text))
    if evidence.get("store_compare"):
        lines += store_compare_lines(evidence["store_compare"], text)
    if evidence.get("target_price"):
        lines += target_lines(evidence["target_price"], text)
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
