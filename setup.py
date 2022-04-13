import os

from setuptools import find_packages  # type: ignore
from setuptools import setup  # type: ignore

HERE = os.path.abspath(os.path.dirname(__file__))

DESC = "A k8s operator for creating postgres databases, roles and extensions"


def read(*parts):
    with open(os.path.join(HERE, *parts)) as f:
        return f.read()


setup(
    name="database-entity-operator",
    # NOTE: When updating the version for release, don't forget to update the
    # deploy YAML as well.
    version="0.0.1.dev0",
    license="MIT",
    description=DESC,
    author="Praekelt.org SRE team",
    author_email="sre@praekelt.org",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    packages=find_packages("src"),
    package_data={"": ["py.typed"]},
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "attrs",
        # Pin kopf because it is (somewhat) rapidly evolving.
        "kopf==1.35.3",
        "pykube-ng>=20.10.0",
        "asyncio>=3.4.3",
        "asyncpg>=0.25.0",
        "psycopg2==2.9.3",
    ],
    extras_require={
        "dev": [
            "black",
            "flake8",
            "isort",
            "mypy",
            "pytest>=6.1.0",
            "pytest-cov",
            "pytest-mock",
            "pytest-asyncio>=0.17.2",
            "pyyaml",
            "types-pyyaml",
        ],
    },
)
