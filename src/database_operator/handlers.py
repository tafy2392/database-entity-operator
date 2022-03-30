"""
A k8s operator for creating databases and their associated roles, extensions
"""
from __future__ import annotations

import asyncio  # type: ignore
import os

import kopf  # type: ignore
import pykube  # type: ignore

from .databases import Database, PostgresConnection

API_GROUP = "dboperator.p16n.org"
API_VERSION = "v1"

LOG_NOT_ALLOWED = (
    "Changing name of database in {} spec is not allowed. Create a new CR"
)
# Global pykube client for managing resources in event handlers.
_kapi = None


async def _create_pykube_postgres():
    """
    This will be used to establish the relationship between
    Postgres and PostgresUsers
    in the future
    """
    Postgres = pykube.object_factory(
        _kapi, f"{API_GROUP}/{API_VERSION}", "Postgres"
    )
    return Postgres


async def filter_on_postgres_update(old, new):
    """
    This will be used to return extensions,
    schemas which were dropped and added
    on update of postgres CR fields
    """
    added = list(filter(lambda a: a not in old, new))
    dropped = list(filter(lambda a: a not in new, old))
    return added, dropped


@kopf.on.startup(errors=kopf.ErrorsMode.PERMANENT)
async def startup(**kwargs):
    """
    Initialise database connections
    """
    POSTGRES_DEFAULT_DATABASE = os.getenv(
        "POSTGRES_DEFAULT_DATABASE", "postgres"
    )
    MASTER_POSTGRES_PASS = os.getenv("POSTGRES_PASS", "somePassword")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    MASTER_POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", 5432)
    global master_conn
    master_conn = PostgresConnection(
        MASTER_POSTGRES_USER,
        MASTER_POSTGRES_PASS,
        POSTGRES_HOST,
        POSTGRES_PORT,
        POSTGRES_DEFAULT_DATABASE,
    )


@kopf.on.login(errors=kopf.ErrorsMode.PERMANENT)
async def login_with_pykube(**kwargs):
    """
    Create an authenticated pykube API client and tell kopf to piggyback on
    pykube for its own authentication.
    """
    global _kapi
    kcfg = pykube.KubeConfig.from_env()
    _kapi = pykube.HTTPClient(kcfg)
    return kopf.login_via_pykube(**kwargs)


@kopf.on.resume(API_GROUP, API_VERSION, "postgres")
@kopf.on.create(API_GROUP, API_VERSION, "postgres")
async def create_fn(spec, logger=None, **kwargs):
    cpd = await Database.from_spec(spec, master_conn)
    await cpd.create_database(
        logger,
    )


@kopf.on.delete(API_GROUP, API_VERSION, "postgres")
async def deleted(spec, logger, **kwargs):
    """
    Handle the deletion of a postgres CR.
    If dropOnDelete is set to false prevent the deletion of a CR
    """
    cpd = await Database.from_spec(spec, master_conn)
    if cpd.drop_database:
        await cpd.delete_database(
            logger,
        )
    if not cpd.drop_database:
        logger.warning(f"Database {cpd.database_name} will not be dropped")


@kopf.on.field(API_GROUP, API_VERSION, "postgres", field="spec")
async def on_spec_data(old, new, name, logger=None, **kwargs):
    """
    This will update permissions of PostgresUsers on update.
    This will also update extensions. schemas
    on update of postgres CR fields
    """
    logger.warning(f"Data changed: {old} -> {new}")
    if old is not None:
        specs_obj = Database.from_spec(new, master_conn), Database.from_spec(
            old, master_conn
        )
        [obj_new, obj_old] = await asyncio.gather(*specs_obj)
        if obj_new.database_name != obj_old.database_name:
            logger.error(LOG_NOT_ALLOWED.format(name))
        else:
            tasks = filter_on_postgres_update(
                obj_old.extensions, obj_new.extensions
            ), filter_on_postgres_update(obj_old.schemas, obj_new.schemas)
            [
                (new_ext, dropped_ext),
                (new_schemas, dropped_schemas),
            ] = await asyncio.gather(*tasks)
            await obj_new.update_database(
                new_ext,
                dropped_ext,
                new_schemas,
                dropped_schemas,
                logger,
            )
