# Mini-OTM

A simplified simulation inspired by Oracle OTM concepts. Small Order and Transportation Management (OTM) API prototype built with Python, FastAPI, and SQLite. It demonstrates a basic shipment workflow: register order releases, group them by route, select the lowest-cost carrier, create shipments, record tracking events, and summarize shipping costs by carrier.

> This is a learning project and a prototype. It is not a production logistics or port-management system.

## Features

- Create and list shipment order releases
- Validate that shipment weight is greater than zero
- Group new orders by source and destination
- Select the lowest-cost carrier for a route using configured rates
- Create shipments and associate planned orders with them
- Record `PICKED_UP`, `IN_TRANSIT`, and `DELIVERED` events
- Retrieve shipment details, associated orders, and tracking history
- Generate a cost and weight summary by carrier
- Explore and try the API through FastAPI's interactive documentation

## Technology

- Python
- FastAPI
- Pydantic
- SQLite (`sqlite3`)
- Uvicorn

## Project files

- `main.py` — FastAPI application, database initialization, validation models, and API endpoints
- `schema.sql` — SQLite tables, constraints, and relationships
- `mini_otm.db` — local SQLite database created/used by the application (not required to run; it is generated automatically)

## Requirements

- Python 3.10 or newer
- `pip`

## Setup and run

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install fastapi uvicorn
uvicorn main:app --reload
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install fastapi uvicorn
uvicorn main:app --reload
```

When the server starts, open:

- API documentation: <http://127.0.0.1:8000/docs>

Stop the local server with `Ctrl+C` in the terminal where Uvicorn is running.

## Example workflow

Use the interactive `/docs` page or an API client:

1. Create an order with `POST /order-releases`:

```json
{
  "source_id": "ALEX_PORT",
  "dest_id": "CAI_DEPOT",
  "weight_kg": 100
}
```

2. Plan new orders with `POST /plan`. Orders sharing a route are grouped into a shipment. The cheapest configured carrier rate is selected.
3. List orders with `GET /order-releases`, or filter by status with `GET /order-releases?status_filter=PLANNED`.
4. Get a shipment and its orders/events with `GET /shipments/{shipment_id}`.
5. Add a tracking event with `POST /shipments/{shipment_id}/events`:

```json
{
  "event_type": "PICKED_UP"
}
```

6. View the carrier cost summary with `GET /reports/cost-by-carrier`.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/order-releases` | Create an order release |
| `GET` | `/order-releases` | List order releases; optionally filter by status |
| `POST` | `/plan` | Group new orders and create shipments using the cheapest available rate |
| `GET` | `/shipments/{shipment_id}` | Read shipment details, associated orders, and tracking events |
| `POST` | `/shipments/{shipment_id}/events` | Add a tracking event and update shipment status |
| `GET` | `/reports/cost-by-carrier` | Summarize shipment count, weight, and total cost by carrier |

## Seed data

On startup, the application creates the database tables from `schema.sql`. If the `location` table is empty, it also inserts sample locations, carriers, and rates. The sample route from `ALEX_PORT` to `CAI_DEPOT` has two carrier rates so the planning logic can demonstrate choosing the lower one.

## Database location

By default, the app uses `mini_otm.db` in the current working directory. Set `MINI_OTM_DB` to use a different database file.

PowerShell example:

```powershell
$env:MINI_OTM_DB = "C:\data\mini_otm.db"
uvicorn main:app --reload
```

