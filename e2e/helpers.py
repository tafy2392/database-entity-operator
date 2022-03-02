# To get nicer type annotations in Python 3.7 and 3.8.
from __future__ import annotations

import logging
import subprocess
from contextlib import contextmanager

import pykube  # type: ignore
import yaml
from kopf.testing import KopfRunner  # type: ignore


def pykube_config():
    try:
        # running in cluster
        return pykube.KubeConfig.from_service_account()
    except FileNotFoundError:
        # not running in cluster => load local ~/.kube/config for testing
        return pykube.KubeConfig.from_file()


class KubeHelper:
    def __init__(self):
        self._api = pykube.HTTPClient(pykube_config())

    def _prepare_yaml(self, body):
        return yaml.dump(body).encode("utf8")

    def _kubectl(self, args, input):
        args = ["kubectl", *args]
        subprocess.run(args, check=True, input=input, capture_output=True)

    def kubectl_apply(self, body):
        self._kubectl(["apply", "-f", "-"], self._prepare_yaml(body))

    def kubectl_delete(self, body):
        self._kubectl(["delete", "-f", "-"], self._prepare_yaml(body))

    def apply_yaml(self, filename):
        self.kubectl_apply(yaml.safe_load(open(filename, "rt")))

    def delete_yaml(self, filename):
        self.kubectl_delete(yaml.safe_load(open(filename, "rt")))


@contextmanager
def kube_helper():
    kube = KubeHelper()
    yield kube


@contextmanager
def kopf_runner():
    logger = logging.getLogger()
    old_handlers = logger.handlers[:]
    args = [
        "--standalone",
        "--verbose",
        "-m",
        "database_operator.handlers",
    ]
    with KopfRunner(["run", *args]) as runner:
        # Remove any extra log handlers that starting kopf may have added.
        # The built-in pytest log capture does what we need already.
        for handler in logger.handlers[:]:
            if handler not in old_handlers:
                logger.removeHandler(handler)
        yield runner
