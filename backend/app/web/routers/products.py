from typing import List, Optional

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Product
from app.web.routers.members import AuthContext, CSRF_COOKIE, enforce_trusted_origin, require_admin, require_csrf
from app.web.schemas import Product as ProductSchema, ProductCreate

router = APIRouter()


# Products
@router.get("/products", response_model=List[ProductSchema])
def get_products(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    model: Optional[str] = None,
    search: Optional[str] = None,
    _: AuthContext = Depends(require_admin),
):
    query = db.query(Product)
    if model:
        query = query.filter(Product.model.ilike(f"%{model}%"))
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    products = query.offset(skip).limit(limit).all()
    return products

@router.get("/products/{product_id}", response_model=ProductSchema)
def get_product(
    product_id: int,
    _: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/products", response_model=ProductSchema)
def create_product(
    product: ProductCreate,
    request: Request,
    context: AuthContext = Depends(require_admin),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-NOVA-CSRF"),
    db: Session = Depends(get_db),
):
    enforce_trusted_origin(request)
    require_csrf(context, csrf_cookie, csrf_header)
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product
