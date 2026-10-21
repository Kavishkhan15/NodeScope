"""
tests/test_sim_conflicts.py
Unit tests for duplicate IP detection and guided conflict resolution.
"""
from database.db import get_db
from simulator.conflicts import (
    detect_and_update_conflicts, get_conflict_diagnostics, resolve_ip_conflict
)


def test_conflict_detection_and_resolution(app_ctx):
    db = get_db()
    net_id = db.execute("""
        INSERT INTO networks (name, subnet, netmask, gateway, dhcp_enabled, dhcp_start, dhcp_end, created_at, updated_at)
        VALUES ('Lab', '192.168.10.0/24', '255.255.255.0', '192.168.10.1', 1, '192.168.10.100', '192.168.10.199', '2026-01-01', '2026-01-01')
    """).lastrowid

    # Create two devices with the SAME IP
    dev_a = db.execute("""
        INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, is_online, created_at, updated_at)
        VALUES (?, 'Alpha', 'desktop', '02:00:00:00:00:01', '192.168.10.50', 1, '2026-01-01', '2026-01-01')
    """, (net_id,)).lastrowid

    dev_b = db.execute("""
        INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, is_online, created_at, updated_at)
        VALUES (?, 'Beta', 'desktop', '02:00:00:00:00:02', '192.168.10.50', 1, '2026-01-01', '2026-01-01')
    """, (net_id,)).lastrowid

    # Detect conflicts
    conflicts = detect_and_update_conflicts(db, net_id)
    assert len(conflicts) == 1
    assert conflicts[0]['ip_address'] == '192.168.10.50'
    assert len(conflicts[0]['devices']) == 2

    # Check alert was created
    alerts = db.execute("SELECT * FROM alerts WHERE network_id = ? AND alert_type = 'ip_conflict'", (net_id,)).fetchall()
    assert len(alerts) >= 1

    # Get diagnostics
    conflict_id = conflicts[0]['id']
    diag = get_conflict_diagnostics(db, net_id, conflict_id)
    assert diag['ip_address'] == '192.168.10.50'
    assert diag['suggested_ip'] is not None
    assert diag['suggested_ip'] != '192.168.10.50'

    # Resolve conflict: Reconfigure Beta with candidate IP
    ok, msg, res_details = resolve_ip_conflict(db, net_id, conflict_id, dev_b, mode='static', new_ip=diag['suggested_ip'])
    assert ok is True
    assert res_details['new_ip'] == diag['suggested_ip']

    # Verify device record was ACTUALLY updated in database
    updated_b = db.execute("SELECT * FROM devices WHERE id = ?", (dev_b,)).fetchone()
    assert updated_b['ip_address'] == diag['suggested_ip']

    # Verify conflict status is now resolved
    conf_row = db.execute("SELECT * FROM ip_conflicts WHERE id = ?", (conflict_id,)).fetchone()
    assert conf_row['status'] == 'resolved'

    # Remaining active conflicts should be 0
    active = detect_and_update_conflicts(db, net_id)
    assert len(active) == 0
