from app.db import models  # noqa: F401
from app.db.roles import COLLECTOR_PRIVILEGES, MEMBER_TABLES, PRICE_TABLES, SOURCE_TABLES, WEB_PRIVILEGES
from app.db.session import Base


def test_every_table_belongs_to_one_group():
    groups = MEMBER_TABLES + PRICE_TABLES + SOURCE_TABLES
    assert len(groups) == len(set(groups))
    assert set(groups) == set(Base.metadata.tables)


def test_web_writes_only_member_data_and_collector_never_sees_it():
    web_writes = {table for table, allowed in WEB_PRIVILEGES.items() if allowed != "SELECT"}
    assert web_writes == set(MEMBER_TABLES) | {"products"}
    assert WEB_PRIVILEGES["products"] == "SELECT, INSERT"
    assert not set(COLLECTOR_PRIVILEGES) & set(MEMBER_TABLES)
    assert COLLECTOR_PRIVILEGES["collection_sources"] == "SELECT"
