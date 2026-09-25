# NOVA買取サイト - 環境構築ガイド

この文書は公開リポジトリ向けの一般的なセットアップ手順のみを記載しています。
実運用の認証情報、内部URL、データソースURL、運用連絡先はリポジトリに含めないでください。

## ローカル開発環境

### 前提条件
- Docker & Docker Compose
- Node.js 20+ (フロントエンド開発のみの場合)
- Python 3.11+ (バックエンド開発のみの場合)

### 1. Dockerで一括起動

```bash
# リポジトリのクローン
git clone https://github.com/jp-lzq/novatekku.git
cd novatekku

# 環境変数のコピー
cp .env.example backend/.env

# コンテナ起動
docker compose up -d

# テーブル作成（初回・更新時）
docker compose run --rm migrate
```

アクセス:
- フロントエンド: http://localhost:3000
- API: http://localhost:8000
- APIドキュメント: http://localhost:8000/docs

### 2. バックエンドのみ開発

```bash
cd backend

# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# データベース起動（Docker）
docker run -d --name nova-postgres \
  -e POSTGRES_USER=app_user \
  -e POSTGRES_PASSWORD=change_me \
  -e POSTGRES_DB=nova_kaitori \
  -p 5432:5432 postgres:15-alpine

# テーブル作成
python -m app.db.migrate

# サーバー起動
uvicorn app.main:app --reload
```

### 3. フロントエンドのみ開発

```bash
cd frontend

# 依存関係インストール
npm install

# 開発サーバー起動
npm run dev
```

## 本番デプロイ

### VPS (Ubuntu)

```bash
# 1. サーバーにSSH接続
ssh user@your-server

# 2. リポジトリクローン
git clone https://github.com/jp-lzq/novatekku.git
cd novatekku

# 3. 本番用環境変数設定
nano .env
# DATABASE_URL=postgresql://app_user:change_me@localhost:5432/nova_kaitori
# REDIS_URL=redis://localhost:6379/0

# 4. Docker Composeで起動
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 5. データベース初期化
docker compose run --rm migrate
```

### 本番フロント反映

現在の `novakai.net` フロントは nginx が `/var/www/novakai` を静的配信しています。
そのため、フロントの見た目変更を本番へ反映するときは Docker コンテナ再作成だけでは不十分で、ビルド済み静的ファイルの同期が必要です。

```bash
cd novatekku
./scripts/deploy_frontend_live.sh
```

このスクリプトは以下を実施します。

- `VITE_APP_VERSION_UPDATED_AT` をビルド時刻で自動注入
- `frontend` の本番ビルド
- `frontend/dist/` を `/var/www/novakai` へ `rsync --delete` で同期

反映確認:

```bash
curl -s https://novakai.net | sed -n '1,40p'
```

ページ最下部の `Current version updated` / `当前版本更新时间` / `現在のバージョン更新日時` が最新時刻なら、新バージョンが配信されています。

### 会員認証とパスワード再設定

会員ログインは、ブラウザのローカル保存値ではなく、バックエンドの `member_sessions` テーブルと安全なCookieで管理します。

- セッションCookie: `HttpOnly`、`Secure`、`SameSite=Lax`
- CSRF保護: `nova_csrf` Cookieと `X-NOVA-CSRF` ヘッダーを照合
- ログイン・登録・パスワード操作: Redis優先のレート制限
- パスワード再設定Token: ハッシュ化してDB保存、有効期限あり、一度のみ使用可能
- パスワード変更・再設定後: 既存セッションをすべて無効化

パスワード再設定メールは、SMTPを設定するまで安全のため無効です。未設定時にメールアドレスだけでパスワードを変更できる代替経路は設けません。

```env
PUBLIC_APP_URL=https://ai.example.com
AUTH_ORIGINS=https://ai.example.com
AUTH_COOKIE_SECURE=true
PASSWORD_RESET_EMAIL_ENABLED=true
PASSWORD_RESET_TOKEN_MINUTES=30
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@example.com
SMTP_STARTTLS=true
```

SMTPを有効化する前に、実際の受信先でメール到達、リンクの有効期限、一度使用したTokenの拒否を確認してください。

依存関係監査では、React RouterのRSCモード向けCSRFアドバイザリが表示されます。本プロジェクトはViteのブラウザSPAで、React Server Components、サーバーAction、React RouterのRSCルートを使用していないため、該当する実行経路はありません。修正版が公開された時点で更新し、監査例外を解消してください。

### クラウドサービス

#### Render
1. GitHubリポジトリと連携
2. Blueprintで `render.yaml` を使用
3. 環境変数を設定
4. 自動デプロイ

#### Railway
```bash
railway login
railway init
railway up
```

## 構成と権限

システム構成、データベース権限、収集元の管理は [ARCHITECTURE.md](ARCHITECTURE.md) を参照してください。
本番では Web サイト用と価格収集用に別のデータベースアカウントを作成し、次のコマンドで権限を付与します。

```bash
python -m app.db.migrate --web-role <web account> --collector-role <collector account>
```

## 広告配信の設定

`.env` で有効化:
```
AD_ENABLED=true
AD_PROVIDER=google_adsense  # または他のプロバイダー
AD_CLIENT_ID=ca-pub-xxxxxxxx
AD_SLOT_ID=xxxxxx
```

フロントエンドの `index.html` に広告スクリプトを追加。

## トラブルシューティング

### データベース接続エラー
```bash
# PostgreSQLコンテナの確認
docker compose ps
docker compose logs db

# データベースリセット（注意: データが消えます）
docker compose down -v
docker compose up -d db
docker compose run --rm migrate
```
