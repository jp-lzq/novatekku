# 会話の文脈（context）

「17 Pro 256 はいくら？」の次に「512 は？」「白は？」「香港なら？」と聞かれたとき、前の質問の機種を引き継いで答えられるようにする。

```python
from app.ai_gateway.context import resolve_message

history = [{"role": "user", "content": "iPhone 17 Pro 256 はいくら？"}, {"role": "assistant", "content": "..."}]
resolve_message("512 は？", history)
# devices: iPhone 17 Pro / 512、context.follow_up: True、context.carried: {"iPhone 17 Pro": []}
```

結果は `understanding.understand(...).to_dict()` と同じ形に `context` を足したもので、`AIRequest.understanding` にそのまま入る。価格の根拠（`evidence`）はこの機種で作られる。

## 構成

| ファイル | 役割 |
|---|---|
| `signals.py` | 言い回しから続きの質問らしいかを見る（「那」「呢」「それ」「なら」「what about」、短いメッセージ） |
| `history.py` | 直前 4 つのユーザー発言を古い順に読み直し、最後に話していた機種を決める |
| `merge.py` | 続きの質問が書いた項目（容量・色・状態・キャリア・台数）だけを差し替える |
| `__init__.py` | `resolve()`：上の 3 つをまとめ、質問の種類も決める |

## ルール

- 自分で機種を書いた質問は何も変えない。
- 続きの質問と見なすのは、**何かを変えている**（容量・色・状態・キャリア・台数・市場のどれか）か、**はっきり指している**（それ・那・what about など）うえで iPhone の話であるとき。短いだけの「ビットコインの価格は？」は続きにしない。
- 読むのはユーザーの発言だけ。AI の回答には多くの機種が出てくるので使わない。
- 発言は古い順に積み重ねるので、「17 Pro 256」→「512 は？」→「白は？」は 17 Pro 512 の白になる（256 に戻らない）。
- 色はその機種にある色だけを受け付ける（17 Pro の「白」はシルバー）。
- 前の質問に機種が 2 つあれば、変更は両方にかける（「17 Pro と 16 Pro」→「512 だと？」は両方 512）。
- 続きの質問が種類を言っていなければ前の種類を引き継ぐ（比較の続きは比較）。市場を言えば海外比較になる。
- あいさつは続きにしない。

## テスト

`backend/tests/test_ai_context_signals.py`、`backend/tests/test_ai_context_merge.py`、`backend/tests/test_ai_context_resolve.py`
