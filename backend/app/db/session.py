from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# データベース接続URL（環境変数から取得、未設定時は占位値）
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://app_user:change_me@localhost:5432/nova_kaitori")

# データベースエンジン作成
engine = create_engine(DATABASE_URL)

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
