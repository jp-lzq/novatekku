"""Import the ad slots from a private JSON file into site_ads (owner account).

    python -m app.db.site_ads import ads.json

The file is a list of {slot, key, icon, brand, text: {ja, zh, en}, href,
enabled, sort_order}.  Every slot named in the file is replaced as a whole, so
an ad removed from the file disappears from the site.
"""

import argparse
import json
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from app.db.models import SiteAd
from app.db.session import SessionLocal

ICONS = ("phone", "card", "gift", "link")
LANGUAGES = ("ja", "zh", "en")


def _validate(item: dict) -> dict:
    if not isinstance(item, dict):
        raise ValueError("each ad must be an object")
    text = item.get("text") or {}
    href = str(item.get("href") or "")
    parts = urlsplit(href)
    if parts.scheme != "https" or not parts.netloc:
        raise ValueError(f"{item.get('key')}: href must be an https URL")
    values = {
        "slot": str(item.get("slot") or ""),
        "key": str(item.get("key") or ""),
        "icon": str(item.get("icon") or "link"),
        "brand": str(item.get("brand") or "").strip(),
        "href": href,
        "enabled": bool(item.get("enabled", True)),
        "sort_order": int(item.get("sort_order", 0)),
        **{f"text_{language}": str(text.get(language) or "").strip() for language in LANGUAGES},
    }
    if not values["slot"] or not values["key"] or not values["brand"]:
        raise ValueError("slot, key and brand are required")
    if values["icon"] not in ICONS:
        raise ValueError(f"{values['key']}: icon must be one of {', '.join(ICONS)}")
    if not all(values[f"text_{language}"] for language in LANGUAGES):
        raise ValueError(f"{values['key']}: text needs ja, zh and en")
    return values


def import_ads(db: Session, items: list) -> dict:
    if not isinstance(items, list):
        raise ValueError("the file must contain a list")
    rows = [_validate(item) for item in items]  # validate everything before touching the table
    slots = sorted({row["slot"] for row in rows})
    removed = db.query(SiteAd).filter(SiteAd.slot.in_(slots)).delete(synchronize_session=False) if slots else 0
    db.add_all(SiteAd(**row) for row in rows)
    db.commit()
    return {"slots": slots, "removed": removed, "imported": len(rows)}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.db.site_ads")
    parser.add_argument("command", choices=["import"])
    parser.add_argument("path")
    args = parser.parse_args(argv)
    with open(args.path, encoding="utf-8") as handle:
        items = json.load(handle)
    with SessionLocal() as db:
        print(json.dumps(import_ads(db, items), ensure_ascii=False))


if __name__ == "__main__":
    main()
