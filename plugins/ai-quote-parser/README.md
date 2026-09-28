# ai-quote-parser

チャットや表に書かれた自由形式の買取見積もり（例：`17PM 256 新品×3 19.8万`）を、機種・容量・状態・台数・単価の行データに変換します。

- 文章の読み取りは AI、値の検証はプログラムが担当します。
- 機種と容量は実在する iPhone の組み合わせのみ受け付けます。
- 単価は元の文章に書かれている金額（`198,000`、`19.8万`、`19万8千` など）と一致する場合のみ採用し、推測された数値は `errors` に記録して除外します。

```bash
export AI_API_URL=https://api.example.com/v1/chat/completions AI_API_KEY=... AI_MODEL=...
python plugin.py quotes.txt              # JSON Lines（1 行ごとの items と errors）
python plugin.py quotes.txt --format csv # 採用された行のみ CSV
```

標準ライブラリのみで動作します。テスト：`python -m unittest`
