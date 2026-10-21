"""
simulator/events.py
Simulation audit logging, event stream, and alert triage.
"""
import datetime
import json


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def record_simulation_event(db, network_id: int, category: str, level: str,
                            message: str, details: dict = None) -> int:
    """Insert a simulation event into simulation_events table."""
    now_str = _now()
    cursor = db.execute("""
        INSERT INTO simulation_events (network_id, category, level, message, details, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        network_id,
        category,
        level,
        message,
        json.dumps(details) if details else None,
        now_str
    ))
    db.commit()
    return cursor.lastrowid


def get_recent_events(db, network_id: int, limit: int = 50) -> list[dict]:
    """Retrieve the most recent simulation events for the network console."""
    rows = db.execute("""
        SELECT * FROM simulation_events 
        WHERE network_id = ? 
        ORDER BY id DESC 
        LIMIT ?
    """, (network_id, limit)).fetchall()
    return [dict(r) for r in rows]


def get_active_alerts(db, network_id: int) -> list[dict]:
    """Retrieve all active or acknowledged alerts for the network."""
    rows = db.execute("""
        SELECT * FROM alerts 
        WHERE network_id = ? AND status != 'dismissed'
        ORDER BY id DESC
    """, (network_id,)).fetchall()
    return [dict(r) for r in rows]


def create_device_alert(db, network_id: int, alert_type: str, device_id: int, message: str) -> int:
    """Create a new alert if not already active."""
    existing = db.execute("""
        SELECT id FROM alerts 
        WHERE network_id = ? AND alert_type = ? AND device_id = ? AND status = 'active'
    """, (network_id, alert_type, device_id)).fetchone()

    if existing:
        return existing['id']

    cursor = db.execute("""
        INSERT INTO alerts (network_id, alert_type, device_id, message, status, created_at)
        VALUES (?, ?, ?, ?, 'active', ?)
    """, (network_id, alert_type, device_id, message, _now()))
    db.commit()
    return cursor.lastrowid
