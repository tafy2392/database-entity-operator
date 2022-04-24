import asyncio
from contextlib import asynccontextmanager
from typing import List

import asyncpg  # type: ignore
import attr  # type: ignore

LOG_SUCCESSFUL = "Successfully created {} {} in database {}"
LOG_ESTABLISH = "Successfully established connection to database {}"
SUCCESSFUL_REMOVE = "Successfully removed {} {} from database {}"


def add_creation(x, y):
    return f'CREATE {y} IF NOT EXISTS "{x}"'


def drop_items(x, y):
    return f'DROP {y} IF EXISTS "{x}"'


def construct_items_map(items, postgres_construct, log_stat):
    # Returns a maps
    return {tuple(items): [postgres_construct, log_stat]}


@attr.s(auto_attribs=True, frozen=True)
class PostgresConnection:
    master_user: str
    master_password: str
    postgres_host: str
    postgres_port: int
    postgres_default_database: str

    def connstr(self, dbname):
        return "postgres://{}:{}@{}:{}/{}".format(
            self.master_user,
            self.master_password,
            self.postgres_host,
            self.postgres_port,
            dbname,
        )

    @asynccontextmanager
    async def master_connection(self):
        db_name = self.postgres_default_database
        conn = await asyncpg.connect(self.connstr(db_name))
        try:
            yield conn
        finally:
            await conn.close()

    @asynccontextmanager
    async def database_connection(self, database_name):
        conn = await asyncpg.connect(self.connstr(database_name))
        try:
            yield conn
        finally:
            await conn.close()


@attr.s(auto_attribs=True, frozen=True)
class Database:
    database_name: str
    drop_database: bool
    schemas: List[str] = attr.ib()
    extensions: List[str] = attr.ib()
    conn_obj: object

    @classmethod
    async def from_spec(cls, spec, conn_obj):
        drop_database = spec.get("dropOnDelete", False)
        schemas = spec["schemas"] if "schemas" in spec else []
        extensions = spec["extensions"] if "extensions" in spec else []
        return cls(
            spec["database"], drop_database, schemas, extensions, conn_obj
        )

    async def create_database(self, logger):
        """
        This function will create a database, extensions and schemas
        """
        NEW_EXTENSION_MAP = construct_items_map(
            self.extensions, "EXTENSION", "extensions"
        )
        NEW_SCHEMA_MAP = construct_items_map(self.schemas, "SCHEMA", "schemas")
        try:
            async with self.conn_obj.master_connection() as conn:
                logger.info(LOG_ESTABLISH.format("postgres"))
                await conn.execute(f'CREATE DATABASE "{self.database_name}"')
                logger.info(f"Database {self.database_name} created")
            async with self.conn_obj.database_connection(
                self.database_name
            ) as conn:
                logger.info(LOG_ESTABLISH.format(self.database_name))
                await conn.execute(
                    "REVOKE CREATE ON SCHEMA public FROM PUBLIC"
                )
                await conn.execute(
                    "REVOKE ALL ON DATABASE "
                    f'"{self.database_name}" FROM PUBLIC'
                )
                logger.info(
                    f"Revoked PUBLIC role access on {self.database_name}"
                )
                for x, y in {
                    **NEW_SCHEMA_MAP,
                    **NEW_EXTENSION_MAP,
                }.items():
                    if x:
                        [
                            await conn.execute(add_creation(item, y[0]))
                            for item in x
                        ]
                        logger.info(
                            LOG_SUCCESSFUL.format(y[1], x, self.database_name)
                        )
        except Exception as e:
            logger.info(f"Error info: {e}")

    @asyncio.coroutine
    async def delete_database(
        self,
        logger,
    ):
        """
        This function will drop a database if dropOnDelete is true
        """
        try:
            async with self.conn_obj.master_connection() as conn:
                logger.info(LOG_ESTABLISH.format("postgres"))
                await conn.execute(
                    "SELECT *, pg_terminate_backend(pid) "
                    "FROM pg_stat_activity WHERE pid <> pg_backend_pid() "
                    f"AND datname = '{self.database_name}'"
                )
                await conn.execute(
                    f'DROP DATABASE IF EXISTS "{self.database_name}"'
                )
                logger.info(
                    f"Successfully dropped database {self.database_name}"
                )
        except Exception as e:
            logger.error(f"Error info: {e}")

    async def update_database(
        self,
        new_ext,
        dropped_ext,
        new_schemas,
        dropped_schemas,
        logger,
    ):
        """
        This function will update a database.
        """
        try:
            async with self.conn_obj.database_connection(
                self.database_name
            ) as conn:
                logger.info(
                    logger.info(LOG_ESTABLISH.format(self.database_name))
                )
                NEW_EXTENSION_MAP = construct_items_map(
                    new_ext, "EXTENSION", "extensions"
                )
                NEW_SCHEMA_MAP = construct_items_map(
                    new_schemas, "SCHEMA", "schemas"
                )
                OLD_SCHEMA_MAP = construct_items_map(
                    dropped_schemas, "SCHEMA", "schemas"
                )
                OLD_EXTENSION_MAP = construct_items_map(
                    dropped_ext, "EXTENSION", "extensions"
                )

                for x, y in {**NEW_SCHEMA_MAP, **NEW_EXTENSION_MAP}.items():
                    if x:
                        [
                            await conn.execute(add_creation(item, y[0]))
                            for item in x
                        ]
                        logger.info(
                            LOG_SUCCESSFUL.format(y[1], x, self.database_name)
                        )

                for x, y in {**OLD_SCHEMA_MAP, **OLD_EXTENSION_MAP}.items():
                    if x:
                        [
                            await conn.execute(drop_items(item, y[0]))
                            for item in x
                        ]
                        logger.info(
                            SUCCESSFUL_REMOVE.format(
                                y[1], x, self.database_name
                            )
                        )
        except Exception as e:
            logger.error(f"Error info {e}")
