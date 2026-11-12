# 質問理解の採点（eval）

NOVA AI が質問をどれだけ正しく理解できるかを、決まった問題集で採点する。変更のたびに点数を比べられるので、改善も劣化もすぐ分かる。

```bash
python -m app.ai_gateway.eval          # 表で表示
python -m app.ai_gateway.eval --json   # JSON で出力
```

## 問題集（`cases.jsonl`）

1 行 1 問。日本語・中国語・英語で約 160 問、続きの質問（前の発言つき）も含む。

```json
{"id": "ja-follow-01", "lang": "ja", "q": "512 は？", "history": ["iPhone 17 Pro 256 はいくら？"],
 "expect": {"intent": "price_quote", "models": ["iPhone 17 Pro"], "capacities": ["512"]}}
```

- `expect` に書いた項目（`intent`・`models`・`capacities`・`colors`・`quantities`・`markets`）だけを採点する。
- まだ正しく答えられない問題は消さずに `known_gap` に理由を書いて残す。点数は隠さない。直ったら採点結果に「known gaps now answered correctly」と出るので、印を外す。
- 誤認しやすい文（「12台」「15:00」「iPad Pro 13」「Galaxy Z Fold」など）も入れて、機種と読み違えないことを確かめる。

## 現在の点数（2026-11-12）

| 項目 | 正答率 |
|---|---|
| 全体 | 151 / 160（94.4%） |
| 容量・色・市場・台数 | 100% |
| 機種 | 97.0% |
| 質問の種類 | 95.9% |

残る 9 問はすべて `known_gap`（数字だけの機種名、営業時間を言わない店舗の質問、「涨还是跌」「after Christmas」のような売り時の言い回しなど）。

この問題集で新たに見つかった 5 つの誤り（「違い」を含む比較、「どこで見られる」の使い方質問、「18发布后17」、「where can I sell … highest price」、「3 of them」）は修正済み。

## テスト

`backend/tests/test_ai_eval.py` が全体 94%・項目ごとの下限を守り、`known_gap` 以外の不正解が出たら失敗する。下限は点数が上がったときだけ引き上げる。
