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


def test_create_and_cleanup(caplog, kube):
    start_time = time.monotonic()
    with kopf_runner():
        kube.apply_yaml("e2e/testdatabase.yaml")
        wait_for_log(start_time, caplog, LOG_ESTABLISH)
        wait_for_log(start_time, caplog, SCHEMAS_CREATED)
        wait_for_log(start_time, caplog, EXTENSIONS_CREATED)
        kube.delete_yaml("e2e/testdatabase.yaml")
        wait_for_log(start_time, caplog, LOG_ESTABLISH)
        wait_for_log(start_time, caplog, SUCCESSFUL_DROP)

