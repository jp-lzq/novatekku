from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# データベース接続URL（環境変数から取得、未設定時は占位値）
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://app_user:change_me@localhost:5432/nova_kaitori")


def with_explicit_driver(url: str) -> str:
    """「postgresql://」にドライバを明示する。

    SQLAlchemy 2.1 から既定のドライバが psycopg2 から psycopg（v3）に変わったため、
    入っている psycopg2 を明示しないと接続できなくなる。2.0 でも同じ意味で動く。
    """
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


# データベースエンジン作成
engine = create_engine(with_explicit_driver(DATABASE_URL))

# セッション作成用ファクトリ
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# モデルのベースクラス
Base = declarative_base()

def get_db():
    """データベースセッションを取得するジェネレーター"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
