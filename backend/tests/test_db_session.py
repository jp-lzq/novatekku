import pytest

from app.db.session import with_explicit_driver


@pytest.mark.parametrize("url,expected", [
    ("postgresql://u:p@db:5432/nova", "postgresql+psycopg2://u:p@db:5432/nova"),
    ("postgres://u:p@db/nova", "postgresql+psycopg2://u:p@db/nova"),
    ("postgresql+psycopg2://u:p@db/nova", "postgresql+psycopg2://u:p@db/nova"),
    ("postgresql+psycopg://u:p@db/nova", "postgresql+psycopg://u:p@db/nova"),
    ("sqlite://", "sqlite://"),
])
def test_postgres_urls_name_the_installed_driver(url, expected):
    assert with_explicit_driver(url) == expected
