"""
tests/test_sim_connectivity.py
Unit tests for BFS path discovery over switches, routers, and active links.
"""
from database.db import get_db
from simulator.connectivity import find_path


def test_topology_path_finding(app_ctx):
    db = get_db()
    # Create network
    net_id = db.execute("""
        INSERT INTO networks (name, subnet, netmask, gateway, created_at, updated_at)
        VALUES ('Lab', '192.168.10.0/24', '255.255.255.0', '192.168.10.1', '2026-01-01', '2026-01-01')
    """).lastrowid

    # Devices: PC1 -> Switch -> PC2, PC3 isolated
    pc1 = db.execute("INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, is_online, created_at, updated_at) VALUES (?, 'PC1', 'desktop', '02:00:00:00:00:01', '192.168.10.10', 1, '2026-01-01', '2026-01-01')", (net_id,)).lastrowid
    sw = db.execute("INSERT INTO devices (network_id, name, device_type, mac_address, is_online, created_at, updated_at) VALUES (?, 'SW', 'switch', '02:00:00:00:00:02', 1, '2026-01-01', '2026-01-01')", (net_id,)).lastrowid
    pc2 = db.execute("INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, is_online, created_at, updated_at) VALUES (?, 'PC2', 'desktop', '02:00:00:00:00:03', '192.168.10.20', 1, '2026-01-01', '2026-01-01')", (net_id,)).lastrowid
    pc3 = db.execute("INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, is_online, created_at, updated_at) VALUES (?, 'PC3', 'desktop', '02:00:00:00:00:04', '192.168.10.30', 1, '2026-01-01', '2026-01-01')", (net_id,)).lastrowid

    # Connect PC1 to Switch, Switch to PC2
    db.execute("INSERT INTO connections (network_id, device_a_id, device_b_id, status, created_at) VALUES (?, ?, ?, 'active', '2026-01-01')", (net_id, pc1, sw))
    db.execute("INSERT INTO connections (network_id, device_a_id, device_b_id, status, created_at) VALUES (?, ?, ?, 'active', '2026-01-01')", (net_id, sw, pc2))

    # Path between PC1 and PC2 should succeed through Switch
    has_path, path_devs, diag = find_path(db, net_id, pc1, pc2)
    assert has_path is True
    assert len(path_devs) == 3
    assert [d['name'] for d in path_devs] == ['PC1', 'SW', 'PC2']

    # Path to isolated PC3 should fail
    has_path_3, _, diag_3 = find_path(db, net_id, pc1, pc3)
    assert has_path_3 is False
    assert "not connected" in diag_3 or "No active" in diag_3

    # Power off the switch: path between PC1 and PC2 should fail
    db.execute("UPDATE devices SET is_online = 0 WHERE id = ?", (sw,))
    has_path_off, _, _ = find_path(db, net_id, pc1, pc2)
    assert has_path_off is False
