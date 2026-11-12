# 回答の数字チェック（verify）

AI の回答に出てくる金額と店名を、価格の根拠（`evidence`）と突き合わせる。言語モデルは、もっともらしいが事実でない価格を書くことがある（ハルシネーション）。その検出用。

```python
from app.ai_gateway.verify import verify_answer, annotate

report = verify_answer(reply, request.price_evidence, request.price_rows)
report.status    # ok / warning / no_evidence / no_amounts
annotate(reply, report, "ja")   # 確認できなかった金額の注意書きを末尾に付けた回答
```

## 構成

| ファイル | 役割 |
|---|---|
| `amounts.py` | 回答から金額を拾う：`¥208,000`、`208,000円`、`20.8万円`、`20万8千円`、`HK$10,800`、`$1,531`、`1,531美元` など。容量・%・機種名・単位のない数字は拾わない。「約」「about」「前後」は概算として印を付ける |
| `facts.py` | 根拠から、回答に出てよい数字の一覧を作る：最高値・2 位・中央値・市場平均・定価・定価との差・順位表の各店・7 日/30 日の変化・傾き・海外価格（現地通貨と円）・まとめ売りの合計など。差は符号なしで持つ |
| `check.py` | 照合。同じ通貨・同じ値なら確認済み。概算は 1 %、万で書いた金額はその桁の丸め（17.6 万 → ±500 円）まで許す。1 文に店名と金額が 1 つずつあれば、その店が本当にその価格を出しているかも見る |
| `annotate.py` | 確認できなかった金額と、店の価格違いを、日・中・英の注意書きにする（回答本文は書き換えない） |

## 使っている場所

- `POST /api/v1/ai/chat`：回答ごとに照合し、`warning` のときはサーバーログに残す。**v1 では利用者に見える回答は変えない**（実際の回答で誤検出がないことを確かめてから注意書きを有効にする）。
- `GET /api/v1/ai/preview?answer=...`（管理者のみ）：貼り付けた回答の照合結果を `answer_check` で返す。

## ルール

- 根拠がない（機種が分からない、価格がない）ときは `no_evidence`。確認できないものを `ok` にはしない。
- 1 文に店が 2 つ以上、または金額が 2 つ以上あるときは、店と金額の組み合わせは推測になるので店の照合はしない（金額そのものの照合はする）。

## テスト

`backend/tests/test_ai_verify_amounts.py`、`backend/tests/test_ai_verify_check.py`、`backend/tests/test_ai_verify_annotate.py`（実際のサイトの回答を含む）
