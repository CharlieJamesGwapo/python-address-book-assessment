from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from address_book.main import create_app


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    with TestClient(create_app(tmp_path / "addresses.sqlite3")) as test_client:
        yield test_client


@pytest.fixture
def address_payload() -> dict:
    return {
        "street": "  1 Main Street  ",
        "city": "Manila",
        "region": "Metro Manila",
        "postal_code": "1000",
        "country": "Philippines",
        "latitude": 14.5995,
        "longitude": 120.9842,
    }
