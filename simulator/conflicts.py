"""
simulator/conflicts.py
IP Conflict detection, diagnosis, and real-time virtual resolution.
"""
import json
import datetime
from collections import defaultdict
from simulator.addressing import find_candidate_ip, validate_device_ip
from simulator.dhcp import allocate_dhcp_lease


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def detect_and_update_conflicts(db, network_id: int) -> list[dict]:
    """
    Evaluate all online devices in the network.
    Detect any IPv4 shared by 2 or more devices.
    Update `ip_conflicts` table and create alerts/events.
    Returns list of active conflict dicts.
    """
    dev_rows = db.execute("""
        SELECT * FROM devices 
        WHERE network_id = ? AND ip_address IS NOT NULL AND ip_address != '' AND is_online = 1
    """, (network_id,)).fetchall()

    ip_to_devs = defaultdict(list)
    for dev in dev_rows:
        ip_to_devs[dev['ip_address'].strip()].append(dict(dev))

    current_conflict_ips = {ip: devs for ip, devs in ip_to_devs.items() if len(devs) >= 2}

    # Fetch existing active conflicts in DB
    existing_rows = db.execute("""
        SELECT * FROM ip_conflicts 
        WHERE network_id = ? AND status = 'active'
    """, (network_id,)).fetchall()
    existing_map = {r['ip_address']: dict(r) for r in existing_rows}

    now_str = _now()

    # 1. Handle newly detected or continuing conflicts
    for ip, devs in current_conflict_ips.items():
        dev_ids = [d['id'] for d in devs]
        dev_names = ", ".join(d['name'] for d in devs)
        json_ids = json.dumps(dev_ids)

        if ip in existing_map:
            # Update device_ids if changed
            db.execute("""
                UPDATE ip_conflicts SET device_ids = ? 
                WHERE id = ?
            """, (json_ids, existing_map[ip]['id']))
        else:
            # Insert new active conflict
            cursor = db.execute("""
                INSERT INTO ip_conflicts (network_id, ip_address, device_ids, status, detected_at)
                VALUES (?, ?, ?, 'active', ?)
            """, (network_id, ip, json_ids, now_str))
            conflict_id = cursor.lastrowid

            # Create Alert
            db.execute("""
                INSERT INTO alerts (network_id, alert_type, device_id, message, status, created_at)
                VALUES (?, 'ip_conflict', ?, ?, 'active', ?)
            """, (network_id, dev_ids[0], f"IP Conflict: {ip} is assigned to multiple devices ({dev_names})", now_str))

            # Record Simulation Event
            db.execute("""
                INSERT INTO simulation_events (network_id, category, level, message, details, created_at)
                VALUES (?, 'conflict', 'danger', ?, ?, ?)
            """, (
                network_id,
                f"IP Address Conflict Detected: {ip}",
                json.dumps({'ip': ip, 'devices': [d['name'] for d in devs], 'device_ids': dev_ids}),
                now_str
            ))

    # 2. Handle resolved conflicts (previously active, now cleared)
    for ip, row in existing_map.items():
        if ip not in current_conflict_ips:
            db.execute("""
                UPDATE ip_conflicts SET status = 'resolved', resolved_at = ? 
                WHERE id = ?
            """, (now_str, row['id']))

            # Dismiss matching alerts
            db.execute("""
                UPDATE alerts SET status = 'dismissed' 
                WHERE network_id = ? AND alert_type = 'ip_conflict' AND message LIKE ?
            """, (network_id, f"%{ip}%"))

            # Record event
            db.execute("""
                INSERT INTO simulation_events (network_id, category, level, message, details, created_at)
                VALUES (?, 'conflict', 'success', ?, ?, ?)
            """, (network_id, f"IP Address Conflict Resolved: {ip} is now unique.", None, now_str))

    db.commit()

    # Return active conflicts enriched with device details
    active_rows = db.execute("""
        SELECT * FROM ip_conflicts WHERE network_id = ? AND status = 'active'
    """, (network_id,)).fetchall()

    result = []
    for r in active_rows:
        c = dict(r)
        c['devices'] = current_conflict_ips.get(c['ip_address'], [])
        result.append(c)

    return result


