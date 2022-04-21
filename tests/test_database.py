import asyncio  # type: ignore

import pytest  # type: ignore

from database_operator.databases import PostgresConnection

test_conn = PostgresConnection(
    "testuser",
    "testpassword",
    "testhost",
    5432,
    "testdefaultdatabase",
)


class TestPostgresSpec:
    @pytest.mark.asyncio
    @asyncio.coroutine  # dummy to let tests pass
    async def test_postgresconnection(self):
        assert test_conn.master_user == "testuser"
        assert test_conn.master_password == "testpassword"
        assert test_conn.postgres_host == "testhost"
        assert test_conn.postgres_port == 5432
        assert test_conn.postgres_default_database == "testdefaultdatabase"
        assert isinstance(test_conn, object)
        assert (
            test_conn.connstr("testnewdb")
            == "postgres://testuser:testpassword@testhost:5432/testnewdb"
        )
