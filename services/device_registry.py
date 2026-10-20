"""
services/device_registry.py
Manages the approved device registry and rogue-device detection.

An 'approved' device is one the administrator has explicitly registered.
An 'unknown' device is one observed on the network but not in the registry.

NOTE: MAC addresses can be randomised (especially mobile devices).
An unknown MAC does not necessarily indicate a malicious device.
Always investigate before drawing conclusions.
"""
import datetime
from database.db import get_db
from services.activity_history import record_event, create_alert


def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + 'Z'


def register_observation(ip: str, mac: str, observed_at: str,
                         scan_id: int, is_demo: int = 0) -> dict:
    """
    Upsert a device based on MAC address.
    - If MAC is new: insert device, create 'device_discovered' event.
    - If MAC exists: update last_seen and ip_address if changed.
    Returns a dict with keys: device_id, is_new, ip_changed.
    """
    db = get_db()
    mac = mac.upper()

    existing = db.execute(
        "SELECT * FROM devices WHERE mac_address = ?", (mac,)
    ).fetchone()

    if existing is None:
        # New device — insert it
        db.execute(
            """INSERT INTO devices
                   (mac_address, ip_address, approved, first_seen, last_seen, is_demo)
               VALUES (?, ?, 0, ?, ?, ?)""",
            (mac, ip, observed_at, observed_at, is_demo)
        )
        db.commit()
        device = db.execute(
            "SELECT * FROM devices WHERE mac_address = ?", (mac,)
        ).fetchone()
        record_event('device_discovered', mac, ip,
                     f"New device observed: MAC {mac} at IP {ip}", is_demo)
        return {'device_id': device['id'], 'is_new': True, 'ip_changed': False}

    # Existing device
    ip_changed = existing['ip_address'] != ip
    db.execute(
        "UPDATE devices SET last_seen=?, ip_address=?, is_demo=? WHERE mac_address=?",
        (observed_at, ip, is_demo, mac)
    )
    db.commit()

    if ip_changed and existing['ip_address']:
        record_event('ip_changed', mac, ip,
                     f"Device {mac} changed IP from {existing['ip_address']} to {ip}",
                     is_demo)

    return {'device_id': existing['id'], 'is_new': False, 'ip_changed': ip_changed}


def check_unknown_devices(observations: list, is_demo: int = 0) -> list:
    """
    Compare observations against the approved device registry.
    Returns observations where the MAC is not approved.
    Also creates alerts for newly unknown devices.
    """
    db = get_db()
    unknown = []

    for obs in observations:
        mac = obs['mac'].upper()
        device = db.execute(
            "SELECT * FROM devices WHERE mac_address = ?", (mac,)
        ).fetchone()

        if device is None or device['approved'] == 0:
            unknown.append(obs)
            # Only alert if there isn't an active alert for this MAC already
            existing_alert = db.execute(
                """SELECT id FROM alerts
                   WHERE alert_type='unknown_device' AND device_mac=?
                     AND status='active' LIMIT 1""",
                (mac,)
            ).fetchone()
            if not existing_alert:
                create_alert(
                    alert_type='unknown_device',
                    device_mac=mac,
                    ip_address=obs['ip'],
                    message=(
                        f"Unknown device observed: MAC {mac} at IP {obs['ip']}. "
                        "This device is not in the approved registry. "
                        "Review and approve it if it belongs on this network."
                    ),
                    is_demo=is_demo
                )

    return unknown


def approve_device(mac: str, friendly_name: str | None = None,
                   notes: str | None = None) -> bool:
    """
    Mark a device as approved and assign an optional friendly name.
    Returns True if the device was found and updated.
    """
    db = get_db()
    mac = mac.upper()
    db.execute(
        """UPDATE devices SET approved=1, friendly_name=?, notes=?
           WHERE mac_address=?""",
        (friendly_name, notes, mac)
    )
    db.commit()
    changed = db.execute("SELECT changes()").fetchone()[0] > 0

    if changed:
        label = friendly_name or mac
        record_event('device_approved', mac, None,
                     f"Device approved: {label} (MAC {mac})")
        # Dismiss active unknown_device alerts for this MAC
        db.execute(
            """UPDATE alerts SET status='dismissed', acknowledged_at=?
               WHERE alert_type='unknown_device' AND device_mac=? AND status='active'""",
            (_now(), mac)
        )
        db.commit()

    return changed


def get_all_devices(search: str | None = None) -> list:
    """Return all devices, with optional search across IP/MAC/name."""
    db = get_db()
    if search:
        pattern = f'%{search}%'
        rows = db.execute(
            """SELECT * FROM devices
               WHERE mac_address LIKE ? OR ip_address LIKE ? OR friendly_name LIKE ?
               ORDER BY last_seen DESC""",
            (pattern, pattern, pattern)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM devices ORDER BY last_seen DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_device_by_mac(mac: str) -> dict | None:
    """Return a single device record by MAC address."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM devices WHERE mac_address = ?", (mac.upper(),)
    ).fetchone()
    return dict(row) if row else None


def get_stats() -> dict:
    """Return summary counts for the dashboard."""
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    approved = db.execute(
        "SELECT COUNT(*) FROM devices WHERE approved=1"
    ).fetchone()[0]
    unknown = db.execute(
        "SELECT COUNT(*) FROM devices WHERE approved=0"
    ).fetchone()[0]
    return {'total': total, 'approved': approved, 'unknown': unknown}
