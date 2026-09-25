

from app.db.models import Price
from app.db.store_metadata import get_store_metadata


def price_to_dict(price: Price) -> dict:
    """価格モデルを辞書に変換（利益情報付き）"""
    store_metadata = get_store_metadata(price.store.name) if price.store else {}
    return {
        "id": price.id,
        "product_id": price.product_id,
        "store_id": price.store_id,
        "price": price.price,
        "price_change": price.price_change,
        "price_change_percent": price.price_change_percent,
        "is_best_price": price.is_best_price,
        "scraped_at": price.scraped_at.isoformat() if price.scraped_at else None,
        "created_at": price.created_at.isoformat() if price.created_at else None,
        "store": {
            "id": price.store.id,
            "name": price.store.name,
            "name_kana": price.store.name_kana,
            "logo_url": price.store.logo_url,
            "website_url": price.store.website_url or store_metadata.get("website_url"),
            "address": store_metadata.get("address"),
            "phone": store_metadata.get("phone"),
            "summary": store_metadata.get("summary"),
            "is_sponsored": store_metadata.get("is_sponsored", False),
            "is_active": price.store.is_active,
            "priority": price.store.priority,
            "created_at": price.store.created_at.isoformat() if price.store.created_at else None,
        } if price.store else None,
        "product": {
            "id": price.product.id,
            "name": price.product.name,
            "model": price.product.model,
            "capacity": price.product.capacity,
            "color": price.product.color,
            "carrier": price.product.carrier,
            "condition": price.product.condition,
            "image_url": price.product.image_url,
            "retail_price": price.product.retail_price,
        } if price.product else None,
        "profit": price.profit,
        "profit_percent": price.profit_percent,
    }


def public_price_to_dict(price: Price) -> dict:
    """Return only the fields rendered by the public price pages."""
    store_metadata = get_store_metadata(price.store.name) if price.store else {}
    return {
        "id": price.id,
        "price": price.price,
        "price_change": price.price_change,
        "price_change_percent": price.price_change_percent,
        "is_best_price": price.is_best_price,
        "scraped_at": price.scraped_at.isoformat() if price.scraped_at else None,
        "store": {
            "id": price.store.id,
            "name": price.store.name,
            "is_sponsored": store_metadata.get("is_sponsored", False),
        } if price.store else None,
        "product": {
            "id": price.product.id,
            "name": price.product.name,
            "model": price.product.model,
            "capacity": price.product.capacity,
            "color": price.product.color,
            "carrier": price.product.carrier,
            "condition": price.product.condition,
            "image_url": price.product.image_url,
            "retail_price": price.product.retail_price,
        } if price.product else None,
        "profit": price.profit,
        "profit_percent": price.profit_percent,
    }
