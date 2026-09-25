from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Price, Product
from app.pricing.current_prices import latest_prices_query
from app.web.routers.common import price_to_dict
from app.web.routers.members import AuthContext, require_admin

router = APIRouter()


# Search
@router.get("/search")
def search_products(
    q: str = Query(..., min_length=1),
    _: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db)
):
    products = db.query(Product).filter(
        Product.name.ilike(f"%{q}%") | Product.model.ilike(f"%{q}%")
    ).limit(20).all()

    results = []
    for product in products:
        prices = (
            latest_prices_query(db)
            .filter(Price.product_id == product.id)
            .order_by(desc(Price.price))
            .limit(20)
            .all()
        )
        latest_prices = [price_to_dict(price) for price in prices]

        best_price_val = max([p['price'] for p in latest_prices]) if latest_prices else None
        results.append({
            "product": product,
            "best_price": best_price_val,
            "store_count": len(latest_prices),
            "prices": latest_prices
        })

    return results
