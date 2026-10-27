"""Ad slots shown on the website.  Copy and links come from the site_ads table."""
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.db.models import SiteAd
from app.db.session import get_db

router = APIRouter()

MAX_ADS_PER_SLOT = 6


def _safe_href(href: str) -> bool:
    parts = urlsplit(href or "")
    return parts.scheme == "https" and bool(parts.netloc)


@router.get("/ads")
def list_ads(response: Response, slot: str = Query(..., pattern=r"^[a-z0-9_]{1,40}$"), db: Session = Depends(get_db)):
    rows = (
        db.query(SiteAd)
        .filter(SiteAd.slot == slot, SiteAd.enabled.is_(True))
        .order_by(SiteAd.sort_order, SiteAd.id)
        .all()
    )
    response.headers["Cache-Control"] = "public, max-age=300"
    return {
        "slot": slot,
        "ads": [
            {
                "key": row.key,
                "icon": row.icon,
                "brand": row.brand,
                "text": {"ja": row.text_ja, "zh": row.text_zh, "en": row.text_en},
                "href": row.href,
            }
            for row in rows
            if _safe_href(row.href)  # never hand a javascript: or http: link to the page
        ][:MAX_ADS_PER_SLOT],
    }
