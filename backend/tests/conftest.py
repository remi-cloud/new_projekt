import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
