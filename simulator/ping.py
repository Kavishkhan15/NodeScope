"""
simulator/ping.py
Simulated ICMP Echo / Ping Diagnostic Engine.
Deterministically evaluates reachability based on:
1. Power state (both online?)
2. IP configuration (both have valid IPs?)
3. Subnet alignment (both on same LAN subnet?)
4. Physical/data-link path (active topology link via switches/AP/router?)
5. IP conflict ambiguity (is either IP involved in an active address conflict?)
"""
import ipaddress
import datetime
import json
from simulator.connectivity import find_path


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def simulate_ping(db, network_id: int, src_id: int, dst_id: int) -> dict:
    """
    Perform a deterministic simulated ping from src_id to dst_id.
    Returns diagnostic dict with status ('success' or 'failed'), message, step checks, and hops.
    """
    now_str = _now()
    net = db.execute("SELECT * FROM networks WHERE id = ?", (network_id,)).fetchone()
    if not net:
        return {'status': 'failed', 'message': 'Network project not found.', 'steps': []}

    src = db.execute("SELECT * FROM devices WHERE id = ? AND network_id = ?",
                     (src_id, network_id)).fetchone()
    dst = db.execute("SELECT * FROM devices WHERE id = ? AND network_id = ?",
                     (dst_id, network_id)).fetchone()

    if not src or not dst:
        return {'status': 'failed', 'message': 'Source or destination device not found.', 'steps': []}

    steps = []
    subnet = ipaddress.ip_network(net['subnet'], strict=False)

    # 1. Power State Check
    if not src['is_online']:
        msg = f"Ping failed: Source device '{src['name']}' is powered OFF."
        steps.append({'check': 'Power State (Source)', 'passed': False, 'detail': 'Device is offline'})
        _log_ping(db, network_id, src['name'], dst['name'], False, msg)
        return {'status': 'failed', 'message': msg, 'steps': steps, 'path': []}
    steps.append({'check': 'Power State (Source)', 'passed': True, 'detail': f"'{src['name']}' is online"})

    if not dst['is_online']:
        msg = f"Ping failed: Destination device '{dst['name']}' is powered OFF."
        steps.append({'check': 'Power State (Destination)', 'passed': False, 'detail': 'Device is offline'})
        _log_ping(db, network_id, src['name'], dst['name'], False, msg)
        return {'status': 'failed', 'message': msg, 'steps': steps, 'path': []}
    steps.append({'check': 'Power State (Destination)', 'passed': True, 'detail': f"'{dst['name']}' is online"})

    # 2. IP Assignment Check
    if not src['ip_address']:
        msg = f"Ping failed: Source device '{src['name']}' has no assigned IP address."
        steps.append({'check': 'IP Configuration (Source)', 'passed': False, 'detail': 'No IP address configured'})
        _log_ping(db, network_id, src['name'], dst['name'], False, msg)
        return {'status': 'failed', 'message': msg, 'steps': steps, 'path': []}
    steps.append({'check': 'IP Configuration (Source)', 'passed': True, 'detail': f"IP is {src['ip_address']}"})

    if not dst['ip_address']:
        msg = f"Ping failed: Destination device '{dst['name']}' has no assigned IP address."
        steps.append({'check': 'IP Configuration (Destination)', 'passed': False, 'detail': 'No IP address configured'})
        _log_ping(db, network_id, src['name'], dst['name'], False, msg)
        return {'status': 'failed', 'message': msg, 'steps': steps, 'path': []}
    steps.append({'check': 'IP Configuration (Destination)', 'passed': True, 'detail': f"IP is {dst['ip_address']}"})

    # 3. Subnet Membership Check
    try:
        src_ip = ipaddress.ip_address(src['ip_address'])
        dst_ip = ipaddress.ip_address(dst['ip_address'])
    except ValueError as e:
        msg = f"Ping failed: Malformed IP address: {e}"
        return {'status': 'failed', 'message': msg, 'steps': steps, 'path': []}

    if src_ip not in subnet:
        msg = f"Ping failed: Source IP {src_ip} does not belong to subnet {subnet}."
        steps.append({'check': 'Subnet Membership (Source)', 'passed': False, 'detail': f"{src_ip} not in {subnet}"})
        _log_ping(db, network_id, src['name'], dst['name'], False, msg)
        return {'status': 'failed', 'message': msg, 'steps': steps, 'path': []}
    steps.append({'check': 'Subnet Membership (Source)', 'passed': True, 'detail': f"{src_ip} in {subnet}"})

    if dst_ip not in subnet:
        msg = f"Ping failed: Destination IP {dst_ip} does not belong to subnet {subnet}."
        steps.append({'check': 'Subnet Membership (Destination)', 'passed': False, 'detail': f"{dst_ip} not in {subnet}"})
        _log_ping(db, network_id, src['name'], dst['name'], False, msg)
        return {'status': 'failed', 'message': msg, 'steps': steps, 'path': []}
    steps.append({'check': 'Subnet Membership (Destination)', 'passed': True, 'detail': f"{dst_ip} in {subnet}"})

    # 4. IP Conflict Ambiguity Check
    conflict_rows = db.execute("""
        SELECT ip_address FROM ip_conflicts 
        WHERE network_id = ? AND status = 'active'
    """, (network_id,)).fetchall()
    active_conflict_ips = {r['ip_address'] for r in conflict_rows}

    if src['ip_address'] in active_conflict_ips:
        msg = f"Ping failed: Source IP {src['ip_address']} is involved in an active IP conflict."
        steps.append({'check': 'IP Conflict Check (Source)', 'passed': False, 'detail': 'Ambiguous MAC address binding'})
        _log_ping(db, network_id, src['name'], dst['name'], False, msg)
        return {'status': 'failed', 'message': msg, 'steps': steps, 'path': []}
    steps.append({'check': 'IP Conflict Check (Source)', 'passed': True, 'detail': 'No IP collision'})

    if dst['ip_address'] in active_conflict_ips:
        msg = f"Ping failed: Destination IP {dst['ip_address']} is involved in an active IP conflict (ARP ambiguity)."
        steps.append({'check': 'IP Conflict Check (Destination)', 'passed': False, 'detail': 'Multiple hosts responding to destination IP'})
        _log_ping(db, network_id, src['name'], dst['name'], False, msg)
        return {'status': 'failed', 'message': msg, 'steps': steps, 'path': []}
    steps.append({'check': 'IP Conflict Check (Destination)', 'passed': True, 'detail': 'No IP collision'})

    # 5. Physical/Data-Link Path Check (Topology BFS)
    has_path, path_devs, diag = find_path(db, network_id, src_id, dst_id)
    if not has_path:
        msg = f"Ping failed: No active communication path exists ({diag})."
        steps.append({'check': 'Topology Link & Path', 'passed': False, 'detail': diag})
        _log_ping(db, network_id, src['name'], dst['name'], False, msg)
        return {'status': 'failed', 'message': msg, 'steps': steps, 'path': []}

    path_names = [d['name'] for d in path_devs]
    steps.append({'check': 'Topology Link & Path', 'passed': True, 'detail': ' → '.join(path_names)})

    # Success!
    msg = f"Ping successful: '{src['name']}' ({src['ip_address']}) successfully reached '{dst['name']}' ({dst['ip_address']})."
    _log_ping(db, network_id, src['name'], dst['name'], True, msg, path_names)

    return {
        'status': 'success',
        'message': msg,
        'steps': steps,
        'path': path_names,
        'rtt_ms': 1.4  # Realistic local LAN RTT indicator
    }


def _log_ping(db, network_id: int, src_name: str, dst_name: str, success: bool, message: str, path: list = None):
    level = 'success' if success else 'warning'
    db.execute("""
        INSERT INTO simulation_events (network_id, category, level, message, details, created_at)
        VALUES (?, 'ping', ?, ?, ?, ?)
    """, (
        network_id,
        level,
        message,
        json.dumps({'source': src_name, 'destination': dst_name, 'success': success, 'path': path or []}),
        _now()
    ))
    db.commit()
