# To get nicer type annotations in Python 3.7 and 3.8.
from __future__ import annotations

import pytest  # type: ignore
import time

from .helpers import kopf_runner, kube_helper

TIMEOUT_SECS = 240
LOG_ESTABLISH = "Successfully established connection to database postgres"
DATABASE_CREATED = "Database test created"
SCHEMAS_CREATED =  "Successfully created schemas ('ruru',) in database test"
EXTENSIONS_CREATED = "Successfully created extensions ('hstore',) in database test"
SUCCESSFUL_DROP = "Successfully dropped database test"
NO_DROP = "Database testfalse will not be dropped"
DATABASE_EXISTS = 'Error info: database "test" already exists'
UPDATED_SCHEMAS = "Successfully created schemas ('app',) in database test"
UPDATED_EXTENSIONS = "Successfully created extensions ('pg_stat_statements',) in database test"
REMOVED_SCHEMAS = "Successfully removed schemas ('ruru',) from database test"
REMOVED_EXTENSIONS = "Successfully removed extensions ('hstore',) from database test"


@pytest.fixture
def kube():
    with kube_helper() as kube:
        yield kube


def poll_with_timeout(start_time, log_msg=None):
    while time.monotonic() - start_time < TIMEOUT_SECS:
        if log_msg:
            print(log_msg, "time:", time.monotonic() - start_time)
        yield
        time.sleep(1)
    raise TimeoutError()


def wait_for_log(start_time, caplog, msg, skip=0):
    for _ in poll_with_timeout(start_time, f"Waiting for log entry: {msg!r}"):
        for rec in caplog.records[skip:]:
            if msg in rec.message:
                return


def test_database_create_and_cleanup(caplog, kube):
    """
    Test with a CR where dropOnDelete is true
    """
    start_time = time.monotonic()
    with kopf_runner():
        kube.apply_yaml("e2e/testdatabase.yaml")
        wait_for_log(start_time, caplog, LOG_ESTABLISH)
        wait_for_log(start_time, caplog, SCHEMAS_CREATED)
        wait_for_log(start_time, caplog, EXTENSIONS_CREATED)
        kube.delete_yaml("e2e/testdatabase.yaml")
        wait_for_log(start_time, caplog, LOG_ESTABLISH)
        wait_for_log(start_time, caplog, SUCCESSFUL_DROP)


def test_database_create_and_cleanup_with_false(caplog, kube):
    """
    Test with a CR where dropOnDelete is false
    """
    start_time = time.monotonic()
    with kopf_runner():
        kube.apply_yaml("e2e/testdatabasefalse.yaml")
        wait_for_log(start_time, caplog, LOG_ESTABLISH)
        wait_for_log(start_time, caplog, SCHEMAS_CREATED)
        wait_for_log(start_time, caplog, EXTENSIONS_CREATED)
        kube.delete_yaml("e2e/testdatabasefalse.yaml")
        wait_for_log(start_time, caplog, NO_DROP)


def test_database_create_with_the_same_database_name(caplog, kube):
    """
    Test two CRs with the same db name
    """
    start_time = time.monotonic()
    with kopf_runner():
        kube.apply_yaml("e2e/testdatabase.yaml")
        wait_for_log(start_time, caplog, LOG_ESTABLISH)
        wait_for_log(start_time, caplog, SCHEMAS_CREATED)
        wait_for_log(start_time, caplog, EXTENSIONS_CREATED)
        kube.apply_yaml("e2e/testdatabasesame.yaml")
        wait_for_log(start_time, caplog, DATABASE_EXISTS)
        kube.delete_yaml("e2e/testdatabase.yaml")
        kube.delete_yaml("e2e/testdatabasesame.yaml")


def test_update(caplog, kube):
    """
    Test update of extensions and schemas
    """
    start_time = time.monotonic()
    with kopf_runner():
        kube.apply_yaml("e2e/update.yaml")
        wait_for_log(start_time, caplog, LOG_ESTABLISH)
        wait_for_log(start_time, caplog, SCHEMAS_CREATED)
        wait_for_log(start_time, caplog, EXTENSIONS_CREATED)
        kube.apply_yaml("e2e/updatefirst.yaml")
        wait_for_log(start_time, caplog, UPDATED_SCHEMAS)
        wait_for_log(start_time, caplog, UPDATED_EXTENSIONS)
        wait_for_log(start_time, caplog, REMOVED_SCHEMAS)
        wait_for_log(start_time, caplog, REMOVED_EXTENSIONS)
        kube.delete_yaml("e2e/updatefirst.yaml")
