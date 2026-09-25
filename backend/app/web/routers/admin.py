from datetime import timedelta

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import (
    AIConversationLog,
    CollectionRun,
    Member,
    MemberAIUsage,
    MemberLoginEvent,
    MemberSession,
    OfficialProductMapping,
    OfficialStoreProduct,
    Price,
    PriceCollectionSource,
    Product,
    ProductVariant,
    Store,
    StoreProductPrice,
)
from app.web.routers.members import (
    AuthContext,
    CSRF_COOKIE,
    MEMBER_AI_LIMIT,
    enforce_trusted_origin,
    require_admin,
    require_csrf,
)
from app.web.schemas import MemberAuthControlUpdate
from app.web.services.member_auth_control import member_auth_control_payload, set_member_auth_enabled
from app.pricing.product_catalog import normalize_capacity as normalize_catalog_capacity

router = APIRouter(prefix="/admin", tags=["admin"])


def no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


@router.get("/member-auth")
def admin_member_auth_status(
    response: Response,
    _: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    no_store(response)
    return member_auth_control_payload(db)


@router.post("/member-auth")
def admin_update_member_auth(
    payload: MemberAuthControlUpdate,
    request: Request,
    response: Response,
    context: AuthContext = Depends(require_admin),
    csrf_cookie: str | None = Cookie(default=None, alias=CSRF_COOKIE),
    csrf_header: str | None = Header(default=None, alias="X-NOVA-CSRF"),
    db: Session = Depends(get_db),
):
    enforce_trusted_origin(request)
    require_csrf(context, csrf_cookie, csrf_header)
    result = set_member_auth_enabled(db, payload.enabled, context.member.id)
    no_store(response)
    return result


@router.get("/overview")
def admin_overview(
    response: Response,
    _: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    no_store(response)
    latest_runs = db.query(CollectionRun).order_by(CollectionRun.started_at.desc()).limit(12).all()
    return {
        "members": db.query(func.count(Member.id)).scalar() or 0,
        "price_records": db.query(func.count(Price.id)).scalar() or 0,
        "latest_price_at": db.query(func.max(Price.scraped_at)).scalar(),
        "latest_runs": [_run_payload(run) for run in latest_runs],
    }


@router.get("/prices")
def admin_prices(
    response: Response,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    source_type: str | None = Query(default=None, pattern="^(sheet|official|unknown)$"),
    _: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    no_store(response)
    query = db.query(Price, Product, Store, PriceCollectionSource).join(
        Product, Product.id == Price.product_id
    ).join(
        Store, Store.id == Price.store_id
    ).outerjoin(
        PriceCollectionSource, PriceCollectionSource.price_id == Price.id
    )
    if source_type == "official":
        query = query.filter(PriceCollectionSource.source_type == "official")
    elif source_type == "sheet":
        query = query.filter(PriceCollectionSource.source_type == "sheet")
    elif source_type == "unknown":
        query = query.filter(PriceCollectionSource.id.is_(None))
    rows = query.order_by(Price.scraped_at.desc(), Price.id.desc()).offset(offset).limit(limit).all()
    return {
        "items": [
            {
                "id": price.id,
                "product": f"{product.model} {product.capacity or ''}".strip(),
                "store": store.name,
                "price": price.price,
                "scraped_at": price.scraped_at,
                "source_type": source.source_type if source else "unknown",
                "source_url": source.source_url if source else price.url,
                "run_id": source.run_id if source else None,
            }
            for price, product, store, source in rows
        ],
        "limit": limit,
        "offset": offset,
    }


@router.get("/members")
def admin_members(
    response: Response,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    no_store(response)
    members = db.query(Member).order_by(Member.created_at.desc(), Member.id.desc()).offset(offset).limit(limit).all()
    items = []
    for member in members:
        first_event_at = db.query(func.min(MemberLoginEvent.created_at)).filter(
            MemberLoginEvent.member_id == member.id,
        ).scalar()
        event_count = db.query(func.count(MemberLoginEvent.id)).filter(
            MemberLoginEvent.member_id == member.id,
        ).scalar() or 0
        event_latest = db.query(func.max(MemberLoginEvent.created_at)).filter(
            MemberLoginEvent.member_id == member.id,
        ).scalar()

        legacy_sessions = db.query(MemberSession).filter(MemberSession.member_id == member.id)
        if first_event_at is not None:
            legacy_sessions = legacy_sessions.filter(MemberSession.created_at < first_event_at - timedelta(seconds=5))
        legacy_count = legacy_sessions.count()
        legacy_latest = legacy_sessions.with_entities(func.max(MemberSession.created_at)).scalar()
        latest_candidates = [value for value in (event_latest, legacy_latest) if value is not None]

        usage = db.get(MemberAIUsage, member.id)
        used_count = min(max(int(usage.used_count if usage else 0), 0), MEMBER_AI_LIMIT)
        items.append({
            "id": member.id,
            "username": member.username,
            "email": member.email,
            "status": member.status,
            "created_at": member.created_at,
            "last_login_at": max(latest_candidates) if latest_candidates else None,
            "login_count": int(event_count) + int(legacy_count),
            "ai_used": used_count,
            "ai_remaining": MEMBER_AI_LIMIT - used_count,
        })
    return {
        "items": items,
        "total": db.query(func.count(Member.id)).scalar() or 0,
        "limit": limit,
        "offset": offset,
    }


@router.get("/members/{member_id}/logins")
def admin_member_logins(
    member_id: int,
    response: Response,
    limit: int = Query(default=200, ge=1, le=500),
    _: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    no_store(response)
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    events = db.query(MemberLoginEvent).filter(
        MemberLoginEvent.member_id == member_id,
    ).order_by(MemberLoginEvent.created_at.desc(), MemberLoginEvent.id.desc()).limit(limit).all()
    first_event_at = db.query(func.min(MemberLoginEvent.created_at)).filter(
        MemberLoginEvent.member_id == member_id,
    ).scalar()
    sessions_query = db.query(MemberSession).filter(MemberSession.member_id == member_id)
    if first_event_at is not None:
        sessions_query = sessions_query.filter(MemberSession.created_at < first_event_at - timedelta(seconds=5))
    sessions = sessions_query.order_by(MemberSession.created_at.desc(), MemberSession.id.desc()).limit(limit).all()

    records = [
        {
            "id": f"event-{event.id}",
            "event_type": event.event_type,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "created_at": event.created_at,
            "expires_at": None,
            "revoked_at": None,
        }
        for event in events
    ]
    records.extend(
        {
            "id": f"session-{session.id}",
            "event_type": "legacy_session",
            "ip_address": None,
            "user_agent": None,
            "created_at": session.created_at,
            "expires_at": session.expires_at,
            "revoked_at": session.revoked_at,
        }
        for session in sessions
    )
    records.sort(key=lambda record: record["created_at"], reverse=True)
    return {
        "member": {
            "id": member.id,
            "username": member.username,
            "email": member.email,
            "status": member.status,
            "created_at": member.created_at,
        },
        "items": records[:limit],
    }


@router.get("/price-stores")
def admin_price_stores(
    response: Response,
    _: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    no_store(response)
    catalog_rows = db.query(
        OfficialStoreProduct.store_id,
        func.count(OfficialStoreProduct.id).label("catalog_count"),
    ).group_by(OfficialStoreProduct.store_id).all()
    catalog_by_store = {row.store_id: int(row.catalog_count or 0) for row in catalog_rows}
    mapping_rows = db.query(
        OfficialStoreProduct.store_id,
        func.count(func.distinct(OfficialProductMapping.official_product_id)).label("mapped_count"),
        func.count(OfficialProductMapping.id).label("variant_count"),
    ).join(
        OfficialProductMapping,
        OfficialProductMapping.official_product_id == OfficialStoreProduct.id,
    ).group_by(OfficialStoreProduct.store_id).all()
    mapping_by_store = {
        row.store_id: {
            "mapped_count": int(row.mapped_count or 0),
            "variant_count": int(row.variant_count or 0),
        }
        for row in mapping_rows
    }
    normalized_rows = db.query(
        StoreProductPrice.store_id,
        StoreProductPrice.source_type,
        func.count(StoreProductPrice.id).label("price_count"),
        func.max(StoreProductPrice.collected_at).label("latest_at"),
    ).group_by(
        StoreProductPrice.store_id,
        StoreProductPrice.source_type,
    ).all()
    normalized_by_store: dict[int, dict[str, dict]] = {}
    for row in normalized_rows:
        normalized_by_store.setdefault(row.store_id, {})[row.source_type] = {
            "count": int(row.price_count or 0),
            "latest_at": row.latest_at,
        }
    if normalized_rows:
        source_rows = db.query(
            StoreProductPrice.store_id,
            func.count(func.distinct(StoreProductPrice.product_id)).label("product_count"),
            func.max(StoreProductPrice.collected_at).label("latest_at"),
        ).group_by(StoreProductPrice.store_id).all()
        source_by_store = {
            row.store_id: {"product_count": int(row.product_count or 0), "latest_at": row.latest_at}
            for row in source_rows
        }
        fallback_by_store: dict[int, dict[str, int]] = {}
    else:
        source_rows = db.query(
            Price.store_id,
            func.count(func.distinct(Price.product_id)).label("product_count"),
            func.max(PriceCollectionSource.collected_at).label("latest_at"),
        ).join(
            PriceCollectionSource, PriceCollectionSource.price_id == Price.id
        ).filter(
            PriceCollectionSource.source_type.in_(("official", "sheet")),
        ).group_by(Price.store_id).all()
        source_by_store = {
            row.store_id: {"product_count": int(row.product_count or 0), "latest_at": row.latest_at}
            for row in source_rows
        }
        fallback_source_counts = db.query(
            Price.store_id,
            PriceCollectionSource.source_type,
            func.count(func.distinct(Price.product_id)).label("price_count"),
        ).join(
            PriceCollectionSource, PriceCollectionSource.price_id == Price.id
        ).filter(
            PriceCollectionSource.source_type.in_(("official", "sheet")),
        ).group_by(
            Price.store_id,
            PriceCollectionSource.source_type,
        ).all()
        fallback_by_store = {}
        for row in fallback_source_counts:
            fallback_by_store.setdefault(row.store_id, {})[row.source_type] = int(row.price_count or 0)
    stores = db.query(Store).filter(Store.is_active == 1).order_by(Store.priority.desc(), Store.name.asc()).all()
    return {
        "items": [
            {
                "id": store.id,
                "name": store.name,
                "website_url": store.website_url,
                "official_catalog_count": catalog_by_store.get(store.id, 0),
                "official_price_count": catalog_by_store.get(store.id, 0),
                "official_mapped_count": mapping_by_store.get(store.id, {}).get("mapped_count", 0),
                "official_standard_variant_count": mapping_by_store.get(store.id, {}).get("variant_count", 0),
                "official_unmapped_count": max(
                    0,
                    catalog_by_store.get(store.id, 0)
                    - mapping_by_store.get(store.id, {}).get("mapped_count", 0),
                ),
                "sheet_price_count": normalized_by_store.get(store.id, {}).get("sheet", {}).get(
                    "count", fallback_by_store.get(store.id, {}).get("sheet", 0)
                ),
                **source_by_store.get(store.id, {"product_count": 0, "latest_at": None}),
            }
            for store in stores
        ]
    }


@router.get("/price-stores/{store_id}")
def admin_store_prices(
    store_id: int,
    response: Response,
    _: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    no_store(response)
    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    normalized_rows = db.query(StoreProductPrice, Product, ProductVariant).join(
        Product, Product.id == StoreProductPrice.product_id
    ).outerjoin(
        ProductVariant, ProductVariant.id == StoreProductPrice.product_variant_id
    ).filter(
        StoreProductPrice.store_id == store_id,
        StoreProductPrice.source_type.in_(("official", "sheet")),
    ).order_by(
        StoreProductPrice.collected_at.desc(),
        StoreProductPrice.price.desc(),
    ).all()

    if normalized_rows:
        products: dict[int, dict] = {}
        for price, product, variant in normalized_rows:
            item = products.setdefault(product.id, {
                "product_id": product.id,
                "product": f"{product.model} {product.capacity or ''}".strip(),
                "model": product.model,
                "capacity": product.capacity,
                "official": None,
                "sheet": None,
            })
            current = item[price.source_type]
            candidate = {
                "price": price.price,
                "updated_at": price.collected_at,
                "source_url": price.source_url,
                "color_name_ja": variant.color_name_ja if variant else None,
                "is_default_color_price": variant is None,
            }
            if current is None or candidate["price"] > current["price"]:
                item[price.source_type] = candidate

        official_count = db.query(func.count(OfficialStoreProduct.id)).filter(
            OfficialStoreProduct.store_id == store_id,
        ).scalar() or 0
        sheet_count = db.query(func.count(StoreProductPrice.id)).filter(
            StoreProductPrice.store_id == store_id,
            StoreProductPrice.source_type == "sheet",
        ).scalar() or 0
        return {
            "store": {
                "id": store.id,
                "name": store.name,
                "website_url": store.website_url,
            },
            "official_price_count": int(official_count),
            "sheet_price_count": int(sheet_count),
            "items": sorted(products.values(), key=lambda item: (item["model"], item["capacity"] or "")),
        }

    latest_source = db.query(
        Price.product_id.label("product_id"),
        PriceCollectionSource.source_type.label("source_type"),
        func.max(PriceCollectionSource.collected_at).label("latest_at"),
    ).join(
        PriceCollectionSource, PriceCollectionSource.price_id == Price.id
    ).filter(
        Price.store_id == store_id,
        PriceCollectionSource.source_type.in_(("official", "sheet")),
    ).group_by(
        Price.product_id,
        PriceCollectionSource.source_type,
    ).subquery()

    rows = db.query(Price, Product, PriceCollectionSource).join(
        Product, Product.id == Price.product_id
    ).join(
        PriceCollectionSource, PriceCollectionSource.price_id == Price.id
    ).join(
        latest_source,
        (latest_source.c.product_id == Price.product_id)
        & (latest_source.c.source_type == PriceCollectionSource.source_type)
        & (latest_source.c.latest_at == PriceCollectionSource.collected_at),
    ).filter(
        Price.store_id == store_id,
        PriceCollectionSource.source_type.in_(("official", "sheet")),
    ).order_by(
        PriceCollectionSource.collected_at.desc(),
        Price.id.desc(),
    ).all()

    products: dict[int, dict] = {}
    for price, product, source in rows:
        item = products.setdefault(product.id, {
            "product_id": product.id,
            "product": f"{product.model} {product.capacity or ''}".strip(),
            "model": product.model,
            "capacity": product.capacity,
            "official": None,
            "sheet": None,
        })
        if item[source.source_type] is None:
            item[source.source_type] = {
                "price": price.price,
                "updated_at": source.collected_at or price.scraped_at,
                "source_url": source.source_url or price.url,
            }

    return {
        "store": {
            "id": store.id,
            "name": store.name,
            "website_url": store.website_url,
        },
        "official_price_count": db.query(func.count(OfficialStoreProduct.id)).filter(
            OfficialStoreProduct.store_id == store_id,
        ).scalar() or 0,
        "sheet_price_count": sum(1 for item in products.values() if item["sheet"] is not None),
        "items": sorted(products.values(), key=lambda item: (item["model"], item["capacity"] or "")),
    }


@router.get("/price-stores/{store_id}/official-products")
def admin_store_official_products(
    store_id: int,
    response: Response,
    _: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    no_store(response)
    store = db.get(Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    source_product_count = db.query(func.count(OfficialStoreProduct.id)).filter(
        OfficialStoreProduct.store_id == store_id,
    ).scalar() or 0
    rows = db.query(
        OfficialProductMapping,
        OfficialStoreProduct,
        Product,
        ProductVariant,
    ).join(
        OfficialStoreProduct,
        OfficialStoreProduct.id == OfficialProductMapping.official_product_id,
    ).join(
        Product,
        Product.id == OfficialProductMapping.product_id,
    ).join(
        ProductVariant,
        ProductVariant.id == OfficialProductMapping.product_variant_id,
    ).filter(
        OfficialStoreProduct.store_id == store_id,
    ).order_by(
        Product.model.asc(),
        Product.capacity.asc(),
        ProductVariant.sort_order.asc(),
        OfficialStoreProduct.product_name.asc(),
    ).all()
    mapped_source_count = len({official.id for _mapping, official, _product, _variant in rows})

    return {
        "store": {"id": store.id, "name": store.name},
        "source_product_count": int(source_product_count),
        "mapped_source_count": mapped_source_count,
        "standard_variant_count": len(rows),
        "unmapped_source_count": max(0, int(source_product_count) - mapped_source_count),
        "items": [
            {
                "id": mapping.id,
                "source_product_id": row.id,
                "product_id": product.id,
                "model": product.model,
                "capacity": normalize_catalog_capacity(product.capacity),
                "standard_product": f"{product.model} {normalize_catalog_capacity(product.capacity)}".strip(),
                "product_name": row.product_name,
                "source_jan_code": row.jan_code,
                "jan_code": variant.jan_code,
                "price": row.price,
                "source_url": row.source_url,
                "collected_at": row.collected_at,
                "run_id": row.run_id,
                "mapping_method": mapping.mapping_method,
                "mapping_confidence": mapping.confidence,
                "matcher_version": mapping.matcher_version,
                "offer_condition": mapping.offer_condition,
                "is_default_color_price": bool(mapping.is_default_color_price),
                "variant": {
                    "id": variant.id,
                    "color_code": variant.color_code,
                    "color_name_ja": variant.color_name_ja,
                    "color_name_en": variant.color_name_en,
                    "color_name_zh": variant.color_name_zh,
                },
            }
            for mapping, row, product, variant in rows
        ],
    }


@router.get("/ai-history")
def admin_ai_history(
    response: Response,
    actor: str = Query(default="all", pattern="^(all|member|guest)$"),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    no_store(response)
    query = db.query(AIConversationLog, Member).outerjoin(Member, Member.id == AIConversationLog.member_id)
    if actor == "member":
        query = query.filter(AIConversationLog.member_id.is_not(None))
    elif actor == "guest":
        query = query.filter(AIConversationLog.member_id.is_(None))
    total = query.with_entities(func.count(AIConversationLog.id)).scalar() or 0
    rows = query.order_by(
        AIConversationLog.created_at.desc(),
        AIConversationLog.id.desc(),
    ).offset(offset).limit(limit).all()
    return {
        "items": [
            {
                "id": conversation.id,
                "member_id": conversation.member_id,
                "username": member.username if member else None,
                "email": member.email if member else None,
                "ip_address": conversation.ip_address,
                "question": conversation.question,
                "answer": conversation.answer,
                "language": conversation.language,
                "created_at": conversation.created_at,
            }
            for conversation, member in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/collection-runs")
def admin_collection_runs(
    response: Response,
    limit: int = Query(default=100, ge=1, le=500),
    source_type: str | None = Query(default=None, pattern="^(sheet|official)$"),
    _: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    no_store(response)
    query = db.query(CollectionRun)
    if source_type:
        query = query.filter(CollectionRun.source_type == source_type)
    runs = query.order_by(CollectionRun.started_at.desc()).limit(limit).all()
    return {"items": [_run_payload(run) for run in runs]}


def _run_payload(run: CollectionRun) -> dict:
    return {
        "id": run.id,
        "source_type": run.source_type,
        "source_name": run.source_name,
        "store_name": run.store_name,
        "source_url": run.source_url,
        "status": run.status,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "items_found": run.items_found,
        "prices_saved": run.prices_saved,
        "error_message": run.error_message,
        "detail": run.detail,
    }
