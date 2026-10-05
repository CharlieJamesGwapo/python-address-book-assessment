"""Great-circle distance calculations using WGS84 mean Earth radius."""

from math import asin, cos, degrees, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0088


def latitude_range(latitude: float, radius_km: float) -> tuple[float, float]:
    """A coarse, inclusive latitude window for a radius search."""
    delta = degrees(radius_km / EARTH_RADIUS_KM)
    return max(-90.0, latitude - delta), min(90.0, latitude + delta)


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return shortest surface distance in kilometres via the haversine formula."""
    if lat1 == lat2 and abs(lat1) == 90:
        return 0.0  # All longitudes meet at a pole.
    lat1_rad, lat2_rad = radians(lat1), radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians((lon2 - lon1 + 180) % 360 - 180)
    haversine = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(min(1.0, max(0.0, haversine))))
