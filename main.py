"""Mini-OTM: order release -> plan shipment -> pick cheapest carrier -> track events.
Run:  uvicorn main:app --reload     then open http://127.0.0.1:8000/docs
"""
import os
import sqlite3
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

DB_PATH = os.environ.get("MINI_OTM_DB", "mini_otm.db")
SCHEMA = Path(__file__).with_name("schema.sql")

app = FastAPI(title="Mini-OTM")


# ---------- database helpers (plain SQL through sqlite3) ----------
def get_db() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row          # rows behave like dicts
    db.execute("PRAGMA foreign_keys = ON")  # enforce REFERENCES
    return db


def init_db() -> None:
    db = get_db()
    db.executescript(SCHEMA.read_text())
    if db.execute("SELECT COUNT(*) FROM location").fetchone()[0] == 0:  # seed once
        db.executemany("INSERT INTO location VALUES (?,?,?)", [
            ("ALEX_PORT", "Alexandria Port", "Alexandria"),
            ("CAI_DEPOT", "Cairo Depot", "Cairo"),
            ("DAM_PORT", "Damietta Port", "Damietta"),
        ])
        db.executemany("INSERT INTO carrier VALUES (?,?)", [
            ("FAST_TRUCK", "Fast Truck Co"), ("NILE_LOG", "Nile Logistics"),
        ])
        db.executemany(
            "INSERT INTO rate (carrier_id, source_id, dest_id, cost_per_kg) VALUES (?,?,?,?)", [
                ("FAST_TRUCK", "ALEX_PORT", "CAI_DEPOT", 1.20),
                ("NILE_LOG",   "ALEX_PORT", "CAI_DEPOT", 0.95),
                ("FAST_TRUCK", "DAM_PORT",  "CAI_DEPOT", 1.10),
            ])
    db.commit()
    db.close()


init_db()


# ---------- request models ----------
class OrderReleaseIn(BaseModel):
    source_id: str
    dest_id: str
    weight_kg: float = Field(gt=0)


class EventIn(BaseModel):
    event_type: Literal["PICKED_UP", "IN_TRANSIT", "DELIVERED"]


# ---------- endpoints ----------
@app.post("/order-releases", status_code=status.HTTP_201_CREATED)
def create_order_release(data: OrderReleaseIn):
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO order_release (source_id, dest_id, weight_kg) VALUES (?,?,?)",
            (data.source_id, data.dest_id, data.weight_kg))
        db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(400, "Unknown source/destination location")
    finally:
        db.close()
    return {"order_release_id": cur.lastrowid, "status": "NEW"}


@app.get("/order-releases")
def list_order_releases(status_filter: str | None = None):
    db = get_db()
    sql, params = "SELECT * FROM order_release", ()
    if status_filter:
        sql, params = sql + " WHERE status = ?", (status_filter,)
    rows = [dict(r) for r in db.execute(sql, params)]
    db.close()
    return rows


@app.post("/plan")
def plan_shipments():
    """Group NEW releases by route, pick the cheapest carrier, create shipments."""
    db = get_db()
    created, unplannable = [], []
    groups = db.execute(
        """SELECT source_id, dest_id, SUM(weight_kg) AS w
           FROM order_release WHERE status = 'NEW'
           GROUP BY source_id, dest_id""").fetchall()
    for g in groups:
        best = db.execute(
            """SELECT carrier_id, cost_per_kg FROM rate
               WHERE source_id = ? AND dest_id = ?
               ORDER BY cost_per_kg LIMIT 1""",
            (g["source_id"], g["dest_id"])).fetchone()
        if best is None:
            unplannable.append({"source_id": g["source_id"], "dest_id": g["dest_id"]})
            continue
        cur = db.execute(
            """INSERT INTO shipment (carrier_id, source_id, dest_id, total_weight_kg, total_cost)
               VALUES (?,?,?,?,?)""",
            (best["carrier_id"], g["source_id"], g["dest_id"], g["w"], g["w"] * best["cost_per_kg"]))
        db.execute(
            """UPDATE order_release SET status = 'PLANNED', shipment_id = ?
               WHERE status = 'NEW' AND source_id = ? AND dest_id = ?""",
            (cur.lastrowid, g["source_id"], g["dest_id"]))
        created.append(cur.lastrowid)
    db.commit()
    db.close()
    return {"shipments_created": created, "no_rate_found": unplannable}


@app.get("/shipments/{shipment_id}")
def get_shipment(shipment_id: int):
    db = get_db()
    s = db.execute("SELECT * FROM shipment WHERE shipment_id = ?", (shipment_id,)).fetchone()
    if s is None:
        db.close()
        raise HTTPException(404, "Shipment not found")
    result = dict(s)
    result["order_releases"] = [dict(r) for r in db.execute(
        "SELECT * FROM order_release WHERE shipment_id = ?", (shipment_id,))]
    result["events"] = [dict(r) for r in db.execute(
        "SELECT event_type, event_time FROM shipment_event WHERE shipment_id = ? ORDER BY event_id",
        (shipment_id,))]
    db.close()
    return result


@app.post("/shipments/{shipment_id}/events", status_code=status.HTTP_201_CREATED)
def add_event(shipment_id: int, data: EventIn):
    db = get_db()
    if db.execute("SELECT 1 FROM shipment WHERE shipment_id = ?", (shipment_id,)).fetchone() is None:
        db.close()
        raise HTTPException(404, "Shipment not found")
    db.execute("INSERT INTO shipment_event (shipment_id, event_type) VALUES (?,?)",
               (shipment_id, data.event_type))
    db.execute("UPDATE shipment SET status = ? WHERE shipment_id = ?", (data.event_type, shipment_id))
    db.commit()
    db.close()
    return {"shipment_id": shipment_id, "status": data.event_type}


@app.get("/reports/cost-by-carrier")
def cost_by_carrier():
    db = get_db()
    rows = [dict(r) for r in db.execute(
        """SELECT c.name AS carrier, COUNT(*) AS shipments,
                  SUM(s.total_weight_kg) AS total_kg, SUM(s.total_cost) AS total_cost
           FROM shipment s JOIN carrier c ON c.carrier_id = s.carrier_id
           GROUP BY c.name ORDER BY total_cost DESC""")]
    db.close()
    return rows
