import asyncio  # type: ignore

import pytest  # type: ignore
from pytest_postgresql.janitor import DatabaseJanitor  # type: ignore

from database_operator.databases import (
    PostgresConnection,
    add_creation,
    construct_items_map,
    drop_items,
)

test_conn = PostgresConnection(
    "testuser",
    "testpassword",
    "testhost",
    5432,
    "testdefaultdatabase",
)

EXTENSIONS = ["fuzzstr", "pg_statement"]


@pytest.fixture(scope="function")
async def database(postgresql_proc):
    with DatabaseJanitor(
        postgresql_proc.user,
        postgresql_proc.host,
        postgresql_proc.port,
        "my_test_database",
        postgresql_proc.version,
        password="secret_password",
    ):
        master_conn = PostgresConnection(
            postgresql_proc.user,
            "secret_password",
            postgresql_proc.host,
            postgresql_proc.port,
            "master_test_database",
        )
        yield master_conn.master_connection()


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

    def test_postgres_statements_constr_methods(self):
        assert add_creation("x", "y") == 'CREATE y IF NOT EXISTS "x"'
        assert (
            drop_items("test", "DATABASE") == 'DROP DATABASE IF EXISTS "test"'
        )
        assert construct_items_map(
            EXTENSIONS, "POSTGRES_CONSTRUCT", "LOG_MESSAGE"
        ) == {tuple(EXTENSIONS): ["POSTGRES_CONSTRUCT", "LOG_MESSAGE"]}

    @pytest.mark.usefixtures("database")
    @pytest.mark.asyncio
    async def test_master_database(self):
        print("damba")
        async with database as conn:
            await conn.execute('CREATE DATABASE "tanya"')
