"""
tests/test_sim_dhcp.py
Unit tests for virtual DHCP pool, lease tracking, and pool exhaustion.
"""
from database.db import get_db
from simulator.dhcp import allocate_dhcp_lease, release_dhcp_lease


def test_dhcp_allocation_and_release(app_ctx):
    db = get_db()
    # Create network with 2-IP pool: 192.168.10.100 to 192.168.10.101
    cursor = db.execute("""
        INSERT INTO networks (name, subnet, netmask, gateway, dhcp_enabled, dhcp_start, dhcp_end, created_at, updated_at)
        VALUES ('Test Net', '192.168.10.0/24', '255.255.255.0', '192.168.10.1', 1, '192.168.10.100', '192.168.10.101', '2026-01-01', '2026-01-01')
    """)
    net_id = cursor.lastrowid

    # Create 3 devices
    dev1 = db.execute("INSERT INTO devices (network_id, name, device_type, mac_address, ip_mode, created_at, updated_at) VALUES (?, 'Dev1', 'laptop', '02:00:00:00:00:01', 'dhcp', '2026-01-01', '2026-01-01')", (net_id,)).lastrowid
    dev2 = db.execute("INSERT INTO devices (network_id, name, device_type, mac_address, ip_mode, created_at, updated_at) VALUES (?, 'Dev2', 'laptop', '02:00:00:00:00:02', 'dhcp', '2026-01-01', '2026-01-01')", (net_id,)).lastrowid
    dev3 = db.execute("INSERT INTO devices (network_id, name, device_type, mac_address, ip_mode, created_at, updated_at) VALUES (?, 'Dev3', 'laptop', '02:00:00:00:00:03', 'dhcp', '2026-01-01', '2026-01-01')", (net_id,)).lastrowid

    # 1st Allocation
    ok1, msg1, ip1 = allocate_dhcp_lease(db, net_id, dev1)
    assert ok1 is True
    assert ip1 == '192.168.10.100'

    # 2nd Allocation
    ok2, msg2, ip2 = allocate_dhcp_lease(db, net_id, dev2)
    assert ok2 is True
    assert ip2 == '192.168.10.101'

    # 3rd Allocation -> Pool Exhaustion!
    ok3, msg3, ip3 = allocate_dhcp_lease(db, net_id, dev3)
    assert ok3 is False
    assert "DHCP pool exhausted" in msg3
    assert ip3 is None

    # Release dev1
    rel_ok, rel_msg = release_dhcp_lease(db, net_id, dev1)
    assert rel_ok is True

    # Now dev3 can get lease!
    ok3_retry, msg3_retry, ip3_retry = allocate_dhcp_lease(db, net_id, dev3)
    assert ok3_retry is True
    assert ip3_retry == '192.168.10.100'
