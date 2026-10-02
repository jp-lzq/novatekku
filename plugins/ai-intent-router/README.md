# ai-intent-router

ユーザーの質問を、価格・一括計算・機種一覧・売却・購入・データ移行・不具合・その他スマホ・対象外の 9 種類に分類します。

- AI がまとめて分類し、一覧にないラベルや確信度 0.6 未満の結果はキーワード規則で判定し直します。
- すべての質問に必ず有効なラベルが付き、`source` で AI と規則のどちらが決めたか分かります。
- 正解ラベル付きの入力なら、正解率と取り違えの内訳を出力します。

```bash
python plugin.py questions.jsonl --rules-only   # {"question": "...", "intent": "price"} を 1 行ずつ
export AI_API_URL=https://api.example.com/v1/chat/completions AI_API_KEY=... AI_MODEL=...
python plugin.py questions.jsonl
```

標準ライブラリのみで動作します。テスト：`python -m unittest`
