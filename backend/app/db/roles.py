"""Database accounts of the three systems and what each may touch.

- web:       the website and the AI gateway.  Reads everything, writes only
             member data and AI conversation logs (plus admin product creation).
- collector: the price collectors.  Reads and writes prices, catalog and
             collection tables; cannot see member data or AI logs.
- owner:     the account that owns the tables and runs migrations.

The login roles and their passwords are created by the operator; this module
only (re)applies table privileges and is run by ``python -m app.db.migrate``.
"""

from sqlalchemy import text
from sqlalchemy.engine import Connection

MEMBER_TABLES = (
    "members",
    "member_auth_control",
    "member_sessions",
    "password_reset_tokens",
    "member_ai_usage",
    "member_login_events",
    "ai_conversation_logs",
)
PRICE_TABLES = (
    "products",
    "stores",
    "product_variants",
    "product_variant_identifiers",
    "prices",
    "price_history",
    "daily_high_prices",
    "store_product_prices",
    "official_store_products",
    "official_product_mappings",
    "collection_runs",
    "price_collection_sources",
)
SOURCE_TABLES = ("collection_sources",)

# table -> privileges
WEB_PRIVILEGES = {
    **{table: "SELECT" for table in PRICE_TABLES + SOURCE_TABLES},
    **{table: "SELECT, INSERT, UPDATE, DELETE" for table in MEMBER_TABLES},
    "products": "SELECT, INSERT",  # admin can register a product
}
COLLECTOR_PRIVILEGES = {
    **{table: "SELECT, INSERT, UPDATE, DELETE" for table in PRICE_TABLES},
    **{table: "SELECT" for table in SOURCE_TABLES},
}


def _quote(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"invalid identifier: {name}")
    return f'"{name}"'


def apply_grants(connection: Connection, role: str, privileges: dict[str, str]) -> None:
    quoted = _quote(role)
    connection.execute(text(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {quoted}"))
    connection.execute(text(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {quoted}"))
    connection.execute(text(f"GRANT USAGE ON SCHEMA public TO {quoted}"))
    for table, allowed in privileges.items():
        connection.execute(text(f"GRANT {allowed} ON TABLE {_quote(table)} TO {quoted}"))
        if "INSERT" in allowed:
            sequences = connection.execute(
                text(
                    "SELECT pg_get_serial_sequence(quote_ident(table_name), column_name) FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = :table "
                    "AND pg_get_serial_sequence(quote_ident(table_name), column_name) IS NOT NULL"
                ),
                {"table": table},
            ).scalars()
            for sequence in sequences:
                connection.execute(text(f"GRANT USAGE, SELECT ON SEQUENCE {sequence} TO {quoted}"))
