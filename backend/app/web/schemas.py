from pydantic import BaseModel, ConfigDict, model_validator
from typing import Optional, List
from datetime import datetime

# Store Schemas
class StoreBase(BaseModel):
    name: str
    name_kana: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    summary: Optional[str] = None
    is_sponsored: bool = False
    is_active: int = 1
    priority: int = 0

class StoreCreate(StoreBase):
    pass

class Store(StoreBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime

# Member Schemas
class MemberRegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class MemberLoginRequest(BaseModel):
    identifier: Optional[str] = None
    email: Optional[str] = None
    password: str

    @model_validator(mode="after")
    def require_identifier(self):
        if not (self.identifier or self.email):
            raise ValueError("Username or email is required")
        return self

class MemberPasswordResetRequest(BaseModel):
    email: str

class MemberPasswordResetConfirm(BaseModel):
    token: str
    password: str

class MemberChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class MemberProfileUpdateRequest(BaseModel):
    username: str
    email: str
    current_password: str

class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    status: str
    created_at: datetime
    is_admin: bool = False
    ai_remaining: int = 100

class MessageResponse(BaseModel):
    message: str

class PasswordResetAvailabilityResponse(BaseModel):
    enabled: bool


class MemberAuthControlUpdate(BaseModel):
    enabled: bool

# Product Schemas
class ProductBase(BaseModel):
    jan_code: Optional[str] = None
    name: str
    brand: str = "Apple"
    model: str
    capacity: Optional[str] = None
    color: Optional[str] = None
    carrier: Optional[str] = None
    condition: str = "新品"
    image_url: Optional[str] = None
    retail_price: Optional[int] = None  # 定価

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

# Price Schemas
class PriceBase(BaseModel):
    product_id: int
    store_id: int
    price: int
    price_change: int = 0
    price_change_percent: float = 0.0
    is_best_price: int = 0
    url: Optional[str] = None

class PriceCreate(PriceBase):
    pass

class Price(PriceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scraped_at: datetime
    created_at: datetime
    store: Optional[Store] = None
    profit: Optional[int] = None
    profit_percent: Optional[float] = None

# Price with Product info (for listing)
class PriceWithProduct(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    price: int
    price_change: int
    price_change_percent: float
    is_best_price: int
    scraped_at: datetime
    store: Store
    product: Product

# Price History Schema
class PriceHistoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price: int
    recorded_at: datetime

class ProductPriceHistory(BaseModel):
    product: Product
    store: Store
    history: List[PriceHistoryEntry]

# Search/Filter Schemas
class ProductSearchResult(BaseModel):
    product: Product
    best_price: Optional[int] = None
    store_count: int = 0
    prices: List[Price] = []

class PriceFilter(BaseModel):
    product_id: Optional[int] = None
    store_id: Optional[int] = None
    model: Optional[str] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None

# Stats
class PriceStats(BaseModel):
    total_products: int
    total_stores: int
    today_updates: int
    price_changes_24h: int

# AI Chat
class AIChatRequest(BaseModel):
    session_id: str
    message: str
    language: Optional[str] = None

class AIChatResponse(BaseModel):
    reply: str
    remaining: int

class AIUsageResponse(BaseModel):
    authenticated: bool
    limit: int
    used: int
    remaining: int
