"""
tests/test_sim_ping.py
Unit tests for simulated ICMP Ping diagnostic engine.
"""
from database.db import get_db
from simulator.ping import simulate_ping
from simulator.conflicts import detect_and_update_conflicts


def test_simulate_ping_conditions(app_ctx):
    db = get_db()
    net_id = db.execute("""
        INSERT INTO networks (name, subnet, netmask, gateway, created_at, updated_at)
        VALUES ('Lab', '192.168.10.0/24', '255.255.255.0', '192.168.10.1', '2026-01-01', '2026-01-01')
    """).lastrowid

    # Devices
    pc1 = db.execute("INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, is_online, created_at, updated_at) VALUES (?, 'PC1', 'desktop', '02:00:00:00:00:01', '192.168.10.11', 1, '2026-01-01', '2026-01-01')", (net_id,)).lastrowid
    pc2 = db.execute("INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, is_online, created_at, updated_at) VALUES (?, 'PC2', 'desktop', '02:00:00:00:00:02', '192.168.10.12', 1, '2026-01-01', '2026-01-01')", (net_id,)).lastrowid

    # 1. Not connected yet -> Ping should fail on path
    res1 = simulate_ping(db, net_id, pc1, pc2)
    assert res1['status'] == 'failed'
    assert "No active communication path" in res1['message']

    # 2. Connect devices -> Ping should succeed
    db.execute("INSERT INTO connections (network_id, device_a_id, device_b_id, status, created_at) VALUES (?, ?, ?, 'active', '2026-01-01')", (net_id, pc1, pc2))
    res2 = simulate_ping(db, net_id, pc1, pc2)
    assert res2['status'] == 'success'
    assert "successfully reached" in res2['message']

    # 3. Power off destination -> Ping should fail on power state
    db.execute("UPDATE devices SET is_online = 0 WHERE id = ?", (pc2,))
    res3 = simulate_ping(db, net_id, pc1, pc2)
    assert res3['status'] == 'failed'
    assert "powered OFF" in res3['message']

    # Power back on
    db.execute("UPDATE devices SET is_online = 1 WHERE id = ?", (pc2,))

    # 4. Trigger IP conflict on destination
    pc3 = db.execute("INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, is_online, created_at, updated_at) VALUES (?, 'PC3', 'desktop', '02:00:00:00:00:03', '192.168.10.12', 1, '2026-01-01', '2026-01-01')", (net_id,)).lastrowid
    detect_and_update_conflicts(db, net_id)

    res4 = simulate_ping(db, net_id, pc1, pc2)
    assert res4['status'] == 'failed'
    assert "active IP conflict" in res4['message']

    # 5. Clear conflict and test unapproved device (NAC block)
    db.execute("DELETE FROM devices WHERE id = ?", (pc3,))
    detect_and_update_conflicts(db, net_id)

    db.execute("UPDATE devices SET is_approved = 0 WHERE id = ?", (pc2,))
    res5 = simulate_ping(db, net_id, pc1, pc2)
    assert res5['status'] == 'failed'
    assert "UNAPPROVED" in res5['message']

    # Approve device -> ping succeeds
    db.execute("UPDATE devices SET is_approved = 1 WHERE id = ?", (pc2,))
    res6 = simulate_ping(db, net_id, pc1, pc2)
    assert res6['status'] == 'success'
