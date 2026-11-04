# 価格の根拠（evidence）

質問理解（`understanding`）が「どの iPhone の話か」を決めた後、その機種について回答の根拠になる数字を集める。
AI コアが価格を推測せず、NOVA のデータどおりに答えられるようにするための材料。

```python
from app.ai_gateway.evidence import build_price_evidence
from app.ai_gateway.understanding import understand

build_price_evidence(understand("17 pro 256 x2 と 16e 128 x3 合計").to_dict(), price_rows, fx_rates=rates)
```

結果は `AIRequest.price_evidence` に入る（v1 では回答内容は変えない）。

## 機種・容量ごとに出す数字

| 項目 | 内容 | ファイル |
|---|---|---|
| 現在の買取価格 | 最高値と店、2 位との差、上位 5 店、中央値、最高値と最安値の差、市場平均、Apple 定価との差 | `quotes.py` |
| 値動き | 7 日前・30 日前との差、30 日の最小二乗直線の傾き（円/週）、30 日の高値・安値、up / down / flat | `trend.py` |
| 海外 | 香港・アメリカの最高値を円に換算し、日本の最高値との差と % | `overseas.py` |
| まとめ売り | 機種ごとに最高値の店で売った合計と、全機種を 1 店で売る場合の最高の店 | `bulk.py` |
| 表示文 | 上の数字を日・中・英の短い 1 行にまとめる（`lines`）。AI コアのプロンプトと管理者プレビューで使う | `render.py` |

管理者は `GET /api/v1/ai/preview?message=...&language=ja` で、質問の理解結果と根拠を本番データで確認できる（モデルは呼ばず、質問回数も減らない）。

## ルール

- 容量の指定がなければ、価格のある容量をすべて（小さい順、最大 6 つ）出し、`capacity_missing` を付ける。
- 指定の容量に価格がなければ、ある容量を出して `capacity_not_quoted` を付ける。
- カタログにない機種は `unknown_model`、価格がない機種は `no_prices`。
- 同じ店が色別に複数の価格を出していても、その店の最高値 1 つだけを数える。
- 値動きの「その日の最高値」は price_history から日本時間の 1 日ごとに作る：各店のその日の最後の価格だけを使い、下限（1 万円）と上限を外れた価格を除き、3 店以上なら価格ページと同じ合意帯で外れ値の店を除いた後の最高値。今日の値はサイトの現在の最高値と一致する。数十分だけ出た高値（例：11:17 に 385,000、11:47 に 360,000）は数えない。daily_high_prices の close_price は「その日最後に取得した店の価格」で最高値ではないので使わない。
- まとめ売りの合計に入れるのは、質問に容量が書かれていて価格がある機種だけ。入れられなかった機種は `excluded` に理由付きで出し、合計が黙って少なくならないようにする。合計を出すのは、合計を聞かれたときか、同じ機種を 2 台以上売るときだけ。
- 一度に扱う機種は最大 4 つで、それ以上は `devices_not_shown` に名前を出す。
- `fx_updated` に為替の更新日時を入れる。
- 海外価格は直近 48 時間以内の各ソースの最新スナップショットだけを使う（`/api/v1/prices/markets` と同じ）。
- 為替はメモリかファイルにある値だけを使い、質問のたびにネットワークへは行かない。
- データベースの読み込みに失敗しても例外を出さず、空の結果を返す（AI の回答は止めない）。

## テスト

`backend/tests/test_ai_evidence.py`（45 件）、`backend/tests/test_ai_evidence_render.py`（表示文と管理者プレビュー）
