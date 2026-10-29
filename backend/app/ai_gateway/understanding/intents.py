"""Decide what kind of question the user asked.

Each intent has weighted cue patterns in Japanese, Chinese and English.  The
score of an intent is the sum of the weights of its cues found in the
question, plus small adjustments from the recognised devices (two phones
suggest a comparison, a quantity suggests a bulk quote).  The intent with the
highest score wins; ``confidence`` is its share of all scores, so 1.0 means no
other intent was suggested at all.

The result is advice for the AI core, not a gate: a low confidence means
"answer generally", never "refuse".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .entities import DeviceMention
from .lexicon import MARKETS

PRICE_QUOTE = "price_quote"  # how much will a shop pay for this phone
STORE_RANKING = "store_ranking"  # which shop pays the most
MODEL_COMPARE = "model_compare"  # which of two phones is worth more / should I sell
SELL_TIMING = "sell_timing"  # sell now or wait
OVERSEAS_MARKET = "overseas_market"  # Hong Kong / United States prices
BULK_QUOTE = "bulk_quote"  # several phones at once, totals
CATALOG = "catalog"  # which models / capacities exist
RETAIL_PRICE = "retail_price"  # Apple's own price
STORE_INFO = "store_info"  # address, opening hours, phone number of a shop
DEVICE_HELP = "device_help"  # iPhone usage: data transfer, battery, reset
GREETING = "greeting"  # hello / thanks
OFF_TOPIC = "off_topic"  # nothing to do with iPhones or buyback

INTENTS = (PRICE_QUOTE, STORE_RANKING, MODEL_COMPARE, SELL_TIMING, OVERSEAS_MARKET, BULK_QUOTE,
           CATALOG, RETAIL_PRICE, STORE_INFO, DEVICE_HELP, GREETING, OFF_TOPIC)

# intents that need the current price table
PRICE_INTENTS = frozenset({PRICE_QUOTE, STORE_RANKING, MODEL_COMPARE, SELL_TIMING, OVERSEAS_MARKET, BULK_QUOTE})

CUES: dict[str, tuple[tuple[str, float], ...]] = {
    PRICE_QUOTE: (
        (r"いくら|何円|買取価格|買取額|値段|相場|査定|価格", 2.0),
        (r"多少钱|多少錢|回收价|回收價|价格|價格|价钱|报价|估价|值多少", 2.0),
        (r"how much|price|worth|quote|value|buyback|trade[ -]?in", 2.0),
        (r"買取|回收|売りたい|卖掉|出手|sell", 1.0),
    ),
    STORE_RANKING: (
        (r"どこ(が|で|の店)|どの(店|お店|店舗)|一番高|最高値|高く売れる|おすすめの店", 3.0),
        (r"哪家|哪个店|哪間|哪里卖|最高价|卖得最贵|最贵|推荐.*店", 3.0),
        (r"which (store|shop)|where (can|should|to) i sell|best (store|shop|price)|highest", 3.0),
    ),
    MODEL_COMPARE: (
        (r"比較|比べ|どっち|どちら|違い|vs|の差|差は|差額|価格差", 2.5),
        (r"哪个|哪個|对比|對比|比较|比較|区别|區別|还是|差多少|差价|差價|差距|差额", 2.5),
        (r"compare|comparison|versus|difference|which (one|is better)|or the|price gap", 2.5),
    ),
    SELL_TIMING: (
        (r"いつ売|今売|売り時|タイミング|待つべき|待った方|値下がり|値上がり|下が[るりっ]|上が[るりっ]|今後|が出たら|発売(後|され)", 3.0),
        (r"什么时候卖|現在卖|现在卖|何时卖|时机|時機|会跌|会降|会涨|等等再卖|再等|跌价|降价|涨价|发布后|出了以后|出来以后", 3.0),
        (r"when (should|to) (i )?sell|sell now|good time|wait|price drop|drop|going (up|down)|trend|after .{0,20}(launch|release|comes out)", 3.0),
    ),
    OVERSEAS_MARKET: (
        (r"海外|外国|国外|overseas|abroad|global|全球|世界", 2.0),
    ),
    BULK_QUOTE: (
        (r"まとめて|合計|全部で|複数|一括", 2.5),
        (r"一共|合计|合計|总共|總共|批量|全部卖", 2.5),
        (r"in total|altogether|total|bulk|all of them", 2.5),
    ),
    CATALOG: (
        (r"種類|ラインナップ|モデル一覧|どんな機種|何がある", 3.0),
        (r"有什么种类|有哪些|型号|系列|种类", 3.0),
        (r"which models|what models|lineup|line-up|types of iphone", 3.0),
    ),
    RETAIL_PRICE: (
        (r"定価|発売価格|apple価格|アップル.*価格|公式価格|新品価格", 3.0),
        (r"官网价|官網價|官方价|发售价|發售價|原价|定价", 3.0),
        (r"retail price|apple price|launch price|msrp|official price|apple store price", 3.0),
    ),
    STORE_INFO: (
        (r"住所|営業時間|電話番号|アクセス|最寄り|何時まで|定休日|どこにあ|場所", 3.5),
        (r"地址|营业时间|營業時間|电话|電話|怎么去|几点|在哪里|在哪儿|在哪", 3.5),
        (r"address|opening hours|open until|phone number|how to get|located|where is (your|the) (shop|store)", 3.5),
    ),
    DEVICE_HELP: (
        (r"データ移行|バックアップ|初期化|機種変更|設定|バッテリー|充電|アップデート|ios|使い方|android", 2.5),
        (r"数据迁移|資料轉移|备份|備份|恢复出厂|初始化|电池|電池|充电|升级|怎么用|设置|設定", 2.5),
        (r"transfer|backup|back up|reset|battery|charge|charging|update|settings|how (do|to) (i )?use|android", 2.5),
    ),
    GREETING: (
        (r"^(こんにちは|こんばんは|おはよう|はじめまして|ありがとう|どうも|よろしく)", 3.0),
        (r"^(你好|您好|嗨|谢谢|謝謝|多谢|早上好|晚上好)", 3.0),
        (r"^(hi|hello|hey|thanks|thank you|good (morning|evening))\b", 3.0),
    ),
}

# words that show the question is about phones or buyback at all
_DOMAIN_RE = re.compile(
    r"iphone|apple|アップル|スマホ|携帯|機種|买取|買取|回收|手机|手機|苹果|蘋果|phone|smartphone|ipad|"
    r"(?<![a-z])au(?![a-z])|docomo|softbank|(?<![a-z])sim(?![a-z])|simフリー|中古|二手|新品|店|ショップ|shop|store"
)


@dataclass
class IntentResult:
    intent: str
    confidence: float
    scores: dict[str, float] = field(default_factory=dict)
    cues: dict[str, list[str]] = field(default_factory=dict)  # intent -> cue texts found
    markets: list[str] = field(default_factory=list)  # hk / us / jp mentioned

    @property
    def needs_prices(self) -> bool:
        return self.intent in PRICE_INTENTS

    def ranked(self) -> list[tuple[str, float]]:
        return sorted(((name, score) for name, score in self.scores.items() if score > 0),
                      key=lambda item: (-item[1], INTENTS.index(item[0])))

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "confidence": round(self.confidence, 3),
            "needs_prices": self.needs_prices,
            "ranked": [[name, round(score, 2)] for name, score in self.ranked()],
            "cues": self.cues,
            "markets": self.markets,
        }


def _markets(text: str) -> list[str]:
    found: list[str] = []
    for word, market in MARKETS:
        if market in found:
            continue
        pattern = rf"(?<![a-z]){re.escape(word)}(?![a-z])" if word.isascii() else re.escape(word)
        if re.search(pattern, text):
            found.append(market)
    return found


def classify(text: str, devices: list[DeviceMention], follow_up: bool = False) -> IntentResult:
    """``text`` must already be normalised with normalize_query().

    ``follow_up``: the message only names a capacity ("那 512 呢？"), so it
    continues the previous price question.
    """
    scores = {name: 0.0 for name in INTENTS}
    cues: dict[str, list[str]] = {}
    for intent, patterns in CUES.items():
        for pattern, weight in patterns:
            for match in re.finditer(pattern, text):
                scores[intent] += weight
                cues.setdefault(intent, []).append(match.group(0))
                break  # one hit per pattern is enough; repeating a word should not win

    markets = _markets(text)
    overseas = [market for market in markets if market != "jp"]
    if overseas:
        scores[OVERSEAS_MARKET] += 5.0  # "香港でいくら" is a price question about that market
        cues.setdefault(OVERSEAS_MARKET, []).extend(overseas)

    distinct_models = {device.model for device in devices}
    if len(distinct_models) >= 2:
        scores[MODEL_COMPARE] += 1.5 if scores[MODEL_COMPARE] else 0.5
        if any(device.quantity > 1 for device in devices):
            scores[BULK_QUOTE] += 2.0
    if any(device.quantity > 1 for device in devices):
        scores[BULK_QUOTE] += 2.5
        cues.setdefault(BULK_QUOTE, []).extend(
            device.evidence["quantity"] for device in devices if "quantity" in device.evidence
        )
    if devices:
        # a bare model ("17 pro 256") is almost always a price question
        scores[PRICE_QUOTE] += 1.5
        if scores[DEVICE_HELP] and not scores[PRICE_QUOTE] > 1.5:
            scores[DEVICE_HELP] += 0.5
    if follow_up:
        scores[PRICE_QUOTE] += 2.0
        cues.setdefault(PRICE_QUOTE, []).append("follow-up capacity")
    if scores[RETAIL_PRICE]:
        scores[PRICE_QUOTE] = max(0.0, scores[PRICE_QUOTE] - 2.0)  # "apple price" also contains "price"
    if scores[SELL_TIMING]:
        scores[PRICE_QUOTE] = max(0.0, scores[PRICE_QUOTE] - 2.0)  # "will the buyback price drop?" is about timing
    if scores[MODEL_COMPARE] and scores[BULK_QUOTE] and not any(device.quantity > 1 for device in devices):
        scores[BULK_QUOTE] = 0.0  # "17 pro と 16 pro の差" compares, it does not add up
    if scores[GREETING] and any(scores[name] for name in INTENTS if name != GREETING):
        scores[GREETING] *= 0.3  # "こんにちは、17 pro はいくら？" is a price question

    total = sum(scores.values())
    if total == 0:
        intent = GREETING if not text else (DEVICE_HELP if _DOMAIN_RE.search(text) else OFF_TOPIC)
        return IntentResult(intent=intent, confidence=0.0 if intent != OFF_TOPIC else 0.6,
                            scores=scores, cues=cues, markets=markets)

    best = max(INTENTS, key=lambda name: (scores[name], -INTENTS.index(name)))
    if best in PRICE_INTENTS and not devices and not follow_up and not overseas and not _DOMAIN_RE.search(text):
        # "ビットコインの価格は？": a price question, but not about phones
        cues.setdefault(OFF_TOPIC, []).append("no phone or shop words")
        return IntentResult(intent=OFF_TOPIC, confidence=0.5, scores=scores, cues=cues, markets=markets)
    return IntentResult(intent=best, confidence=scores[best] / total, scores=scores, cues=cues, markets=markets)
