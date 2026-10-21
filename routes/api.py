"""
routes/api.py
JSON REST API endpoints powering the NodeScope interactive simulator.
"""
import datetime
from flask import Blueprint, request, jsonify
from database.db import get_db
from simulator.addressing import (
    validate_network_settings, validate_device_ip,
    generate_virtual_mac, is_valid_mac
)
from simulator.dhcp import allocate_dhcp_lease, release_dhcp_lease
from simulator.conflicts import (
    detect_and_update_conflicts, get_conflict_diagnostics, resolve_ip_conflict
)
from simulator.ping import simulate_ping
from simulator.arp import get_virtual_arp_table
from simulator.events import record_simulation_event, get_recent_events, get_active_alerts

api_bp = Blueprint('api', __name__, url_prefix='/api')


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ----------------------------------------------------------------------
# Networks API
# ----------------------------------------------------------------------

@api_bp.route('/networks', methods=['POST'])
def create_network():
    """Create a new virtual LAN network project."""
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'Network name is required.'}), 400

    subnet = data.get('subnet', '192.168.10.0/24')
    gateway = data.get('gateway', '192.168.10.1')
    dhcp_enabled = bool(data.get('dhcp_enabled', True))
    dhcp_start = data.get('dhcp_start', '192.168.10.100')
    dhcp_end = data.get('dhcp_end', '192.168.10.199')
    description = (data.get('description') or '').strip()

    valid, err, parsed = validate_network_settings(
        subnet, gateway, dhcp_enabled, dhcp_start, dhcp_end
    )
    if not valid:
        return jsonify({'success': False, 'error': err}), 400

    db = get_db()
    now_str = _now()
    cursor = db.execute("""
        INSERT INTO networks (name, description, subnet, netmask, gateway, dhcp_enabled, dhcp_start, dhcp_end, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name, description, parsed['subnet'], parsed['netmask'], parsed['gateway'],
        parsed['dhcp_enabled'], parsed['dhcp_start'], parsed['dhcp_end'], now_str, now_str
    ))
    net_id = cursor.lastrowid

    # Automatically initialize default virtual gateway router representing configured gateway
    db.execute("""
        INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, subnet_mask, gateway, ip_mode, is_online, is_approved, pos_x, pos_y, created_at, updated_at)
        VALUES (?, 'Default Gateway Router', 'router', ?, ?, ?, ?, 'static', 1, 1, 380, 80, ?, ?)
    """, (
        net_id, generate_virtual_mac(), parsed['gateway'], parsed['netmask'], parsed['gateway'], now_str, now_str
    ))

    record_simulation_event(db, net_id, 'network', 'info', f"Virtual network '{name}' ({parsed['subnet']}) created.")
    db.commit()

    return jsonify({'success': True, 'network_id': net_id, 'message': 'Network created successfully.'})


@api_bp.route('/networks/<int:network_id>', methods=['GET'])
def get_network(network_id: int):
    """Retrieve network configuration."""
    db = get_db()
    net = db.execute("SELECT * FROM networks WHERE id = ?", (network_id,)).fetchone()
    if not net:
        return jsonify({'success': False, 'error': 'Network not found.'}), 404
    return jsonify({'success': True, 'network': dict(net)})


@api_bp.route('/networks/<int:network_id>', methods=['DELETE'])
def delete_network(network_id: int):
    """Delete a network project and all associated entities."""
    db = get_db()
    db.execute("DELETE FROM networks WHERE id = ?", (network_id,))
    db.commit()
    return jsonify({'success': True, 'message': 'Network deleted.'})


# ----------------------------------------------------------------------
# Topology State API
# ----------------------------------------------------------------------

@api_bp.route('/networks/<int:network_id>/topology', methods=['GET'])
def get_topology(network_id: int):
    """Fetch complete live topology state."""
    db = get_db()
    net = db.execute("SELECT * FROM networks WHERE id = ?", (network_id,)).fetchone()
    if not net:
        return jsonify({'success': False, 'error': 'Network not found.'}), 404

    # Run conflict detection to ensure active conflicts table is 100% synchronized
    active_conflicts = detect_and_update_conflicts(db, network_id)

    dev_rows = db.execute("SELECT * FROM devices WHERE network_id = ? ORDER BY id ASC", (network_id,)).fetchall()
    conn_rows = db.execute("SELECT * FROM connections WHERE network_id = ?", (network_id,)).fetchall()
    alerts = get_active_alerts(db, network_id)
    events = get_recent_events(db, network_id, limit=30)

    # Build set of device IDs currently in conflict
    conflict_ip_set = {c['ip_address'] for c in active_conflicts}
    devices = []
    for d in dev_rows:
        dev = dict(d)
        dev['in_conflict'] = bool(dev['ip_address'] and dev['ip_address'] in conflict_ip_set)
        devices.append(dev)

    return jsonify({
        'success': True,
        'network': dict(net),
        'devices': devices,
        'connections': [dict(c) for c in conn_rows],
        'conflicts': active_conflicts,
        'alerts': alerts,
        'recent_events': events
    })


# ----------------------------------------------------------------------
# Devices API
# ----------------------------------------------------------------------

@api_bp.route('/networks/<int:network_id>/devices', methods=['POST'])
def add_device(network_id: int):
    """Add a new device to the network."""
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    device_type = data.get('device_type', 'desktop')
    pos_x = float(data.get('pos_x', 200))
    pos_y = float(data.get('pos_y', 200))
    ip_mode = data.get('ip_mode', 'dhcp')
    is_approved = int(data.get('is_approved', 1))

    if not name:
        return jsonify({'success': False, 'error': 'Device name is required.'}), 400

    db = get_db()
    net = db.execute("SELECT * FROM networks WHERE id = ?", (network_id,)).fetchone()
    if not net:
        return jsonify({'success': False, 'error': 'Network not found.'}), 404

    mac = generate_virtual_mac()
    now_str = _now()

    # Switches and APs don't require IP configuration on simple L2 topology
    ip_address = None
    if device_type in ('switch', 'access_point'):
        ip_mode = 'none'

    cursor = db.execute("""
        INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, subnet_mask, gateway, ip_mode, is_online, is_approved, pos_x, pos_y, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)
    """, (
        network_id, name, device_type, mac, ip_address, net['netmask'], net['gateway'],
        ip_mode, is_approved, pos_x, pos_y, now_str, now_str
    ))
    device_id = cursor.lastrowid

    # If unapproved, generate an alert
    if not is_approved:
        db.execute("""
            INSERT INTO alerts (network_id, alert_type, device_id, message, status, created_at)
            VALUES (?, 'unapproved_device', ?, ?, 'active', ?)
        """, (network_id, device_id, f"Security Alert: Unapproved device '{name}' added to network.", now_str))

    record_simulation_event(db, network_id, 'device', 'info', f"Added device '{name}' ({device_type.title()}) with MAC {mac}.")

    # Auto-request DHCP lease if in DHCP mode
    if ip_mode == 'dhcp' and net['dhcp_enabled']:
        allocate_dhcp_lease(db, network_id, device_id)

    db.commit()
    detect_and_update_conflicts(db, network_id)

    new_dev = db.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
    return jsonify({'success': True, 'device': dict(new_dev)})


@api_bp.route('/devices/<int:device_id>', methods=['PUT'])
def update_device(device_id: int):
    """Update device configuration, status, or coordinates."""
    data = request.get_json() or {}
    db = get_db()
    dev = db.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
    if not dev:
        return jsonify({'success': False, 'error': 'Device not found.'}), 404

    network_id = dev['network_id']
    net = db.execute("SELECT * FROM networks WHERE id = ?", (network_id,)).fetchone()

    name = data.get('name', dev['name']).strip()
    is_online = int(data.get('is_online', dev['is_online']))
    is_approved = int(data.get('is_approved', dev['is_approved']))
    pos_x = float(data.get('pos_x', dev['pos_x']))
    pos_y = float(data.get('pos_y', dev['pos_y']))
    ip_mode = data.get('ip_mode', dev['ip_mode'])
    ip_address = data.get('ip_address', dev['ip_address'])

    # Validate MAC if custom provided
    mac_address = (data.get('mac_address') or dev['mac_address']).strip().upper()
    if not is_valid_mac(mac_address):
        return jsonify({'success': False, 'error': 'Invalid MAC address format (use XX:XX:XX:XX:XX:XX).' }), 400

    # If static IP provided, validate format (intentionally permit duplicates so conflicts can be demonstrated)
    if ip_mode == 'static' and ip_address:
        ip_address = ip_address.strip()
        valid, err = validate_device_ip(ip_address, net['subnet'], net['gateway'])
        if not valid:
            return jsonify({'success': False, 'error': err}), 400

    now_str = _now()
    db.execute("""
        UPDATE devices 
        SET name = ?, mac_address = ?, ip_address = ?, ip_mode = ?, is_online = ?, is_approved = ?, pos_x = ?, pos_y = ?, updated_at = ?
        WHERE id = ?
    """, (name, mac_address, ip_address, ip_mode, is_online, is_approved, pos_x, pos_y, now_str, device_id))

    # If approved status changed to approved, clear unapproved alerts for this device
    if is_approved and not dev['is_approved']:
        db.execute("""
            UPDATE alerts SET status = 'dismissed' 
            WHERE network_id = ? AND device_id = ? AND alert_type = 'unapproved_device'
        """, (network_id, device_id))
        record_simulation_event(db, network_id, 'approval', 'success', f"Device '{name}' approved by administrator.")

    db.commit()

    # Re-evaluate conflicts
    detect_and_update_conflicts(db, network_id)

    updated_dev = db.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
    return jsonify({'success': True, 'device': dict(updated_dev)})


@api_bp.route('/devices/<int:device_id>', methods=['DELETE'])
def delete_device(device_id: int):
    """Delete a virtual device."""
    db = get_db()
    dev = db.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
    if not dev:
        return jsonify({'success': False, 'error': 'Device not found.'}), 404

    network_id = dev['network_id']
    name = dev['name']
    db.execute("DELETE FROM devices WHERE id = ?", (device_id,))
    record_simulation_event(db, network_id, 'device', 'info', f"Deleted device '{name}'.")
    db.commit()

    detect_and_update_conflicts(db, network_id)
    return jsonify({'success': True, 'message': f"Device '{name}' deleted."})


# ----------------------------------------------------------------------
# Connections API
# ----------------------------------------------------------------------

@api_bp.route('/networks/<int:network_id>/connections', methods=['POST'])
def add_connection(network_id: int):
    """Connect two devices in the virtual topology."""
    data = request.get_json() or {}
    dev_a_id = data.get('device_a_id')
    dev_b_id = data.get('device_b_id')
    link_type = data.get('link_type', 'wired')

    if not dev_a_id or not dev_b_id or dev_a_id == dev_b_id:
        return jsonify({'success': False, 'error': 'Two distinct devices must be selected.'}), 400

    db = get_db()
    dev_a = db.execute("SELECT * FROM devices WHERE id = ? AND network_id = ?", (dev_a_id, network_id)).fetchone()
    dev_b = db.execute("SELECT * FROM devices WHERE id = ? AND network_id = ?", (dev_b_id, network_id)).fetchone()

    if not dev_a or not dev_b:
        return jsonify({'success': False, 'error': 'One or both devices do not exist.'}), 404

    # Check for existing connection between these two devices
    existing = db.execute("""
        SELECT id FROM connections 
        WHERE network_id = ? AND 
              ((device_a_id = ? AND device_b_id = ?) OR (device_a_id = ? AND device_b_id = ?))
    """, (network_id, dev_a_id, dev_b_id, dev_b_id, dev_a_id)).fetchone()

    if existing:
        return jsonify({'success': False, 'error': 'A connection already exists between these devices.'}), 400

    cursor = db.execute("""
        INSERT INTO connections (network_id, device_a_id, device_b_id, link_type, status, created_at)
        VALUES (?, ?, ?, ?, 'active', ?)
    """, (network_id, dev_a_id, dev_b_id, link_type, _now()))
    conn_id = cursor.lastrowid

    record_simulation_event(db, network_id, 'connection', 'info',
                            f"Connected '{dev_a['name']}' to '{dev_b['name']}' ({link_type} link).")
    db.commit()

    return jsonify({'success': True, 'connection_id': conn_id, 'message': 'Devices connected.'})


@api_bp.route('/connections/<int:conn_id>', methods=['DELETE'])
def delete_connection(conn_id: int):
    """Disconnect a link between devices."""
    db = get_db()
    conn = db.execute("SELECT * FROM connections WHERE id = ?", (conn_id,)).fetchone()
    if not conn:
        return jsonify({'success': False, 'error': 'Connection not found.'}), 404

    network_id = conn['network_id']
    db.execute("DELETE FROM connections WHERE id = ?", (conn_id,))
    record_simulation_event(db, network_id, 'connection', 'info', "Disconnected virtual network link.")
    db.commit()

    return jsonify({'success': True, 'message': 'Connection removed.'})


# ----------------------------------------------------------------------
# DHCP API
# ----------------------------------------------------------------------

@api_bp.route('/devices/<int:device_id>/dhcp', methods=['POST'])
def request_dhcp(device_id: int):
    """Request or renew a DHCP lease for a device."""
    db = get_db()
    dev = db.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
    if not dev:
        return jsonify({'success': False, 'error': 'Device not found.'}), 404

    network_id = dev['network_id']
    success, msg, assigned_ip = allocate_dhcp_lease(db, network_id, device_id)
    level = 'success' if success else 'warning'
    record_simulation_event(db, network_id, 'dhcp', level, msg)

    if not success:
        # Create alert if exhausted
        db.execute("""
            INSERT INTO alerts (network_id, alert_type, device_id, message, status, created_at)
            VALUES (?, 'dhcp_exhausted', ?, ?, 'active', ?)
        """, (network_id, device_id, msg, _now()))
        db.commit()
        return jsonify({'success': False, 'error': msg}), 400

    detect_and_update_conflicts(db, network_id)
    updated_dev = db.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
    return jsonify({'success': True, 'message': msg, 'device': dict(updated_dev)})


@api_bp.route('/devices/<int:device_id>/dhcp/release', methods=['POST'])
def release_dhcp(device_id: int):
    """Release active DHCP lease."""
    db = get_db()
    dev = db.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
    if not dev:
        return jsonify({'success': False, 'error': 'Device not found.'}), 404

    success, msg = release_dhcp_lease(db, dev['network_id'], device_id)
    record_simulation_event(db, dev['network_id'], 'dhcp', 'info', msg)
    detect_and_update_conflicts(db, dev['network_id'])

    updated_dev = db.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
    return jsonify({'success': True, 'message': msg, 'device': dict(updated_dev)})


# ----------------------------------------------------------------------
# Conflicts API
# ----------------------------------------------------------------------

@api_bp.route('/networks/<int:network_id>/conflicts', methods=['GET'])
def list_conflicts(network_id: int):
    """List active conflicts with full device context."""
    db = get_db()
    conflicts = detect_and_update_conflicts(db, network_id)
    return jsonify({'success': True, 'conflicts': conflicts})


@api_bp.route('/conflicts/<int:conflict_id>', methods=['GET'])
def get_conflict_info(conflict_id: int):
    """Get conflict diagnostic information and resolution suggestions."""
    db = get_db()
    conflict = db.execute("SELECT * FROM ip_conflicts WHERE id = ?", (conflict_id,)).fetchone()
    if not conflict:
        return jsonify({'success': False, 'error': 'Conflict not found.'}), 404

    diag = get_conflict_diagnostics(db, conflict['network_id'], conflict_id)
    return jsonify({'success': True, 'diagnostic': diag})


@api_bp.route('/conflicts/<int:conflict_id>/resolve', methods=['POST'])
def resolve_conflict(conflict_id: int):
    """
    Actually resolve an IP address conflict in the virtual network!
    Reconfigures the target device and updates simulation state.
    """
    data = request.get_json() or {}
    target_device_id = data.get('target_device_id')
    mode = data.get('mode', 'static')  # 'static' or 'dhcp'
    new_ip = data.get('new_ip')

    if not target_device_id:
        return jsonify({'success': False, 'error': 'Target device must be specified.'}), 400

    db = get_db()
    conflict = db.execute("SELECT * FROM ip_conflicts WHERE id = ?", (conflict_id,)).fetchone()
    if not conflict:
        return jsonify({'success': False, 'error': 'Conflict not found.'}), 404

    success, msg, details = resolve_ip_conflict(
        db, conflict['network_id'], conflict_id, int(target_device_id), mode=mode, new_ip=new_ip
    )
    if not success:
        return jsonify({'success': False, 'error': msg}), 400

    return jsonify({'success': True, 'message': msg, 'details': details})


# ----------------------------------------------------------------------
# Ping and ARP Simulation API
# ----------------------------------------------------------------------

@api_bp.route('/networks/<int:network_id>/ping', methods=['POST'])
def ping_devices(network_id: int):
    """Run simulated ICMP Echo / Ping test between two devices."""
    data = request.get_json() or {}
    src_id = data.get('source_id')
    dst_id = data.get('destination_id')

    if not src_id or not dst_id:
        return jsonify({'success': False, 'error': 'Both source and destination devices are required.'}), 400

    db = get_db()
    result = simulate_ping(db, network_id, int(src_id), int(dst_id))
    return jsonify({'success': True, 'result': result})


@api_bp.route('/networks/<int:network_id>/arp', methods=['GET'])
def get_arp_table(network_id: int):
    """Retrieve virtual ARP table."""
    db = get_db()
    table = get_virtual_arp_table(db, network_id)
    return jsonify({'success': True, 'arp_table': table})


# ----------------------------------------------------------------------
# Events and Alerts API
# ----------------------------------------------------------------------

@api_bp.route('/networks/<int:network_id>/events', methods=['GET'])
def get_events(network_id: int):
    """Get recent events stream."""
    db = get_db()
    events = get_recent_events(db, network_id, limit=60)
    return jsonify({'success': True, 'events': events})


@api_bp.route('/networks/<int:network_id>/events/clear', methods=['POST'])
def clear_events_console(network_id: int):
    """Clear simulation events for this network."""
    db = get_db()
    db.execute("DELETE FROM simulation_events WHERE network_id = ?", (network_id,))
    record_simulation_event(db, network_id, 'network', 'info', "Console events cleared by user.")
    db.commit()
    return jsonify({'success': True, 'message': 'Console cleared.'})


@api_bp.route('/alerts/<int:alert_id>/dismiss', methods=['POST'])
def dismiss_alert(alert_id: int):
    """Dismiss an active alert."""
    db = get_db()
    db.execute("UPDATE alerts SET status = 'dismissed' WHERE id = ?", (alert_id,))
    db.commit()
    return jsonify({'success': True, 'message': 'Alert dismissed.'})
