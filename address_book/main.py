"""FastAPI routes and application factory."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status

from . import database
from .schemas import AddressInput, AddressOutput, AddressPatch, NearbyAddressOutput

logger = logging.getLogger("uvicorn.error")


def database_path(request: Request) -> Path:
    return request.app.state.database_path


DatabasePath = Annotated[Path, Depends(database_path)]


def create_app(db_path: str | Path | None = None) -> FastAPI:
    path = Path(
        db_path if db_path is not None else os.getenv("ADDRESS_BOOK_DB_PATH", "addresses.sqlite3")
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        database.initialize(path)
        logger.info("Address book database ready: %s", path)
        yield

    app = FastAPI(
        title="Address Book API",
        description="Validated address CRUD and radius search, backed by SQLite.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.database_path = path

    @app.post(
        "/addresses",
        response_model=AddressOutput,
        status_code=status.HTTP_201_CREATED,
        tags=["Addresses"],
    )
    def create_address(address: AddressInput, response: Response, path: DatabasePath):
        created = database.create(path, address.model_dump())
        response.headers["Location"] = f"/addresses/{created['id']}"
        logger.info("Address created: id=%s", created["id"])
        return created

    @app.get("/addresses", response_model=list[AddressOutput], tags=["Addresses"])
    def list_addresses(
        path: DatabasePath,
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ):
        return database.list_addresses(path, limit, offset)

    @app.get("/addresses/nearby", response_model=list[NearbyAddressOutput], tags=["Addresses"])
    def nearby_addresses(
        path: DatabasePath,
        latitude: Annotated[float, Query(ge=-90, le=90, allow_inf_nan=False)],
        longitude: Annotated[float, Query(ge=-180, le=180, allow_inf_nan=False)],
        radius_km: Annotated[float, Query(ge=0, allow_inf_nan=False)],
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ):
        results = database.nearby(path, latitude, longitude, radius_km, limit, offset)
        logger.info("Nearby search: matches=%s radius_km=%s", len(results), radius_km)
        return results

    @app.get("/addresses/{address_id}", response_model=AddressOutput, tags=["Addresses"])
    def get_address(address_id: int, path: DatabasePath):
        address = database.get(path, address_id)
        if address is None:
            raise HTTPException(status_code=404, detail="Address not found")
        return address

    @app.put("/addresses/{address_id}", response_model=AddressOutput, tags=["Addresses"])
    def replace_address(address_id: int, address: AddressInput, path: DatabasePath):
        updated = database.update(path, address_id, address.model_dump())
        if updated is None:
            raise HTTPException(status_code=404, detail="Address not found")
        logger.info("Address replaced: id=%s", address_id)
        return updated

    @app.patch("/addresses/{address_id}", response_model=AddressOutput, tags=["Addresses"])
    def patch_address(address_id: int, address: AddressPatch, path: DatabasePath):
        updated = database.update(path, address_id, address.model_dump(exclude_unset=True))
        if updated is None:
            raise HTTPException(status_code=404, detail="Address not found")
        logger.info("Address updated: id=%s", address_id)
        return updated

    @app.delete(
        "/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Addresses"]
    )
    def delete_address(address_id: int, path: DatabasePath):
        if not database.delete(path, address_id):
            raise HTTPException(status_code=404, detail="Address not found")
        logger.info("Address deleted: id=%s", address_id)

    return app


app = create_app()
