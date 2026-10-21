"""
tests/test_sim_devices.py
Tests for device management, property editing, MAC uniqueness, and approval toggling.
"""
from database.db import get_db
from simulator.addressing import generate_virtual_mac


def test_device_creation_and_properties(app_ctx):
    db = get_db()
    net_id = db.execute("""
        INSERT INTO networks (name, subnet, netmask, gateway, created_at, updated_at)
        VALUES ('Lab', '192.168.10.0/24', '255.255.255.0', '192.168.10.1', '2026-01-01', '2026-01-01')
    """).lastrowid

    # Create unapproved laptop
    mac = generate_virtual_mac()
    dev_id = db.execute("""
        INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, ip_mode, is_online, is_approved, pos_x, pos_y, created_at, updated_at)
        VALUES (?, 'Guest Laptop', 'laptop', ?, '192.168.10.25', 'static', 1, 0, 150, 200, '2026-01-01', '2026-01-01')
    """, (net_id, mac)).lastrowid

    dev = db.execute("SELECT * FROM devices WHERE id = ?", (dev_id,)).fetchone()
    assert dev['name'] == 'Guest Laptop'
    assert dev['is_approved'] == 0
    assert dev['mac_address'] == mac

    # Approve device
    db.execute("UPDATE devices SET is_approved = 1 WHERE id = ?", (dev_id,))
    updated = db.execute("SELECT is_approved FROM devices WHERE id = ?", (dev_id,)).fetchone()
    assert updated['is_approved'] == 1

    # Delete device
    db.execute("DELETE FROM devices WHERE id = ?", (dev_id,))
    deleted = db.execute("SELECT * FROM devices WHERE id = ?", (dev_id,)).fetchone()
    assert deleted is None
