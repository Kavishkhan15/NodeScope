"""
services/activity_history.py
Records network events and manages alerts.
Includes deduplication to avoid flooding the log with repeated identical events.
"""
import datetime
from database.db import get_db


def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + 'Z'


def record_event(event_type: str, device_mac: str | None, ip_address: str | None,
                 description: str, is_demo: int = 0) -> int | None:
    """
    Insert an activity event, skipping exact duplicates within 60 seconds.
    Returns the new row id, or None if deduplicated.
    """
    db = get_db()

    # Dedup: skip if same type+mac+ip event already exists in the last 60 seconds
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(seconds=60)).isoformat() + 'Z'
    existing = db.execute(
        """SELECT id FROM activity_events
           WHERE event_type=? AND (device_mac IS ? OR device_mac=?)
             AND (ip_address IS ? OR ip_address=?)
             AND created_at > ?
           LIMIT 1""",
        (event_type, device_mac, device_mac, ip_address, ip_address, cutoff)
    ).fetchone()

    if existing:
        return None  # skip duplicate

    cursor = db.execute(
        """INSERT INTO activity_events
               (event_type, device_mac, ip_address, description, created_at, is_demo)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (event_type, device_mac, ip_address, description, _now(), is_demo)
    )
    db.commit()
    return cursor.lastrowid


def get_events(event_type_filter: str | None = None, limit: int = 100,
               include_demo: bool = True) -> list:
    """Return activity events, optionally filtered by type."""
    db = get_db()
    params = []
    query = "SELECT * FROM activity_events"
    conditions = []

    if event_type_filter:
        conditions.append("event_type = ?")
        params.append(event_type_filter)
    if not include_demo:
        conditions.append("is_demo = 0")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = db.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def create_alert(alert_type: str, device_mac: str | None, ip_address: str | None,
                 message: str, is_demo: int = 0) -> int:
    """Create an alert and a corresponding activity event."""
    db = get_db()
    cursor = db.execute(
        """INSERT INTO alerts
               (alert_type, device_mac, ip_address, message, status, created_at, is_demo)
           VALUES (?, ?, ?, ?, 'active', ?, ?)""",
        (alert_type, device_mac, ip_address, message, _now(), is_demo)
    )
    db.commit()
    alert_id = cursor.lastrowid

    record_event('alert_created', device_mac, ip_address,
                 f"Alert: {message}", is_demo)
    return alert_id


def get_active_alerts(limit: int = 20) -> list:
    """Return active (unacknowledged) alerts, newest first."""
    db = get_db()
    rows = db.execute(
        """SELECT * FROM alerts
           WHERE status = 'active'
           ORDER BY created_at DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_alerts(limit: int = 100) -> list:
    """Return all alerts regardless of status."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def acknowledge_alert(alert_id: int, notes: str | None = None) -> bool:
    """Mark an alert as acknowledged."""
    db = get_db()
    db.execute(
        """UPDATE alerts SET status='acknowledged', acknowledged_at=?, notes=?
           WHERE id=?""",
        (_now(), notes, alert_id)
    )
    db.commit()
    return db.execute("SELECT changes()").fetchone()[0] > 0


def dismiss_alert(alert_id: int, notes: str | None = None) -> bool:
    """Mark an alert as dismissed."""
    db = get_db()
    db.execute(
        """UPDATE alerts SET status='dismissed', acknowledged_at=?, notes=?
           WHERE id=?""",
        (_now(), notes, alert_id)
    )
    db.commit()
    return db.execute("SELECT changes()").fetchone()[0] > 0
