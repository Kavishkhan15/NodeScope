"""
simulator/dhcp.py
Deterministic Virtual DHCP server simulation.
Allocates, tracks, releases, and renews leases from the configured address pool.
"""
import datetime
import ipaddress


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def get_dhcp_pool_ips(dhcp_start: str, dhcp_end: str) -> list[str]:
    """Generate ordered list of IP strings in the DHCP pool."""
    if not dhcp_start or not dhcp_end:
        return []
    try:
        s = int(ipaddress.ip_address(dhcp_start))
        e = int(ipaddress.ip_address(dhcp_end))
        return [str(ipaddress.ip_address(i)) for i in range(s, e + 1)]
    except ValueError:
        return []


def allocate_dhcp_lease(db, network_id: int, device_id: int) -> tuple[bool, str, str | None]:
    """
    Allocate an available IP from the DHCP pool for the device.
    Returns (success, message, assigned_ip).
    """
    # 1. Fetch network DHCP configuration
    net = db.execute("SELECT * FROM networks WHERE id = ?", (network_id,)).fetchone()
    if not net:
        return False, "Network not found.", None

    if not net['dhcp_enabled']:
        return False, "DHCP service is disabled on this network.", None

    # 2. Fetch device
    dev = db.execute("SELECT * FROM devices WHERE id = ? AND network_id = ?",
                     (device_id, network_id)).fetchone()
    if not dev:
        return False, "Device not found.", None

    pool_ips = get_dhcp_pool_ips(net['dhcp_start'], net['dhcp_end'])
    if not pool_ips:
        return False, "DHCP address pool is invalid or empty.", None

    # 3. Find all currently occupied IPs (devices online or static, excluding this device)
    rows = db.execute("""
        SELECT ip_address FROM devices 
        WHERE network_id = ? AND id != ? AND ip_address IS NOT NULL
    """, (network_id, device_id)).fetchall()
    occupied_ips = {r['ip_address'] for r in rows if r['ip_address']}

    # Also include gateway
    occupied_ips.add(net['gateway'])

    # Also include existing active leases for OTHER devices
    lease_rows = db.execute("""
        SELECT ip_address FROM dhcp_leases 
        WHERE network_id = ? AND device_id != ? AND lease_state = 'active'
    """, (network_id, device_id)).fetchall()
    occupied_ips.update(r['ip_address'] for r in lease_rows if r['ip_address'])

    # 4. Check if device already had a lease that is still valid in the pool and not taken
    existing_lease = db.execute("""
        SELECT ip_address FROM dhcp_leases 
        WHERE network_id = ? AND device_id = ? AND lease_state = 'active'
    """, (network_id, device_id)).fetchone()

    candidate_ip = None
    if existing_lease and existing_lease['ip_address'] in pool_ips and existing_lease['ip_address'] not in occupied_ips:
        candidate_ip = existing_lease['ip_address']
    else:
        # Pick the first free IP in the pool
        for ip in pool_ips:
            if ip not in occupied_ips:
                candidate_ip = ip
                break

    if not candidate_ip:
        msg = f"DHCP pool exhausted ({len(pool_ips)} addresses in {net['dhcp_start']}–{net['dhcp_end']}). No address available."
        return False, msg, None

    # 5. Record/update lease and update device record
    now_str = _now()
    # Mark old leases for this device as released
    db.execute("""
        UPDATE dhcp_leases SET lease_state = 'released' 
        WHERE network_id = ? AND device_id = ?
    """, (network_id, device_id))

    db.execute("""
        INSERT INTO dhcp_leases (network_id, device_id, ip_address, mac_address, lease_state, assigned_at)
        VALUES (?, ?, ?, ?, 'active', ?)
    """, (network_id, device_id, candidate_ip, dev['mac_address'], now_str))

    db.execute("""
        UPDATE devices 
        SET ip_address = ?, subnet_mask = ?, gateway = ?, ip_mode = 'dhcp', updated_at = ?
        WHERE id = ?
    """, (candidate_ip, net['netmask'], net['gateway'], now_str, device_id))

    db.commit()

    msg = f"DHCP allocated {candidate_ip} to '{dev['name']}' ({dev['mac_address']})."
    return True, msg, candidate_ip


def release_dhcp_lease(db, network_id: int, device_id: int) -> tuple[bool, str]:
    """Release active DHCP lease for the device."""
    dev = db.execute("SELECT * FROM devices WHERE id = ? AND network_id = ?",
                     (device_id, network_id)).fetchone()
    if not dev:
        return False, "Device not found."

    db.execute("""
        UPDATE dhcp_leases SET lease_state = 'released' 
        WHERE network_id = ? AND device_id = ?
    """, (network_id, device_id))

    db.execute("""
        UPDATE devices 
        SET ip_address = NULL, updated_at = ? 
        WHERE id = ?
    """, (_now(), device_id))

    db.commit()
    return True, f"Released DHCP lease for '{dev['name']}'."
