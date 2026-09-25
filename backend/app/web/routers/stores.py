from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Store
from app.web.schemas import Store as StoreSchema
from app.db.store_metadata import get_store_metadata

router = APIRouter()


# Stores
@router.get("/stores", response_model=List[StoreSchema])
def get_stores(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    stores = db.query(Store).filter(Store.is_active == 1).order_by(Store.priority.desc()).offset(skip).limit(limit).all()
    results = []
    for store in stores:
        metadata = get_store_metadata(store.name)
        results.append({
            "id": store.id,
            "name": store.name,
            "name_kana": store.name_kana,
            "logo_url": store.logo_url,
            "website_url": store.website_url or metadata.get("website_url"),
            "address": metadata.get("address"),
            "phone": metadata.get("phone"),
            "summary": metadata.get("summary"),
            "is_sponsored": metadata.get("is_sponsored", False),
            "is_active": store.is_active,
            "priority": store.priority,
            "created_at": store.created_at,
        })
    return results

@router.get("/stores/{store_id}", response_model=StoreSchema)
def get_store(store_id: int, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    metadata = get_store_metadata(store.name)
    return {
        "id": store.id,
        "name": store.name,
        "name_kana": store.name_kana,
        "logo_url": store.logo_url,
        "website_url": store.website_url or metadata.get("website_url"),
        "address": metadata.get("address"),
        "phone": metadata.get("phone"),
        "summary": metadata.get("summary"),
        "is_sponsored": metadata.get("is_sponsored", False),
        "is_active": store.is_active,
        "priority": store.priority,
        "created_at": store.created_at,
    }
