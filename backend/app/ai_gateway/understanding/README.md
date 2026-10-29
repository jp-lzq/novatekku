# 質問理解（understanding）

NOVA AI に届いた質問を、AI コアへ渡す前に「何を聞いているか」「どの iPhone の話か」に分解する。
モデル呼び出しもネットワークも使わない決定的な処理なので、毎回の質問で動かせる。

```python
from app.ai_gateway.understanding import understand

understand("17プロマ 256 白 未開封 2台 どこが一番高い？").to_dict()
# intent: store_ranking / devices: iPhone 17 Pro Max, 256, silver, sealed, 2台
```

結果は `AIRequest.understanding` に入り、AI コアが答え方を選ぶ材料になる（v1 では回答内容は変えない）。

## 構成

| ファイル | 役割 |
|---|---|
| `normalize.py` | 表記ゆれの統一：全角→半角、十七→17、アイフォン→iphone、256G→256gb、1テラ→1tb |
| `lexicon.py` | 型番・状態・キャリア・台数・市場の別名リスト（日・中・英） |
| `entities.py` | 機種の認識：モデル、容量、色（商品カタログの別名を再利用）、状態、キャリア、台数 |
| `intents.py` | 質問の種類を 12 種に分類し、確信度（全スコアに占める割合）を出す |

## 意図（intent）

| 名前 | 例 |
|---|---|
| `price_quote` | 17 Pro 256 はいくら？ / 那 512 呢？ |
| `store_ranking` | どこが一番高い？ / 哪家最高价 |
| `model_compare` | 17 Pro と 16 Pro Max どっち？ |
| `sell_timing` | 今売るべき？ 待つべき？ |
| `overseas_market` | 香港で売ったらいくら？ |
| `bulk_quote` | 16e×3 と 17×2 の合計 |
| `catalog` | iPhone の種類は？ |
| `retail_price` | 17 Air の定価は？ |
| `store_info` | 店の住所・営業時間 |
| `device_help` | データ移行、バッテリー、初期化 |
| `greeting` | こんにちは / 谢谢 |
| `off_topic` | ビットコインの価格は？ |

## 認識のルール

- 容量・色・状態・台数は、直前に書かれた機種に付く（次の機種が出るまで）。
- 「12台」「2024年」「15時」「15:00」「11/15」「12.5万」「11 pm」の数字は機種にしない。iphone も型番も容量も台数もない裸の「17」は機種にしない。
- iPad Pro 13、MacBook Air 13、Apple Watch Series 11、A18 Pro、iOS 18、小米14、Galaxy Z Fold は iPhone にしない。
- 台数は「17 pro x2」「17 pro 2台」のように後ろに書くのが基本。「两台17pro」のように前に書いた台数は、その機種に自分の台数がないときだけ付ける。
- 「iPhone Air」（世代番号なし）は iPhone 17 Air として扱う。
- カタログにない機種（iPhone 12 など）も捨てずに `known: false` で返す。
- 各項目は読み取った元の文字列を `evidence` に残す。

## 既知の限界

- 「5G対応の17はある？」のように、iphone も型番も容量もない「17」は認識しない（数字の誤認を避けるため）。
- 色は商品カタログの別名で探すので、「青山」「白金台」のような地名の一字を色と読むことがある。
- 前の質問の機種を引き継ぐ処理（「那 512 呢？」の機種補完）は次の段階で入れる。v1 は容量だけを `follow_up_capacity` で返す。

## テスト

`backend/tests/test_ai_understanding.py`（184 件）
