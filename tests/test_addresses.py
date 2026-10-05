import pytest
from fastapi.testclient import TestClient

from address_book.main import create_app


def create_address(client, payload):
    response = client.post("/addresses", json=payload)
    assert response.status_code == 201, response.text
    return response


def test_create_get_list_and_persist(tmp_path, address_payload):
    database = tmp_path / "addresses.sqlite3"
    with TestClient(create_app(database)) as client:
        created = create_address(client, address_payload)
        body = created.json()
        assert body == {
            "id": 1,
            "street": "1 Main Street",
            "city": "Manila",
            "region": "Metro Manila",
            "postal_code": "1000",
            "country": "Philippines",
            "latitude": 14.5995,
            "longitude": 120.9842,
        }
        assert created.headers["location"] == "/addresses/1"
        assert client.get("/addresses/1").json() == body
        assert client.get("/addresses").json() == [body]

    with TestClient(create_app(database)) as client:
        assert client.get("/addresses/1").json() == body


def test_put_replaces_address(client, address_payload):
    address_id = create_address(client, address_payload).json()["id"]
    replacement = {
        **address_payload,
        "street": "2 New Street",
        "region": None,
        "latitude": 15.0,
    }
    response = client.put(f"/addresses/{address_id}", json=replacement)
    assert response.status_code == 200
    assert response.json()["street"] == "2 New Street"
    assert response.json()["region"] is None
    assert client.get(f"/addresses/{address_id}").json()["latitude"] == 15.0


def test_patch_changes_only_supplied_fields(client, address_payload):
    address_id = create_address(client, address_payload).json()["id"]
    response = client.patch(
        f"/addresses/{address_id}", json={"city": "Quezon City", "region": None}
    )
    assert response.status_code == 200
    assert response.json()["city"] == "Quezon City"
    assert response.json()["region"] is None
    assert response.json()["street"] == "1 Main Street"


def test_delete_then_not_found(client, address_payload):
    address_id = create_address(client, address_payload).json()["id"]
    response = client.delete(f"/addresses/{address_id}")
    assert response.status_code == 204
    assert response.content == b""
    for method, path in [
        ("get", f"/addresses/{address_id}"),
        ("delete", f"/addresses/{address_id}"),
        ("patch", f"/addresses/{address_id}"),
    ]:
        request = getattr(client, method)
        response = request(path, json={"city": "Cebu"}) if method == "patch" else request(path)
        assert response.status_code == 404


@pytest.mark.parametrize(
    ("change", "status"),
    [
        ({"street": "   "}, 422),
        ({"latitude": 90.0001}, 422),
        ({"latitude": -90.0001}, 422),
        ({"longitude": 180.0001}, 422),
        ({"longitude": -180.0001}, 422),
        ({"latitude": None}, 422),
        ({"extra": "ignored?"}, 422),
    ],
)
def test_create_rejects_invalid_addresses(client, address_payload, change, status):
    response = client.post("/addresses", json={**address_payload, **change})
    assert response.status_code == status
    assert client.get("/addresses").json() == []


def test_patch_rejects_empty_and_invalid_changes(client, address_payload):
    address_id = create_address(client, address_payload).json()["id"]
    for change in ({}, {"city": "   "}, {"latitude": None}, {"bad": 1}):
        assert client.patch(f"/addresses/{address_id}", json=change).status_code == 422
    assert client.get(f"/addresses/{address_id}").json()["city"] == "Manila"


def test_list_paginates_in_id_order(client, address_payload):
    for number in range(3):
        create_address(client, {**address_payload, "street": f"{number} Main Street"})
    response = client.get("/addresses", params={"limit": 1, "offset": 1})
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [2]
    assert client.get("/addresses", params={"limit": 0}).status_code == 422


def test_nearby_filters_and_sorts_by_distance(client, address_payload):
    for street, longitude in [("Far", 2.0), ("At center", 0.0), ("Near", 1.0)]:
        create_address(
            client,
            {**address_payload, "street": street, "latitude": 0.0, "longitude": longitude},
        )
    response = client.get(
        "/addresses/nearby",
        params={"latitude": 0.0, "longitude": 0.0, "radius_km": 150},
    )
    assert response.status_code == 200
    results = response.json()
    assert [item["street"] for item in results] == ["At center", "Near"]
    assert results[0]["distance_km"] == 0.0
    assert 111 < results[1]["distance_km"] < 112
    assert "distance_km" not in client.get("/addresses/2").json()


def test_nearby_crosses_antimeridian(client, address_payload):
    create_address(
        client,
        {**address_payload, "street": "Across date line", "latitude": 0, "longitude": -179.9},
    )
    create_address(
        client,
        {**address_payload, "street": "Elsewhere", "latitude": 0, "longitude": 170},
    )
    response = client.get(
        "/addresses/nearby",
        params={"latitude": 0, "longitude": 179.9, "radius_km": 30},
    )
    assert response.status_code == 200
    assert [item["street"] for item in response.json()] == ["Across date line"]


def test_nearby_can_page_through_every_match(client, address_payload):
    for number in range(3):
        create_address(
            client,
            {**address_payload, "street": f"Place {number}", "latitude": 0, "longitude": number},
        )
    params = {"latitude": 0, "longitude": 0, "radius_km": 300, "limit": 1}
    ids = []
    for offset in range(3):
        response = client.get("/addresses/nearby", params={**params, "offset": offset})
        assert response.status_code == 200
        ids.append(response.json()[0]["id"])
    assert ids == [1, 2, 3]
    assert client.get("/addresses/nearby", params={**params, "offset": 3}).json() == []


def test_nearby_at_pole(client, address_payload):
    create_address(
        client,
        {**address_payload, "street": "Other meridian", "latitude": 89.9, "longitude": -90},
    )
    response = client.get(
        "/addresses/nearby",
        params={"latitude": 90, "longitude": 90, "radius_km": 20},
    )
    assert response.status_code == 200
    assert [item["street"] for item in response.json()] == ["Other meridian"]


def test_nearby_accepts_radius_larger_than_earths_maximum_distance(client, address_payload):
    create_address(
        client,
        {**address_payload, "street": "Opposite side", "latitude": 0, "longitude": 180},
    )
    response = client.get(
        "/addresses/nearby",
        params={"latitude": 0, "longitude": 0, "radius_km": 30000},
    )
    assert response.status_code == 200
    assert [item["street"] for item in response.json()] == ["Opposite side"]


def test_zero_radius_returns_exact_coordinate_matches(client, address_payload):
    create_address(
        client,
        {**address_payload, "street": "Exact", "latitude": 0, "longitude": 0},
    )
    create_address(
        client,
        {**address_payload, "street": "Not exact", "latitude": 0, "longitude": 0.001},
    )
    response = client.get(
        "/addresses/nearby",
        params={"latitude": 0, "longitude": 0, "radius_km": 0},
    )
    assert response.status_code == 200
    assert [item["street"] for item in response.json()] == ["Exact"]


@pytest.mark.parametrize(
    "params",
    [
        {"latitude": 91, "longitude": 0, "radius_km": 1},
        {"latitude": 0, "longitude": 181, "radius_km": 1},
        {"latitude": 0, "longitude": 0, "radius_km": -1},
        {"latitude": 0, "longitude": 0, "radius_km": "nan"},
        {"latitude": 0, "longitude": 0, "radius_km": "inf"},
    ],
)
def test_nearby_rejects_invalid_queries(client, params):
    assert client.get("/addresses/nearby", params=params).status_code == 422
