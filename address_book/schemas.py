"""Public request and response contracts."""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
PostalCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
Latitude = Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
Longitude = Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]


class AddressInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    street: ShortText
    city: ShortText
    region: ShortText | None = None
    postal_code: PostalCode
    country: ShortText
    latitude: Latitude
    longitude: Longitude


class AddressPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    street: ShortText | None = None
    city: ShortText | None = None
    region: ShortText | None = None
    postal_code: PostalCode | None = None
    country: ShortText | None = None
    latitude: Latitude | None = None
    longitude: Longitude | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_empty_or_null_required_fields(cls, value: Any) -> Any:
        if isinstance(value, dict):
            if not value:
                raise ValueError("At least one field must be supplied")
            if any(field != "region" and item is None for field, item in value.items()):
                raise ValueError("Only region may be null")
        return value


class AddressOutput(AddressInput):
    id: int


class NearbyAddressOutput(AddressOutput):
    distance_km: float
