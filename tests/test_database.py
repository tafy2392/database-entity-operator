import asyncio  # type: ignore
import unittest
from contextlib import asynccontextmanager

import asyncpg  # type: ignore
import pytest  # type: ignore


@pytest.fixture(scope="session")
@asynccontextmanager
async def db_connection():
    """
    generate a python conn object
    """
    db_settings = {
        "database": "postgres",
        "user": "postgres",
        "host": "127.0.0.1",
        "password": "somePassword",
        "port": "31000",
    }
    dbc = await asyncpg.connect(**db_settings)
    try:
        yield dbc
    finally:
        dbc.close()


class TestMock(unittest.TestCase):
    @pytest.fixture
    def test_conn(self, mocker, db_connection):
        mocker.patch(
            "database_operator.databases.PostgresConnection.master_connection",
            db_connection,
        )
        yield True

    def test_program(self, test_conn):
	    # this test is using mocked database connection.
	    assert True
