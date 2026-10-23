-- Mini-OTM schema (SQLite). Same ideas as OTM: locations, carriers, rates,
-- order releases (what must move), shipments (the actual trip), events (tracking).
CREATE TABLE IF NOT EXISTS location (
    location_id TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    city        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS carrier (
    carrier_id TEXT PRIMARY KEY,
    name       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rate (
    rate_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    carrier_id  TEXT NOT NULL REFERENCES carrier(carrier_id),
    source_id   TEXT NOT NULL REFERENCES location(location_id),
    dest_id     TEXT NOT NULL REFERENCES location(location_id),
    cost_per_kg REAL NOT NULL CHECK (cost_per_kg > 0)
);

CREATE TABLE IF NOT EXISTS shipment (
    shipment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    carrier_id      TEXT NOT NULL REFERENCES carrier(carrier_id),
    source_id       TEXT NOT NULL REFERENCES location(location_id),
    dest_id         TEXT NOT NULL REFERENCES location(location_id),
    total_weight_kg REAL NOT NULL,
    total_cost      REAL NOT NULL,
    status          TEXT NOT NULL DEFAULT 'PLANNED'
);

CREATE TABLE IF NOT EXISTS order_release (
    order_release_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id   TEXT NOT NULL REFERENCES location(location_id),
    dest_id     TEXT NOT NULL REFERENCES location(location_id),
    weight_kg   REAL NOT NULL CHECK (weight_kg > 0),
    status      TEXT NOT NULL DEFAULT 'NEW',
    shipment_id INTEGER REFERENCES shipment(shipment_id)
);

CREATE TABLE IF NOT EXISTS shipment_event (
    event_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id INTEGER NOT NULL REFERENCES shipment(shipment_id),
    event_type  TEXT NOT NULL,
    event_time  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
