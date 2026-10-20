"""
services/conflict_detection.py
Detects possible IP address conflicts by identifying IP addresses
that have been observed with more than one MAC address.

IMPORTANT CAVEAT:
Multiple MACs for one IP can have innocent explanations:
  - ARP caching of a stale record
  - Proxy ARP or NAT devices
  - Virtual machines or containers sharing a host NIC
  - MAC address randomisation
NodeScope marks these as 'Possible Conflict' — not confirmed conflicts.
Always investigate before taking corrective action.
"""
import json
import datetime
from collections import defaultdict
from database.db import get_db
from services.activity_history import record_event, create_alert


def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + 'Z'


def detect_conflicts(observations: list) -> list:
    """
    Group observations by IP address.
    Return a list of conflict dicts for any IP with 2+ distinct MACs.
    Each conflict dict: {ip, macs: [mac1, mac2, ...], observations: [...]}
    """
    ip_to_macs = defaultdict(set)
    ip_to_obs = defaultdict(list)

    for obs in observations:
        ip = obs['ip']
        mac = obs['mac'].upper()
        ip_to_macs[ip].add(mac)
        ip_to_obs[ip].append(obs)

    conflicts = []
    for ip, macs in ip_to_macs.items():
        if len(macs) >= 2:
            mac_list = sorted(macs)
            conflicts.append({
                'ip': ip,
                'macs': mac_list,
                'observations': ip_to_obs[ip]
            })

    return conflicts


def record_conflict(ip: str, mac1: str, mac2: str, observations: list,
                    is_demo: int = 0) -> int:
    """
    Insert a new conflict record, or update last_seen if one already exists.
    Creates an alert and activity event for new conflicts.
    Returns the conflict row id.
    """
    db = get_db()
    mac1, mac2 = mac1.upper(), mac2.upper()
    evidence = json.dumps(observations)
    now = _now()

    # Check if a conflict for this IP already exists (any status)
    existing = db.execute(
        "SELECT id, status FROM ip_conflicts WHERE ip_address=? LIMIT 1", (ip,)
    ).fetchone()

    if existing:
        # Update last_seen and evidence; don't downgrade resolved → possible
        db.execute(
            """UPDATE ip_conflicts
               SET last_seen=?, evidence=?, mac_address_1=?, mac_address_2=?,
                   status = CASE WHEN status='resolved' THEN 'possible_conflict'
                                 ELSE status END
               WHERE id=?""",
            (now, evidence, mac1, mac2, existing['id'])
        )
        db.commit()
        return existing['id']

    # New conflict
    cursor = db.execute(
        """INSERT INTO ip_conflicts
               (ip_address, mac_address_1, mac_address_2, first_seen, last_seen,
                status, evidence, is_demo)
           VALUES (?, ?, ?, ?, ?, 'possible_conflict', ?, ?)""",
        (ip, mac1, mac2, now, now, evidence, is_demo)
    )
    db.commit()
    conflict_id = cursor.lastrowid

    # Alert and event
    create_alert(
        alert_type='ip_conflict',
        device_mac=None,
        ip_address=ip,
        message=(
            f"Possible IP conflict detected: {ip} was observed with MAC "
            f"{mac1} and also {mac2}. Investigation recommended."
        ),
        is_demo=is_demo
    )
    record_event('conflict_detected', None, ip,
                 f"Possible IP conflict: {ip} has MACs {mac1} and {mac2}", is_demo)

    return conflict_id


def process_scan_conflicts(observations: list, is_demo: int = 0) -> list:
    """
    Run conflict detection over a list of observations and persist any conflicts.
    Returns list of conflict records that were created or updated.
    """
    conflicts_found = detect_conflicts(observations)
    result = []
    for c in conflicts_found:
        macs = c['macs']
        cid = record_conflict(c['ip'], macs[0], macs[1], c['observations'], is_demo)
        result.append({'conflict_id': cid, 'ip': c['ip'], 'macs': macs})
    return result


def get_all_conflicts(status_filter: str | None = None) -> list:
    """Return all conflict records, optionally filtered by status."""
    db = get_db()
    if status_filter:
        rows = db.execute(
            "SELECT * FROM ip_conflicts WHERE status=? ORDER BY last_seen DESC",
            (status_filter,)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM ip_conflicts ORDER BY last_seen DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_conflict_by_id(conflict_id: int) -> dict | None:
    """Return a single conflict record with its resolution history."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM ip_conflicts WHERE id=?", (conflict_id,)
    ).fetchone()
    if not row:
        return None
    conflict = dict(row)
    # Parse evidence JSON
    if conflict.get('evidence'):
        try:
            conflict['evidence_list'] = json.loads(conflict['evidence'])
        except (json.JSONDecodeError, TypeError):
            conflict['evidence_list'] = []
    else:
        conflict['evidence_list'] = []

    # Fetch resolution actions
    actions = db.execute(
        "SELECT * FROM resolution_actions WHERE conflict_id=? ORDER BY created_at DESC",
        (conflict_id,)
    ).fetchall()
    conflict['resolution_history'] = [dict(a) for a in actions]
    return conflict


def update_conflict_status(conflict_id: int, status: str,
                           notes: str | None = None) -> bool:
    """Update conflict status. Valid statuses: possible_conflict, under_investigation, resolved."""
    valid_statuses = {'possible_conflict', 'under_investigation', 'resolved'}
    if status not in valid_statuses:
        return False
    db = get_db()
    db.execute(
        "UPDATE ip_conflicts SET status=?, investigation_notes=? WHERE id=?",
        (status, notes, conflict_id)
    )
    db.commit()

    if status == 'resolved':
        conflict = db.execute(
            "SELECT ip_address FROM ip_conflicts WHERE id=?", (conflict_id,)
        ).fetchone()
        if conflict:
            record_event('conflict_resolved', None, conflict['ip_address'],
                         f"IP conflict for {conflict['ip_address']} marked as resolved.")

    return db.execute("SELECT changes()").fetchone()[0] > 0


def get_active_conflict_count() -> int:
    """Return count of non-resolved conflicts."""
    db = get_db()
    return db.execute(
        "SELECT COUNT(*) FROM ip_conflicts WHERE status != 'resolved'"
    ).fetchone()[0]
