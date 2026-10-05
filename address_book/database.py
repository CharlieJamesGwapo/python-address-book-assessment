"""Small SQLite persistence layer; each operation owns its connection."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .geo import distance_km, latitude_range

FIELDS = ("street", "city", "region", "postal_code", "country", "latitude", "longitude")


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize(path: Path) -> None:
    with connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS addresses (
                id INTEGER PRIMARY KEY,
                street TEXT NOT NULL CHECK (length(trim(street)) > 0),
                city TEXT NOT NULL CHECK (length(trim(city)) > 0),
                region TEXT,
                postal_code TEXT NOT NULL CHECK (length(trim(postal_code)) > 0),
                country TEXT NOT NULL CHECK (length(trim(country)) > 0),
                latitude REAL NOT NULL CHECK (latitude BETWEEN -90 AND 90),
                longitude REAL NOT NULL CHECK (longitude BETWEEN -180 AND 180)
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_addresses_latitude ON addresses (latitude)"
        )


def create(path: Path, values: dict) -> dict:
    with connect(path) as connection:
        cursor = connection.execute(
            """INSERT INTO addresses
               (street, city, region, postal_code, country, latitude, longitude)
               VALUES (:street, :city, :region, :postal_code, :country, :latitude, :longitude)""",
            values,
        )
        row = connection.execute(
            "SELECT * FROM addresses WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row)


def get(path: Path, address_id: int) -> dict | None:
    with connect(path) as connection:
        row = connection.execute("SELECT * FROM addresses WHERE id = ?", (address_id,)).fetchone()
        return dict(row) if row else None


def list_addresses(path: Path, limit: int, offset: int) -> list[dict]:
    with connect(path) as connection:
        rows = connection.execute(
            "SELECT * FROM addresses ORDER BY id LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
        return [dict(row) for row in rows]


def update(path: Path, address_id: int, values: dict) -> dict | None:
    # SQLite cannot parameterize column names, so allow only known names.
    if not values or not values.keys() <= set(FIELDS):
        raise ValueError("Invalid update fields")
    assignments = ", ".join(f"{field} = :{field}" for field in values)
    with connect(path) as connection:
        cursor = connection.execute(
            f"UPDATE addresses SET {assignments} WHERE id = :id",
            {**values, "id": address_id},
        )
        if cursor.rowcount == 0:
            return None
        row = connection.execute("SELECT * FROM addresses WHERE id = ?", (address_id,)).fetchone()
        return dict(row)


def delete(path: Path, address_id: int) -> bool:
    with connect(path) as connection:
        cursor = connection.execute("DELETE FROM addresses WHERE id = ?", (address_id,))
        return cursor.rowcount > 0


def nearby(
    path: Path, latitude: float, longitude: float, radius_km: float, limit: int, offset: int
) -> list[dict]:
    min_lat, max_lat = latitude_range(latitude, radius_km)
    with connect(path) as connection:
        candidates = connection.execute(
            "SELECT * FROM addresses WHERE latitude BETWEEN ? AND ?", (min_lat, max_lat)
        ).fetchall()

    matches = []
    for row in candidates:
        distance = distance_km(latitude, longitude, row["latitude"], row["longitude"])
        if distance <= radius_km:
            matches.append({**dict(row), "distance_km": distance})
    matches.sort(key=lambda item: (item["distance_km"], item["id"]))
    return matches[offset : offset + limit]
