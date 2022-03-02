import asyncio  # type: ignore
import os
from typing import List

import asyncpg  # type: ignore
import attr

POSTGRES_DEFAULT_DATABASE = os.getenv("POSTGRES_DEFAULT_DATABASE", "postgres")
MASTER_POSTGRES_PASS = os.getenv("POSTGRES_PASS", "somePassword")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
MASTER_POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")


LOG_SUCCESSFUL = "Successfully created {} {} in database {}"
LOG_ESTABLISH = "Successfully established connection to database {}"
SUCCESSFUL_REMOVE = "Successfully removed {} {} from database {}"

MASTER_DB_CONNECTION_STRING = "postgres://{}:{}@{}:{}/{}".format(
    MASTER_POSTGRES_USER,
    MASTER_POSTGRES_PASS,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DEFAULT_DATABASE,
)


def add_creation(x, y):
    return f"CREATE {y} IF NOT EXISTS {x}"


def drop_items(x, y):
    return f"DROP {y} IF EXISTS {x}"


def construct_items_map(items, postgres_construct, log_stat):
    # Returns a maps
    return {tuple(items): [postgres_construct, log_stat]}


@attr.s(auto_attribs=True, frozen=True)
class Database:
    database_name: str
    drop_database: bool
    schemas: List[str] = attr.ib()
    extensions: List[str] = attr.ib()

    @property
    def database_conn_string(self) -> str:
        return "postgres://{}:{}@{}:{}/{}".format(
            MASTER_POSTGRES_USER,
            MASTER_POSTGRES_PASS,
            POSTGRES_HOST,
            POSTGRES_PORT,
            self.database_name,
        )

    @classmethod
    async def from_spec(cls, spec):
        drop_database = spec.get("dropOnDelete", False)
        schemas = spec["schemas"] if "schemas" in spec else []
        extensions = spec["extensions"] if "extensions" in spec else []
        return cls(spec["database"], drop_database, schemas, extensions)

    async def create_database(self, logger):
        """
        This function will create a database, extensions and schemas
        """
        conn = None
        NEW_EXTENSION_MAP = construct_items_map(
            self.extensions, "EXTENSION", "extensions"
        )
        NEW_SCHEMA_MAP = construct_items_map(self.schemas, "SCHEMA", "schemas")
        try:
            conn = await asyncpg.connect(MASTER_DB_CONNECTION_STRING)
            logger.info(LOG_ESTABLISH.format("postgres"))
            try:
                await conn.execute(f'CREATE DATABASE "{self.database_name}"')
                logger.info(f"Database {self.database_name} created")
            except asyncpg.DuplicateDatabaseError:
                logger.info(f"Database {self.database_name} already exists")
            finally:
                await conn.close()
            conn = await asyncpg.connect(self.database_conn_string)
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
            await conn.close()
        except Exception as e:
            logger.error(f"Error info {e}")

    @asyncio.coroutine
    async def delete_database(self, logger):
        """
        This function will drop a database if dropOnDelete is true
        """
        conn = None
        try:
            conn = await asyncpg.connect(MASTER_DB_CONNECTION_STRING)
            logger.info(LOG_ESTABLISH.format("postgres"))
            try:
                await conn.execute(
                    f'DROP DATABASE IF EXISTS "{self.database_name}"'
                )
                logger.info(
                    f"Successfully dropped database {self.database_name}"
                )
            except asyncpg.DatabaseDroppedError:
                logger.error(f"Database {self.database_name} does not exist")
            await conn.close()
        except Exception as e:
            logger.error(f"Error info {e}")

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
        conn = None
        try:
            conn = await asyncpg.connect(self.database_conn_string)
            logger.info(logger.info(LOG_ESTABLISH.format(self.database_name)))
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
                    [await conn.execute(drop_items(item, y[0])) for item in x]
                    logger.info(
                        SUCCESSFUL_REMOVE.format(y[1], x, self.database_name)
                    )
            await conn.close()
        except Exception as e:
            logger.error(f"Error info {e}")
