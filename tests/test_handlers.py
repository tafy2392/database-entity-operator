import asyncio

import pytest  # type: ignore

from database_operator.databases import Database
from database_operator.handlers import filter_on_postgres_update

EXTENSIONS_BEFORE = ["postgis", "postrest"]
EXTENSIONS_AFTER = ["mathlib", "postgis"]

DATABASE_FIELD_MAP = {"database": "DATABASE-NAME"}


class TestExtractedFieldsFromSpec:
    @pytest.mark.asyncio
    async def test_from_spec(self):
        spec = DATABASE_FIELD_MAP
        tps = await Database.from_spec(spec)
        assert tps.database_name == "DATABASE-NAME"
        assert tps.drop_database is False
        assert tps.schemas == []
        assert tps.extensions == []


@pytest.mark.asyncio
@asyncio.coroutine  # dummy to let tests pass
async def test_filter_on_postgres_update():
    added, dropped = await filter_on_postgres_update(
        EXTENSIONS_BEFORE, EXTENSIONS_AFTER
    )
    assert added == ["mathlib"]
    assert dropped == ["postrest"]
