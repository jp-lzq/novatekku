from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, ForeignKey, Index, Text, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Product(Base):
    """iPhone製品モデル"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    jan_code = Column(String(13), unique=True, index=True, nullable=True)  # JANコード
    name = Column(String(255), index=True, nullable=False)  # 製品名
    brand = Column(String(50), default="Apple")  # メーカー
    model = Column(String(100), nullable=False)  # モデル名（iPhone 17 Pro Max等）
    capacity = Column(String(20), nullable=True)  # 容量（128GB, 256GB等）
    color = Column(String(50), nullable=True)  # カラー
    carrier = Column(String(50), nullable=True)  # キャリア（SIMフリー, docomo等）
    condition = Column(String(50), default="新品")  # 状態（新品, 中古A, 中古B等）
    image_url = Column(String(500), nullable=True)  # 製品画像URL
    retail_price = Column(Integer, nullable=True)  # 公式価格（新品時の価格）
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 作成日時
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # 更新日時
    
    # リレーションシップ
    prices = relationship("Price", back_populates="product", cascade="all, delete-orphan")
    daily_highs = relationship("DailyHighPrice", back_populates="product", order_by="DailyHighPrice.date.desc()")

class Store(Base):
    """買取店舗モデル"""
    __tablename__ = "stores"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # 店舗名
    name_kana = Column(String(100), nullable=True)  # 店舗名カナ
    logo_url = Column(String(500), nullable=True)  # ロゴ画像URL
    website_url = Column(String(500), nullable=True)  # 公式サイトURL
    is_active = Column(Integer, default=1)  # 有効フラグ
    priority = Column(Integer, default=0)  # 表示順
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 作成日時
    
    # リレーションシップ
    prices = relationship("Price", back_populates="store")

    @property
    def address(self):
        from app.db.store_metadata import get_store_metadata

        return get_store_metadata(self.name).get("address")

    @property
    def phone(self):
        from app.db.store_metadata import get_store_metadata

        return get_store_metadata(self.name).get("phone")

    @property
    def summary(self):
        from app.db.store_metadata import get_store_metadata

        return get_store_metadata(self.name).get("summary")

    @property
    def is_sponsored(self):
        from app.db.store_metadata import get_store_metadata

        return get_store_metadata(self.name).get("is_sponsored", False)

class Member(Base):
    """会員登録モデル"""
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, index=True, nullable=False)  # ユーザー名
    email = Column(String(255), unique=True, index=True, nullable=False)  # メールアドレス
    password_hash = Column(String(255), nullable=True)  # パスワードハッシュ
    status = Column(String(20), default="active", nullable=False)  # 会員ステータス
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 登録日時
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # 更新日時

    sessions = relationship("MemberSession", back_populates="member", cascade="all, delete-orphan")
    password_reset_tokens = relationship(
        "PasswordResetToken",
        back_populates="member",
        cascade="all, delete-orphan",
    )
    ai_usage = relationship(
        "MemberAIUsage",
        back_populates="member",
        cascade="all, delete-orphan",
        uselist=False,
    )
    login_events = relationship("MemberLoginEvent", back_populates="member", cascade="all, delete-orphan")
    ai_conversations = relationship("AIConversationLog", back_populates="member", cascade="all, delete-orphan")


class MemberAuthControl(Base):
    """管理画面から切り替える会員ログイン・登録の緊急停止状態。"""
    __tablename__ = "member_auth_control"

    id = Column(Integer, primary_key=True, default=1)
    enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by_member_id = Column(Integer, ForeignKey("members.id", ondelete="SET NULL"), nullable=True)


class MemberSession(Base):
    """HttpOnly Cookie と紐づくサーバー側会員セッション。"""
    __tablename__ = "member_sessions"

    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    csrf_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    member = relationship("Member", back_populates="sessions")


class PasswordResetToken(Base):
    """一度だけ利用できるパスワード再設定トークン。"""
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)

    member = relationship("Member", back_populates="password_reset_tokens")


class MemberAIUsage(Base):
    """会員ごとの無料 AI 相談回数（端末やブラウザをまたいで保持）。"""
    __tablename__ = "member_ai_usage"

    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"), primary_key=True)
    used_count = Column(Integer, nullable=False, default=0, server_default="0")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    member = relationship("Member", back_populates="ai_usage")


class MemberLoginEvent(Base):
    """会員登録・ログインの監査記録。"""
    __tablename__ = "member_login_events"

    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(20), nullable=False, index=True)  # register / login
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    member = relationship("Member", back_populates="login_events")


class AIConversationLog(Base):
    """管理画面で確認する NOVA AI の質問・回答履歴。"""
    __tablename__ = "ai_conversation_logs"

    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey("members.id", ondelete="CASCADE"), nullable=True, index=True)
    session_hash = Column(String(64), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    language = Column(String(10), nullable=True)
    ip_address = Column(String(64), nullable=True, index=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    member = relationship("Member", back_populates="ai_conversations")


class CollectionSource(Base):
    """価格収集元の設定。収集先の URL はコードではなくこの表で管理する。"""
    __tablename__ = "collection_sources"

    id = Column(Integer, primary_key=True)
    kind = Column(String(20), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    store_name = Column(String(100), nullable=True, index=True)
    parser = Column(String(80), nullable=True)
    urls = Column(Text, nullable=False, default="[]", server_default="[]")  # JSON array
    public_url = Column(String(1000), nullable=True)
    options = Column(Text, nullable=True)  # JSON object
    unsupported_reason = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True, server_default="true")
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("kind", "name", name="uix_collection_source_kind_name"),
    )


class CollectionRun(Base):
    """表計算シート・公式サイト価格収集の実行記録。"""
    __tablename__ = "collection_runs"

    id = Column(Integer, primary_key=True)
    source_type = Column(String(20), nullable=False, index=True)  # sheet / official
    source_name = Column(String(255), nullable=True)
    store_name = Column(String(100), nullable=True, index=True)
    source_url = Column(String(1000), nullable=True)
    status = Column(String(20), nullable=False, default="running", server_default="running", index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    items_found = Column(Integer, nullable=False, default=0, server_default="0")
    prices_saved = Column(Integer, nullable=False, default=0, server_default="0")
    error_message = Column(Text, nullable=True)
    detail = Column(Text, nullable=True)


class PriceCollectionSource(Base):
    """保存価格を、実際に取得した収集実行へ結び付ける。"""
    __tablename__ = "price_collection_sources"

    id = Column(Integer, primary_key=True)
    price_id = Column(Integer, ForeignKey("prices.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    run_id = Column(Integer, ForeignKey("collection_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String(20), nullable=False, index=True)
    source_url = Column(String(1000), nullable=True)
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class OfficialStoreProduct(Base):
    """公式サイトから取得した店舗別のiPhone商品スナップショット。"""
    __tablename__ = "official_store_products"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id = Column(Integer, ForeignKey("collection_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    model = Column(String(100), nullable=False, index=True)
    capacity = Column(String(20), nullable=False)
    product_name = Column(String(500), nullable=False)
    jan_code = Column(String(32), nullable=True, index=True)
    price = Column(Integer, nullable=False)
    source_url = Column(String(1000), nullable=True)
    collected_at = Column(DateTime(timezone=True), nullable=False, index=True)

    __table_args__ = (
        Index("ix_official_store_products_store_run", "store_id", "run_id"),
        Index("ix_official_store_products_store_model", "store_id", "model", "capacity"),
    )


class ProductVariant(Base):
    """NOVA標準商品庫の機種・容量・カラー別商品。"""
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    color_code = Column(String(80), nullable=False)
    color_name_ja = Column(String(100), nullable=False)
    color_name_en = Column(String(100), nullable=False)
    color_name_zh = Column(String(100), nullable=False)
    jan_code = Column(String(13), unique=True, nullable=True, index=True)
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("product_id", "color_code", name="uix_product_variant_color"),
        Index("ix_product_variants_product_sort", "product_id", "sort_order"),
    )


class ProductVariantIdentifier(Base):
    """JANやApple型番など、標準カラー商品を特定する固定識別子。"""
    __tablename__ = "product_variant_identifiers"

    id = Column(Integer, primary_key=True)
    product_variant_id = Column(
        Integer,
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identifier_type = Column(String(40), nullable=False)  # jan / apple_part_number
    identifier_value = Column(String(100), nullable=False)
    source = Column(String(40), nullable=False, default="catalog", server_default="catalog")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("identifier_type", "identifier_value", name="uix_product_variant_identifier"),
        Index("ix_product_variant_identifier_variant", "product_variant_id", "identifier_type"),
    )


class OfficialProductMapping(Base):
    """店舗の公式商品をNOVA標準商品・カラーへ対応付けた永続マッピング。"""
    __tablename__ = "official_product_mappings"

    id = Column(Integer, primary_key=True)
    official_product_id = Column(
        Integer,
        ForeignKey("official_store_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    product_variant_id = Column(
        Integer,
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mapping_method = Column(String(40), nullable=False)  # jan / embedded_jan / apple_part_number / color_name / all_colors
    confidence = Column(Integer, nullable=False, default=0, server_default="0")
    matcher_version = Column(String(40), nullable=False, default="catalog-v2", server_default="catalog-v2")
    offer_condition = Column(String(30), nullable=False, default="unspecified", server_default="unspecified")
    is_default_color_price = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "official_product_id",
            "product_variant_id",
            name="uix_official_product_variant_mapping",
        ),
        Index("ix_official_product_mapping_product", "product_id", "product_variant_id"),
    )


class StoreProductPrice(Base):
    """公式サイト・表データを標準商品へ対応付けた現在価格。"""
    __tablename__ = "store_product_prices"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    product_variant_id = Column(
        Integer,
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source_type = Column(String(20), nullable=False, index=True)  # official / sheet
    price = Column(Integer, nullable=False)
    source_name = Column(String(500), nullable=True)
    source_url = Column(String(1000), nullable=True)
    run_id = Column(Integer, ForeignKey("collection_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    collected_at = Column(DateTime(timezone=True), nullable=False, index=True)

    __table_args__ = (
        Index(
            "ix_store_product_prices_lookup",
            "store_id",
            "product_id",
            "product_variant_id",
            "source_type",
        ),
        Index("ix_store_product_prices_fresh", "collected_at", "source_type"),
    )

class Price(Base):
    """買取価格モデル"""
    __tablename__ = "prices"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)  # 製品ID
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)  # 店舗ID
    price = Column(Integer, nullable=False)  # 買取価格（円）
    price_change = Column(Integer, default=0)  # 前回比の価格変動
    price_change_percent = Column(Float, default=0.0)  # 変動率（%）
    is_best_price = Column(Integer, default=0)  # 最高価格フラグ
    url = Column(String(1000), nullable=True)  # 買取ページURL
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())  # スクレイピング日時
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 作成日時
    
    # リレーションシップ
    product = relationship("Product", back_populates="prices")
    store = relationship("Store", back_populates="prices")
    
    # インデックス
    __table_args__ = (
        Index('ix_prices_product_store', 'product_id', 'store_id'),
        Index('ix_prices_scraped_at', 'scraped_at'),
    )
    
    @property
    def profit(self):
        """利益 = 買取価格 - 公式価格"""
        if self.product and self.product.retail_price:
            return self.price - self.product.retail_price
        return None
    
    @property
    def profit_percent(self):
        """利益率（%）"""
        if self.product and self.product.retail_price and self.product.retail_price > 0:
            return round((self.price - self.product.retail_price) / self.product.retail_price * 100, 2)
        return None

class PriceHistory(Base):
    """価格履歴モデル"""
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)  # 製品ID
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)  # 店舗ID
    price = Column(Integer, nullable=False)  # 買取価格
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())  # 記録日時
    
    # インデックス
    __table_args__ = (
        Index('ix_price_history_product_store_date', 'product_id', 'store_id', 'recorded_at'),
    )

class DailyHighPrice(Base):
    """每日最高価格履歴 - K線チャート用"""
    __tablename__ = "daily_high_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    
    # K線データ
    open_price = Column(Integer)   # 始値（その日の最初の最高価格）
    high_price = Column(Integer)   # 高値（その日の最高価格）
    low_price = Column(Integer)    # 安値（その日の最低価格）
    close_price = Column(Integer)  # 終値（その日の最後の最高価格）
    
    # ベストストア情報
    best_store_name = Column(String(100))  # 最高価格の店舗名
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーションシップ
    product = relationship("Product", back_populates="daily_highs")
    
    __table_args__ = (
        UniqueConstraint('product_id', 'date', name='uix_daily_high'),
    )
