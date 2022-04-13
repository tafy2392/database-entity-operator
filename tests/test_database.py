import asyncio  # type: ignore
import unittest
from contextlib import asynccontextmanager

import asyncpg  # type: ignore
import pytest  # type: ignore


@pytest.fixture(scope="session")
@asynccontextmanager
async def db_connection(docker_services, docker_ip):
    """
    generate a python conn object
    """
    db_settings = {
        "database": "postgres",
        "user": "postgres",
        "host": docker_ip,
        "password": "somePassword",
        "port": docker_services.port_for("database", 5432),
    }
    dbc = await asyncpg.connect(**db_settings)
    try:
        yield dbc
    finally:
        dbc.close()


@pytest.fixture(autouse=True)
@pytest.mark.asyncio
@asyncio.coroutine  # dummy to let tests pass
async def test_conn(mocker, db_connection):
    mocker.patch(
        "database_operator.databases.PostgresConnection.master_connection",
        db_connection,
    )
    yield True


@pytest.mark.usefixtures("test_conn")
class TestMock(unittest.TestCase):
    def test_program(self):
        #  this test is using mocked database connection.
        assert True
