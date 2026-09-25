"""Create missing tables, rebuild the standard price index and apply grants.

Run with the owner account (DATABASE_URL) on every deploy:

    python -m app.db.migrate --web-role nova_web --collector-role nova_collector
"""

import argparse
import json

from sqlalchemy import text

from app.db import models  # noqa: F401  (registers every table)
from app.db.roles import COLLECTOR_PRIVILEGES, WEB_PRIVILEGES, apply_grants
from app.db.session import Base, SessionLocal, engine
from app.pricing.product_catalog import rebuild_standard_price_index


def role_exists(connection, role: str) -> bool:
    return bool(connection.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role}).scalar())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.db.migrate")
    parser.add_argument("--web-role")
    parser.add_argument("--collector-role")
    parser.add_argument("--skip-index", action="store_true", help="do not rebuild the standard price index")
    args = parser.parse_args(argv)

    Base.metadata.create_all(bind=engine)
    result = {"tables": sorted(Base.metadata.tables)}
    if not args.skip_index:
        with SessionLocal() as db:
            result["price_index"] = rebuild_standard_price_index(db)

    with engine.begin() as connection:
        for role, privileges in ((args.web_role, WEB_PRIVILEGES), (args.collector_role, COLLECTOR_PRIVILEGES)):
            if not role:
                continue
            if not role_exists(connection, role):
                raise SystemExit(f"database role {role} does not exist")
            apply_grants(connection, role, privileges)
            result.setdefault("grants", []).append(role)
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
