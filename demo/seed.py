"""
demo/seed.py
Demo data seeding for NodeScope.

Populates the database with realistic-looking but entirely fabricated records
to demonstrate all features without requiring a real LAN or elevated permissions.

All demo records have is_demo=1 and can be removed with reset_demo().
The UI shows a prominent 'DEMO MODE' banner when NODESCOPE_DEMO=1 is set.
"""
import json
import datetime
from database.db import get_db


def _ts(minutes_ago: int = 0) -> str:
    """Return ISO 8601 UTC timestamp for N minutes ago."""
    t = datetime.datetime.utcnow() - datetime.timedelta(minutes=minutes_ago)
    return t.isoformat() + 'Z'


def seed_demo_data() -> dict:
    """
    Insert demo records into all tables.
    Safe to call multiple times — checks if demo data already exists first.
    Returns counts of inserted records.
    """
    db = get_db()

    # Check if demo data already exists
    existing = db.execute("SELECT COUNT(*) FROM devices WHERE is_demo=1").fetchone()[0]
    if existing > 0:
        return {'message': 'Demo data already exists. Run reset-demo first to re-seed.'}

    counts = {}

    # -------------------------------------------------------------------
    # 1. Insert a demo scan
    # -------------------------------------------------------------------
    db.execute(
        """INSERT INTO scans (subnet, started_at, completed_at, status,
                              device_count, is_demo)
           VALUES (?, ?, ?, 'completed', 7, 1)""",
        ('192.168.1.0/24', _ts(30), _ts(29))
    )
    db.commit()
    scan_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    counts['scans'] = 1

    # -------------------------------------------------------------------
    # 2. Approved devices
    # -------------------------------------------------------------------
    approved_devices = [
        ('AA:BB:CC:DD:EE:01', '192.168.1.1',   'Home Gateway / Router',    1),
        ('AA:BB:CC:DD:EE:02', '192.168.1.100',  'Desktop PC',               1),
        ('AA:BB:CC:DD:EE:03', '192.168.1.101',  'Laptop',                   1),
        ('AA:BB:CC:DD:EE:04', '192.168.1.102',  'Smartphone',               1),
        ('AA:BB:CC:DD:EE:05', '192.168.1.103',  'Network Printer',          1),
    ]
    for mac, ip, name, approved in approved_devices:
        db.execute(
            """INSERT INTO devices
                   (mac_address, ip_address, friendly_name, approved,
                    first_seen, last_seen, is_demo)
               VALUES (?, ?, ?, ?, ?, ?, 1)""",
            (mac, ip, name, approved, _ts(120), _ts(30))
        )

    # 3. Unknown device (not approved)
    db.execute(
        """INSERT INTO devices
               (mac_address, ip_address, friendly_name, approved,
                first_seen, last_seen, is_demo)
           VALUES ('FF:EE:DD:CC:BB:06', '192.168.1.150',
                   NULL, 0, ?, ?, 1)""",
        (_ts(30), _ts(30))
    )

    db.commit()
    counts['devices'] = 6

    # -------------------------------------------------------------------
    # 4. Device observations
    # -------------------------------------------------------------------
    observations = [
        (scan_id, '192.168.1.1',   'AA:BB:CC:DD:EE:01', _ts(29)),
        (scan_id, '192.168.1.100', 'AA:BB:CC:DD:EE:02', _ts(29)),
        (scan_id, '192.168.1.101', 'AA:BB:CC:DD:EE:03', _ts(29)),
        (scan_id, '192.168.1.102', 'AA:BB:CC:DD:EE:04', _ts(29)),
        (scan_id, '192.168.1.103', 'AA:BB:CC:DD:EE:05', _ts(29)),
        (scan_id, '192.168.1.150', 'FF:EE:DD:CC:BB:06', _ts(29)),
        # Conflict: 192.168.1.100 appears with a second MAC
        (scan_id, '192.168.1.100', '11:22:33:44:55:02', _ts(29)),
    ]
    for scan_id_, ip, mac, ts in observations:
        db.execute(
            """INSERT INTO device_observations
                   (scan_id, ip_address, mac_address, observed_at, is_demo)
               VALUES (?, ?, ?, ?, 1)""",
            (scan_id_, ip, mac, ts)
        )
    db.commit()
    counts['observations'] = len(observations)

    # -------------------------------------------------------------------
    # 5. IP conflict (192.168.1.100 with two MACs)
    # -------------------------------------------------------------------
    evidence = json.dumps([
        {'ip': '192.168.1.100', 'mac': 'AA:BB:CC:DD:EE:02', 'observed_at': _ts(29)},
        {'ip': '192.168.1.100', 'mac': '11:22:33:44:55:02', 'observed_at': _ts(29)},
    ])
    db.execute(
        """INSERT INTO ip_conflicts
               (ip_address, mac_address_1, mac_address_2, first_seen, last_seen,
                status, evidence, is_demo)
           VALUES ('192.168.1.100', 'AA:BB:CC:DD:EE:02', '11:22:33:44:55:02',
                   ?, ?, 'possible_conflict', ?, 1)""",
        (_ts(29), _ts(29), evidence)
    )
    db.commit()
    counts['conflicts'] = 1

    # -------------------------------------------------------------------
    # 6. Alerts
    # -------------------------------------------------------------------
    alerts = [
        ('unknown_device', 'FF:EE:DD:CC:BB:06', '192.168.1.150', 'active',
         'Unknown device observed: MAC FF:EE:DD:CC:BB:06 at IP 192.168.1.150. '
         'This device is not in the approved registry.'),
        ('ip_conflict', None, '192.168.1.100', 'active',
         'Possible IP conflict: 192.168.1.100 observed with MAC AA:BB:CC:DD:EE:02 '
         'and also 11:22:33:44:55:02.'),
        ('ip_change', 'AA:BB:CC:DD:EE:02', '192.168.1.105', 'acknowledged',
         'Device AA:BB:CC:DD:EE:02 (Desktop PC) was previously at 192.168.1.100, '
         'now appears at 192.168.1.105.'),
    ]
    for atype, mac, ip, status, msg in alerts:
        db.execute(
            """INSERT INTO alerts
                   (alert_type, device_mac, ip_address, message, status,
                    created_at, is_demo)
               VALUES (?, ?, ?, ?, ?, ?, 1)""",
            (atype, mac, ip, msg, status, _ts(28))
        )
    db.commit()
    counts['alerts'] = len(alerts)

    # -------------------------------------------------------------------
    # 7. Activity events
    # -------------------------------------------------------------------
    events = [
        ('device_discovered', 'FF:EE:DD:CC:BB:06', '192.168.1.150',
         'New device observed: MAC FF:EE:DD:CC:BB:06 at IP 192.168.1.150', _ts(29)),
        ('conflict_detected', None, '192.168.1.100',
         'Possible IP conflict: 192.168.1.100 has MACs AA:BB:CC:DD:EE:02 and 11:22:33:44:55:02',
         _ts(29)),
        ('ip_changed', 'AA:BB:CC:DD:EE:02', '192.168.1.105',
         'Device AA:BB:CC:DD:EE:02 changed IP from 192.168.1.100 to 192.168.1.105',
         _ts(60)),
        ('device_approved', 'AA:BB:CC:DD:EE:03', None,
         'Device approved: Laptop (MAC AA:BB:CC:DD:EE:03)', _ts(90)),
        ('alert_created', 'FF:EE:DD:CC:BB:06', '192.168.1.150',
         'Alert: Unknown device observed at 192.168.1.150', _ts(28)),
    ]
    for etype, mac, ip, desc, ts in events:
        db.execute(
            """INSERT INTO activity_events
                   (event_type, device_mac, ip_address, description, created_at, is_demo)
               VALUES (?, ?, ?, ?, ?, 1)""",
            (etype, mac, ip, desc, ts)
        )
    db.commit()
    counts['events'] = len(events)

    return counts


def reset_demo() -> dict:
    """
    Delete all demo records (is_demo=1) from all tables.
    Does NOT delete real (is_demo=0) records.
    Returns counts of deleted rows per table.
    """
    db = get_db()
    tables = [
        'resolution_actions',
        'activity_events',
        'alerts',
        'ip_conflicts',
        'device_observations',
        'devices',
        'scans',
    ]
    counts = {}
    for table in tables:
        # resolution_actions doesn't have is_demo; delete by conflict_id
        if table == 'resolution_actions':
            db.execute(
                """DELETE FROM resolution_actions WHERE conflict_id IN
                   (SELECT id FROM ip_conflicts WHERE is_demo=1)"""
            )
        else:
            db.execute(f"DELETE FROM {table} WHERE is_demo=1")  # noqa: S608
        counts[table] = db.execute("SELECT changes()").fetchone()[0]
    db.commit()
    return counts
