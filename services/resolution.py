"""
services/resolution.py
Guided IP conflict resolution assistance.

This module SUGGESTS possible corrective actions and alternative IP addresses.
It does NOT automatically change device configurations.

Administrators must:
1. Review the recommendation.
2. Manually reconfigure the affected device(s).
3. Run a follow-up scan to verify the conflict no longer appears.
"""
import ipaddress
import datetime
from database.db import get_db
from services.conflict_detection import get_conflict_by_id


def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + 'Z'


def _get_all_known_ips() -> set:
    """Collect all IP addresses currently in use (devices + observations)."""
    db = get_db()
    ips = set()

    rows = db.execute("SELECT ip_address FROM devices WHERE ip_address IS NOT NULL").fetchall()
    for r in rows:
        if r['ip_address']:
            ips.add(r['ip_address'])

    rows = db.execute("SELECT DISTINCT ip_address FROM device_observations").fetchall()
    for r in rows:
        if r['ip_address']:
            ips.add(r['ip_address'])

    return ips


def suggest_resolution(conflict_id: int) -> dict:
    """
    Analyse a conflict and suggest a resolution.

    Returns a dict with:
      - conflict_ip: the conflicting IP
      - mac1, mac2: the two observed MACs
      - suggested_ip: a candidate alternative IP (may be None)
      - reasoning: human-readable explanation
      - steps: list of recommended action steps
      - warnings: list of important caveats
      - can_suggest: bool indicating whether a suggestion is possible
    """
    conflict = get_conflict_by_id(conflict_id)
    if not conflict:
        return {'error': 'Conflict not found.', 'can_suggest': False}

    ip = conflict['ip_address']
    mac1 = conflict['mac_address_1']
    mac2 = conflict['mac_address_2']

    result = {
        'conflict_ip': ip,
        'mac1': mac1,
        'mac2': mac2,
        'suggested_ip': None,
        'reasoning': '',
        'steps': [],
        'warnings': [],
        'can_suggest': False
    }

    # Parse the conflict IP to determine the /24 subnet to suggest within
    try:
        addr = ipaddress.ip_address(ip)
        # Assume /24 for suggestion (typical home LAN)
        network = ipaddress.ip_network(f"{addr.packed[0]}.{addr.packed[1]}.{addr.packed[2]}.0/24")
    except ValueError:
        result['reasoning'] = f"Could not parse IP address '{ip}'."
        return result

    known_ips = _get_all_known_ips()

    # Find a candidate: avoid network (.0), gateway (.1), broadcast (.255),
    # and any known-in-use addresses
    excluded = {
        str(network.network_address),          # x.x.x.0
        str(list(network.hosts())[0]),         # x.x.x.1 (likely gateway)
        str(network.broadcast_address),        # x.x.x.255
    }
    excluded.update(known_ips)

    candidate = None
    # Search from .50 upward to find a free address (avoids common DHCP pool .2–.50)
    for host in network.hosts():
        h = str(host)
        if h not in excluded and int(host.packed[-1]) >= 50:
            candidate = h
            break

    result['suggested_ip'] = candidate
    result['can_suggest'] = candidate is not None

    result['reasoning'] = (
        f"IP address {ip} was observed responding to ARP requests from two different "
        f"MAC addresses: {mac1} and {mac2}. "
        "This suggests two devices may be configured with the same static IP address, "
        "or a stale ARP entry is causing a false positive. "
        "Common causes include: a device that was recently reconfigured, a VM or container "
        "sharing a host IP, or MAC address randomisation on a mobile device."
    )

    if candidate:
        result['steps'] = [
            f"Identify which device (MAC {mac1} or {mac2}) has IP {ip} assigned statically.",
            f"On that device, change its static IP to {candidate} (or another unused address in the {network} subnet).",
            "Make sure the new address is outside your DHCP pool range to prevent future conflicts.",
            "If the address was assigned by DHCP, update the DHCP reservation or lease on your router.",
            f"After making changes, return here and click 'Verify Resolution' to run a new observation and confirm the conflict is gone.",
            "If the conflict still appears after reconfiguration, the cause may be a stale ARP cache — wait a few minutes and scan again."
        ]
    else:
        result['steps'] = [
            f"All addresses in {network} appear to be in use. Check your DHCP pool and static assignments.",
            "Consider using a larger subnet or reclaiming unused addresses.",
            "After resolving manually, click 'Verify Resolution'."
        ]

    result['warnings'] = [
        "NodeScope CANNOT automatically change device IP configurations. "
        "You must log in to the affected device(s) and change settings manually.",
        "An ARP scan cannot guarantee that a suggested IP address is truly unused — "
        "a device may be offline during the scan. Verify before assigning.",
        "If DHCP is assigning conflicting addresses, the correct fix is to update "
        "the DHCP server reservation or pool, not just reconfigure the client device.",
        "Always verify the resolution with a follow-up scan before closing the case."
    ]

    return result


def record_resolution_attempt(conflict_id: int, recommended_ip: str | None,
                               action_taken: str, admin_notes: str | None) -> int:
    """
    Record an administrator's resolution attempt.
    Returns the resolution_action row id.
    """
    db = get_db()
    cursor = db.execute(
        """INSERT INTO resolution_actions
               (conflict_id, recommended_ip, action_taken, admin_notes, created_at, verified)
           VALUES (?, ?, ?, ?, ?, 0)""",
        (conflict_id, recommended_ip, action_taken, admin_notes, _now())
    )
    db.commit()

    # Move conflict to under_investigation if still at possible_conflict
    db.execute(
        """UPDATE ip_conflicts SET status='under_investigation'
           WHERE id=? AND status='possible_conflict'""",
        (conflict_id,)
    )
    db.commit()
    return cursor.lastrowid


def verify_resolution(conflict_id: int, still_present: bool,
                      admin_notes: str | None = None) -> bool:
    """
    Mark the latest resolution attempt as verified.
    If still_present=False, marks the conflict as resolved.
    If still_present=True, keeps it under_investigation.
    Returns True on success.
    """
    db = get_db()

    # Mark latest action as verified
    latest = db.execute(
        """SELECT id FROM resolution_actions WHERE conflict_id=?
           ORDER BY created_at DESC LIMIT 1""",
        (conflict_id,)
    ).fetchone()

    if latest:
        db.execute(
            "UPDATE resolution_actions SET verified=1 WHERE id=?", (latest['id'],)
        )

    if not still_present:
        db.execute(
            """UPDATE ip_conflicts SET status='resolved', investigation_notes=?
               WHERE id=?""",
            (admin_notes, conflict_id)
        )
        from services.activity_history import record_event
        conflict = db.execute(
            "SELECT ip_address FROM ip_conflicts WHERE id=?", (conflict_id,)
        ).fetchone()
        if conflict:
            record_event('conflict_resolved', None, conflict['ip_address'],
                         f"IP conflict for {conflict['ip_address']} verified as resolved.")
    else:
        if admin_notes:
            db.execute(
                "UPDATE ip_conflicts SET investigation_notes=? WHERE id=?",
                (admin_notes, conflict_id)
            )

    db.commit()
    return True