def get_conflict_diagnostics(db, network_id: int, conflict_id: int) -> dict:
    """
    Get detailed diagnostics and candidate resolution parameters for a conflict.
    """
    conflict = db.execute("SELECT * FROM ip_conflicts WHERE id = ? AND network_id = ?",
                          (conflict_id, network_id)).fetchone()
    if not conflict:
        return {'error': 'Conflict not found.'}

    net = db.execute("SELECT * FROM networks WHERE id = ?", (network_id,)).fetchone()
    dev_ids = json.loads(conflict['device_ids'])

    dev_placeholders = ",".join("?" * len(dev_ids))
    dev_rows = db.execute(f"SELECT * FROM devices WHERE id IN ({dev_placeholders})", dev_ids).fetchall()
    devices = [dict(d) for d in dev_rows]

    # Find candidate available IP
    all_devs = db.execute("SELECT ip_address FROM devices WHERE network_id = ? AND ip_address IS NOT NULL",
                          (network_id,)).fetchall()
    occupied = {r['ip_address'] for r in all_devs if r['ip_address']}
    candidate = find_candidate_ip(net['subnet'], net['gateway'], occupied,
                                  net['dhcp_start'], net['dhcp_end'], prefer_static_outside_dhcp=True)

    return {
        'conflict_id': conflict['id'],
        'ip_address': conflict['ip_address'],
        'status': conflict['status'],
        'detected_at': conflict['detected_at'],
        'devices': devices,
        'suggested_ip': candidate,
        'dhcp_available': bool(net['dhcp_enabled']),
        'subnet': net['subnet'],
        'gateway': net['gateway']
    }


def resolve_ip_conflict(db, network_id: int, conflict_id: int,
                        target_device_id: int,
                        mode: str = 'static',
                        new_ip: str = None) -> tuple[bool, str, dict]:
    """
    Apply an actual resolution to an active IP conflict by reconfiguring the target device.
    If mode == 'dhcp': requests a new DHCP lease.
    If mode == 'static': applies specified new_ip (or auto-calculates if omitted).
    Updates database, verifies conflict status, logs event, returns result.
    """
    net = db.execute("SELECT * FROM networks WHERE id = ?", (network_id,)).fetchone()
    dev = db.execute("SELECT * FROM devices WHERE id = ? AND network_id = ?",
                     (target_device_id, network_id)).fetchone()
    if not dev:
        return False, "Target device not found.", {}

    old_ip = dev['ip_address']
    now_str = _now()

    if mode == 'dhcp':
        if not net['dhcp_enabled']:
            return False, "DHCP is disabled on this network.", {}
        success, msg, assigned_ip = allocate_dhcp_lease(db, network_id, target_device_id)
        if not success:
            return False, f"DHCP resolution failed: {msg}", {}
        applied_ip = assigned_ip
        resolution_method = "switched to DHCP lease"
    else:
        # Static assignment
        if not new_ip:
            all_devs = db.execute("SELECT ip_address FROM devices WHERE network_id = ? AND ip_address IS NOT NULL",
                                  (network_id,)).fetchall()
            occupied = {r['ip_address'] for r in all_devs if r['ip_address']}
            new_ip = find_candidate_ip(net['subnet'], net['gateway'], occupied,
                                       net['dhcp_start'], net['dhcp_end'])
            if not new_ip:
                return False, "No free candidate IP address found in the subnet.", {}

        # Validate proposed IP
        valid, err = validate_device_ip(new_ip, net['subnet'], net['gateway'])
        if not valid:
            return False, f"Invalid resolution IP: {err}", {}

        # Check if new_ip is already in use by another device
        in_use = db.execute("""
            SELECT id, name FROM devices 
            WHERE network_id = ? AND id != ? AND ip_address = ? AND is_online = 1
        """, (network_id, target_device_id, new_ip)).fetchone()
        if in_use:
            return False, f"Target IP {new_ip} is already assigned to active device '{in_use['name']}'.", {}

        # Update target device
        db.execute("""
            UPDATE devices 
            SET ip_address = ?, ip_mode = 'static', subnet_mask = ?, gateway = ?, updated_at = ?
            WHERE id = ?
        """, (new_ip, net['netmask'], net['gateway'], now_str, target_device_id))
        applied_ip = new_ip
        resolution_method = f"reconfigured with static IP {new_ip}"

    # Log simulation resolution event
    db.execute("""
        INSERT INTO simulation_events (network_id, category, level, message, details, created_at)
        VALUES (?, 'conflict', 'success', ?, ?, ?)
    """, (
        network_id,
        f"Conflict Resolved: '{dev['name']}' {resolution_method} (was {old_ip})",
        json.dumps({
            'device_id': target_device_id,
            'device_name': dev['name'],
            'old_ip': old_ip,
            'new_ip': applied_ip,
            'mode': mode
        }),
        now_str
    ))
    db.commit()

    # Re-evaluate all conflicts for this network
    active_conflicts = detect_and_update_conflicts(db, network_id)

    return True, f"Device '{dev['name']}' successfully updated to {applied_ip}.", {
        'old_ip': old_ip,
        'new_ip': applied_ip,
        'device_id': target_device_id,
        'device_name': dev['name'],
        'remaining_active_conflicts': len(active_conflicts)
    }
