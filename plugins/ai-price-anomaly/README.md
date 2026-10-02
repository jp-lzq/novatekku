# ai-price-anomaly

店舗別の買取価格から、ほかの店舗と大きく離れた価格を見つけ、考えられる原因を付けます。

- 検出は統計のみ（機種・容量ごとの中央値と MAD によるロバスト z スコア、既定 3.5）。AI の判断で検出結果は変わりません。
- AI は原因を `typo` / `different_condition` / `stale_price` / `promotion` / `carrier_model` / `unknown` から選ぶだけです。一覧にない原因は `unknown` になります。
- 店舗数が 4 未満の組み合わせは判定しません。

```bash
python plugin.py prices.csv --rules-only   # 検出のみ（model,capacity,store,price）
export AI_API_URL=https://api.example.com/v1/chat/completions AI_API_KEY=... AI_MODEL=...
python plugin.py prices.csv                # 検出 + 原因の推定
```

標準ライブラリのみで動作します。テスト：`python -m unittest`
