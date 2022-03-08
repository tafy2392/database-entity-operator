import asyncio  # type: ignore
from contextlib import asynccontextmanager
from typing import List

import asyncpg  # type: ignore
import attr

LOG_SUCCESSFUL = "Successfully created {} {} in database {}"
LOG_ESTABLISH = "Successfully established connection to database {}"
SUCCESSFUL_REMOVE = "Successfully removed {} {} from database {}"


def add_creation(x, y):
    return f"CREATE {y} IF NOT EXISTS {x}"


def drop_items(x, y):
    return f"DROP {y} IF EXISTS {x}"


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

    @asynccontextmanager
    async def master_connection(self):
        MASTER_DB_CONNECTION_STRING = "postgres://{}:{}@{}:{}/{}".format(
            self.master_user,
            self.master_password,
            self.postgres_host,
            str(self.postgres_port),
            self.postgres_default_database,
        )
        conn = await asyncpg.connect(MASTER_DB_CONNECTION_STRING)
        try:
            yield conn
        finally:
            await conn.close()

    @asynccontextmanager
    async def database_connection(self, database_name):
        DB_CONNECTION_STRING = "postgres://{}:{}@{}:{}/{}".format(
            self.master_user,
            self.master_password,
            self.postgres_host,
            str(self.postgres_port),
            database_name,
        )
        conn = await asyncpg.connect(DB_CONNECTION_STRING)
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

    @classmethod
    async def from_spec(cls, spec):
        drop_database = spec.get("dropOnDelete", False)
        schemas = spec["schemas"] if "schemas" in spec else []
        extensions = spec["extensions"] if "extensions" in spec else []
        return cls(spec["database"], drop_database, schemas, extensions)

    async def create_database(self, logger, master_obj, database_obj):
        """
        This function will create a database, extensions and schemas
        """
        NEW_EXTENSION_MAP = construct_items_map(
            self.extensions, "EXTENSION", "extensions"
        )
        NEW_SCHEMA_MAP = construct_items_map(self.schemas, "SCHEMA", "schemas")
        try:
            async with master_obj as conn:
                logger.info(LOG_ESTABLISH.format("postgres"))
                await conn.execute(f'CREATE DATABASE "{self.database_name}"')
                logger.info(f"Database {self.database_name} created")
        except Exception as e:
            logger.info(f"Error info: {e}")
        try:
            async with database_obj as conn:
                logger.info(LOG_ESTABLISH.format(self.database_name))
                for x, y in {**NEW_SCHEMA_MAP, **NEW_EXTENSION_MAP}.items():
                    if x:
                        [
                            await conn.execute(add_creation(item, y[0]))
                            for item in x
                        ]
                        logger.info(
                            LOG_SUCCESSFUL.format(y[1], x, self.database_name)
                        )
        except Exception as e:
            logger.error(f"Error info {e}")

    @asyncio.coroutine
    async def delete_database(self, logger, master_obj):
        """
        This function will drop a database if dropOnDelete is true
        """
        try:
            async with master_obj as conn:
                logger.info(LOG_ESTABLISH.format("postgres"))
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
        database_obj,
    ):
        """
        This function will update a database.
        """
        try:
            async with database_obj as conn:
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
