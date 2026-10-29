"""Word lists for the recognisers, all written in normalize_query() form.

Keep every list lower-case and half-width.  Longer phrases must come before
the shorter phrases they contain ("pro max" before "pro"), because the
recognisers take the first match.
"""

from __future__ import annotations

# Variant words that may follow a generation number ("17 pro max", "17プロマ", "16e").
VARIANT_ALIASES: tuple[tuple[str, str], ...] = (
    ("pro max", "Pro Max"), ("promax", "Pro Max"), ("pro-max", "Pro Max"), ("プロマックス", "Pro Max"),
    ("プロマ", "Pro Max"), ("ppm", "Pro Max"), ("pm", "Pro Max"), ("max", "Pro Max"), ("マックス", "Pro Max"),
    ("pro", "Pro"), ("プロ", "Pro"), ("普罗", "Pro"),
    ("plus", "Plus"), ("プラス", "Plus"), ("+", "Plus"),
    ("mini", "mini"), ("ミニ", "mini"),
    ("air", "Air"), ("エアー", "Air"), ("エア", "Air"),
    ("e", "e"),
)

# Words that name the foldable, which has no generation number.  The generic
# words ("fold", 折叠) only count when no other maker's foldable is named.
DUO_ALIASES: tuple[str, ...] = ("iphone duo", "duo", "デュオ", "折りたたみ", "折り畳み", "折叠", "摺疊", "fold", "フォールド")
DUO_GENERIC: frozenset[str] = frozenset({"折りたたみ", "折り畳み", "折叠", "摺疊", "fold", "フォールド"})
OTHER_MAKERS = ("galaxy", "pixel", "razr", "huawei", "honor", "oppo", "vivo", "xiaomi", "小米", "华为", "華為",
                "三星", "サムスン", "motorola", "z fold", "z flip")

# Apple products whose names also carry a number ("ipad pro 13", "a18 pro", "ios 18").
NOT_IPHONE_BEFORE = r"(ipad|macbook|mac|imac|watch|series|ios|ipados|macos|airpods|chip|galaxy|pixel|xiaomi|小米|华为|huawei|surface|ultra)\s*(pro|air|mini|max|ultra)?\s*$"

# Names without a generation number, mapped to the catalogue name.
UNNUMBERED_MODELS: tuple[tuple[str, str], ...] = (("iphone air", "iPhone 17 Air"), ("iphone エア", "iPhone 17 Air"), ("iphoneエア", "iPhone 17 Air"))

# Generations NOVA may be asked about.  Unknown ones are still reported (e.g. "iPhone 12").
MIN_GENERATION = 11
MAX_GENERATION = 19

CAPACITIES_GB = (64, 128, 256, 512, 1024, 2048)

CONDITION_ALIASES: tuple[tuple[str, str], ...] = (
    ("未開封", "sealed"), ("未开封", "sealed"), ("未拆封", "sealed"), ("sealed", "sealed"), ("unopened", "sealed"),
    ("シュリンク付", "sealed"), ("新品未使用", "sealed"),
    ("開封済", "opened"), ("開封", "opened"), ("开封", "opened"), ("拆封", "opened"), ("open box", "opened"),
    ("ジャンク", "broken"), ("故障", "broken"), ("壊れ", "broken"), ("坏了", "broken"), ("broken", "broken"),
    ("画面割れ", "broken"), ("碎屏", "broken"), ("cracked", "broken"),
    ("美品", "used"), ("中古", "used"), ("二手", "used"), ("used", "used"), ("second hand", "used"), ("secondhand", "used"),
    ("新品", "new"), ("全新", "new"), ("brand new", "new"),
)

CARRIER_ALIASES: tuple[tuple[str, str], ...] = (
    ("simフリー", "sim_free"), ("sim free", "sim_free"), ("simfree", "sim_free"), ("unlocked", "sim_free"),
    ("无锁", "sim_free"), ("無鎖", "sim_free"), ("国际版", "sim_free"),
    ("docomo", "docomo"), ("ドコモ", "docomo"),
    ("softbank", "softbank"), ("ソフトバンク", "softbank"),
    ("楽天モバイル", "rakuten"), ("rakuten mobile", "rakuten"),
    ("au版", "au"), ("au", "au"),
    ("港版", "hk_model"), ("国行", "cn_model"), ("美版", "us_model"), ("日版", "jp_model"),
)

# Counter words after a quantity ("3台", "2部", "5 units").
QUANTITY_COUNTERS: tuple[str, ...] = ("台", "部", "个", "個", "件", "units", "unit", "pcs", "pieces")
# a counter followed by these is a duration ("3个月" = three months), not a number of phones
DURATION_AFTER = r"(?:月|小时|小時|星期|年|日|天|回|週|周|weeks?|months?|years?|days?)"

MARKETS: tuple[tuple[str, str], ...] = (
    ("香港", "hk"), ("hong kong", "hk"), ("hongkong", "hk"), ("hk", "hk"),
    ("アメリカ", "us"), ("米国", "us"), ("美国", "us"), ("美國", "us"), ("usa", "us"), ("united states", "us"),
    ("日本", "jp"), ("japan", "jp"),
)
