# Address Book API

A small FastAPI service for storing validated postal addresses in SQLite and finding addresses within a distance of a coordinate. The built-in Swagger UI is the only interface required.

## Requirements

- Python 3.10 or newer
- No separate database server

## Run locally

From a terminal with Python 3.10 installed, run these exact commands:

```bash
git clone https://github.com/CharlieJamesGwapo/python-address-book-assessment.git
cd python-address-book-assessment
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn address_book.main:app --reload
```

Open <http://127.0.0.1:8000/docs> to use the API interactively. The SQLite file `addresses.sqlite3` is created automatically in the working directory on startup. To store it elsewhere, set `ADDRESS_BOOK_DB_PATH` to a file path whose parent directory already exists before starting the server.

For Windows PowerShell, replace the environment setup commands with:

```powershell
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn address_book.main:app --reload
```

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/addresses` | Create an address; returns `201` and a `Location` header |
| `GET` | `/addresses` | List addresses in ID order |
| `GET` | `/addresses/{id}` | Get one address |
| `PUT` | `/addresses/{id}` | Replace all address fields |
| `PATCH` | `/addresses/{id}` | Update supplied fields only |
| `DELETE` | `/addresses/{id}` | Delete an address; returns `204` |
| `GET` | `/addresses/nearby` | Find addresses within `radius_km` of `latitude` and `longitude` |

List and nearby results accept `limit` (1–100, default 100) and `offset` (0 or greater, default 0). Nearby results are ordered by exact distance, then ID, and include `distance_km`. Page with increasing offsets to retrieve every match.

`radius_km` must be nonnegative. A zero radius returns addresses at the requested location, including equivalent coordinates across the antimeridian and at the poles.

Address input requires `street`, `city`, `postal_code`, `country`, `latitude`, and `longitude`; `region` is optional. Text is trimmed and cannot be blank. Latitude must be between −90 and 90, longitude between −180 and 180. Unknown fields and invalid values return `422`; missing address IDs return `404`. A `PATCH` request must include at least one field. Only `region` may be set to `null`.

### Example commands

With the server running, create and query an address:

```bash
curl -i -X POST http://127.0.0.1:8000/addresses \
  -H 'Content-Type: application/json' \
  -d '{"street":"1 Main Street","city":"Manila","region":"Metro Manila","postal_code":"1000","country":"Philippines","latitude":14.5995,"longitude":120.9842}'

curl 'http://127.0.0.1:8000/addresses/nearby?latitude=14.6&longitude=120.98&radius_km=5'

curl -X PATCH http://127.0.0.1:8000/addresses/1 \
  -H 'Content-Type: application/json' \
  -d '{"street":"2 Main Street"}'

curl -i -X DELETE http://127.0.0.1:8000/addresses/1
```

## Design

- `address_book/main.py` defines HTTP routes and uses an application factory so tests can inject a temporary database path.
- `address_book/schemas.py` validates API input with Pydantic. SQLite also enforces essential nonempty and coordinate constraints.
- `address_book/database.py` owns parameterized SQLite operations. Each operation closes its connection and commits or rolls back as needed.
- `address_book/geo.py` calculates great-circle distance with the haversine formula and a mean Earth radius of 6,371.0088 km. A latitude index narrows candidates; the exact distance check handles poles and the antimeridian correctly.
- The application logs database startup, writes, and search counts through Uvicorn's configured logger. No address text is logged.

## Test and lint

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

Tests use temporary SQLite files and cover CRUD, persistence, validation, pagination, geographic edge cases, and SQL column allowlisting.
