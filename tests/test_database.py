import asyncio  # type: ignore
import unittest
from contextlib import asynccontextmanager

import asyncpg  # type: ignore
import pytest  # type: ignore


@pytest.fixture(scope="session")
def http_service(docker_ip, docker_services):
    """Ensure that HTTP service is up and responsive."""

    # `port_for` takes a container port and returns the corresponding host port
    port = docker_services.port_for("httpbin", 80)
    url = "http://{}:{}".format(docker_ip, port)
    docker_services.wait_until_responsive(
        timeout=30.0, pause=0.1, check=lambda: is_responsive(url)
    )
    return url


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
        "password": "",
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
