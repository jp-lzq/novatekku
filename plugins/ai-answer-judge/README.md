# ai-answer-judge

NOVA AI のテスト問題集（`frontend/src/data/aiTestCases.json`）の回答を採点し、合格率レポートを出力します。

1. ルール検査（AI の判定より優先）：空の回答、質問と異なる言語、表形式、必須語句の欠落・禁止語句
2. AI 採点：正確さ・有用性（0〜5）と、根拠のない価格・店舗・合計の有無。`--reference` で価格データを渡すと、それを唯一の根拠として判定します
3. 正確さ 3 以上かつ根拠のない情報がない回答を合格とし、カテゴリ別に集計します

```bash
python plugin.py ../../frontend/src/data/aiTestCases.json --rules-only
export AI_API_URL=https://api.example.com/v1/chat/completions AI_API_KEY=... AI_MODEL=...
python plugin.py aiTestCases.json --reference prices.json --min-pass-rate 0.9
```

言語判定はひらがなの有無を基準にしているため、カタカナや漢字の店舗名を含む中国語・英語の回答を日本語と誤判定しません。
標準ライブラリのみで動作します。テスト：`python -m unittest`
