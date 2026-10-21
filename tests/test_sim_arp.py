"""
tests/test_sim_arp.py
Tests for educational virtual ARP table generation.
"""
from database.db import get_db
from simulator.arp import get_virtual_arp_table


def test_virtual_arp_table_and_ambiguity(app_ctx):
    db = get_db()
    net_id = db.execute("""
        INSERT INTO networks (name, subnet, netmask, gateway, created_at, updated_at)
        VALUES ('Lab', '192.168.10.0/24', '255.255.255.0', '192.168.10.1', '2026-01-01', '2026-01-01')
    """).lastrowid

    # 1 unique host
    db.execute("""
        INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, is_online, created_at, updated_at)
        VALUES (?, 'PC1', 'desktop', '02:00:00:00:00:01', '192.168.10.10', 1, '2026-01-01', '2026-01-01')
    """, (net_id,))

    # 2 conflicting hosts on 192.168.10.20
    db.execute("""
        INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, is_online, created_at, updated_at)
        VALUES (?, 'PC2A', 'desktop', '02:00:00:00:00:02', '192.168.10.20', 1, '2026-01-01', '2026-01-01')
    """, (net_id,))
    db.execute("""
        INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, is_online, created_at, updated_at)
        VALUES (?, 'PC2B', 'desktop', '02:00:00:00:00:03', '192.168.10.20', 1, '2026-01-01', '2026-01-01')
    """, (net_id,))

    table = get_virtual_arp_table(db, net_id)
    assert len(table) == 3

    # Check that 192.168.10.10 is normal
    pc1_entry = next(r for r in table if r['ip_address'] == '192.168.10.10')
    assert pc1_entry['is_conflict'] is False
    assert 'DYNAMIC' in pc1_entry['status']

    # Check that 192.168.10.20 entries are marked AMBIGUOUS
    conf_entries = [r for r in table if r['ip_address'] == '192.168.10.20']
    assert len(conf_entries) == 2
    for entry in conf_entries:
        assert entry['is_conflict'] is True
        assert 'AMBIGUOUS' in entry['status']
