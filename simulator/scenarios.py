"""
simulator/scenarios.py
5 Ready-made educational scenarios for classroom and viva presentations.
"""
import datetime
from simulator.addressing import generate_virtual_mac
from simulator.conflicts import detect_and_update_conflicts


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def load_example_scenario(db, scenario_id: int) -> int:
    """
    Load one of the 5 educational scenarios into SQLite.
    Returns the created network_id.
    """
    now = _now()

    if scenario_id == 1:
        # Scenario 1: Working Computer Lab
        cursor = db.execute("""
            INSERT INTO networks (name, description, subnet, netmask, gateway, dhcp_enabled, dhcp_start, dhcp_end, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Scenario 1: Working Computer Lab",
            "A standard, healthy local area network with router, central switch, workstations, laptop, and network printer. All devices can communicate.",
            "192.168.10.0/24", "255.255.255.0", "192.168.10.1", 1, "192.168.10.100", "192.168.10.199", now, now
        ))
        net_id = cursor.lastrowid

        # Devices
        r_id = _add_dev(db, net_id, "Main Gateway Router", "router", "192.168.10.1", "static", 1, 1, 350, 70)
        sw_id = _add_dev(db, net_id, "Lab Core Switch", "switch", None, "static", 1, 1, 350, 200)
        pc1_id = _add_dev(db, net_id, "Student Desktop 01", "desktop", "192.168.10.11", "static", 1, 1, 150, 340)
        pc2_id = _add_dev(db, net_id, "Student Desktop 02", "desktop", "192.168.10.12", "static", 1, 1, 290, 340)
        lap_id = _add_dev(db, net_id, "Instructor Laptop", "laptop", "192.168.10.15", "static", 1, 1, 430, 340)
        prn_id = _add_dev(db, net_id, "Network Laser Printer", "printer", "192.168.10.25", "static", 1, 1, 570, 340)

        # Connections: All connect to Switch, Switch connects to Router
        _add_conn(db, net_id, r_id, sw_id)
        _add_conn(db, net_id, sw_id, pc1_id)
        _add_conn(db, net_id, sw_id, pc2_id)
        _add_conn(db, net_id, sw_id, lap_id)
        _add_conn(db, net_id, sw_id, prn_id)

    elif scenario_id == 2:
        # Scenario 2: Duplicate IP Conflict
        cursor = db.execute("""
            INSERT INTO networks (name, description, subnet, netmask, gateway, dhcp_enabled, dhcp_start, dhcp_end, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Scenario 2: Duplicate IP Conflict",
            "Two workstations (Workstation Alpha and Workstation Beta) have accidentally been assigned the identical static IP 192.168.10.50.",
            "192.168.10.0/24", "255.255.255.0", "192.168.10.1", 1, "192.168.10.100", "192.168.10.199", now, now
        ))
        net_id = cursor.lastrowid

        r_id = _add_dev(db, net_id, "Gateway Router", "router", "192.168.10.1", "static", 1, 1, 350, 70)
        sw_id = _add_dev(db, net_id, "FastEthernet Switch", "switch", None, "static", 1, 1, 350, 200)
        pc_a = _add_dev(db, net_id, "Workstation Alpha", "desktop", "192.168.10.50", "static", 1, 1, 200, 340)
        pc_b = _add_dev(db, net_id, "Workstation Beta", "desktop", "192.168.10.50", "static", 1, 1, 500, 340)

        _add_conn(db, net_id, r_id, sw_id)
        _add_conn(db, net_id, sw_id, pc_a)
        _add_conn(db, net_id, sw_id, pc_b)

    elif scenario_id == 3:
        # Scenario 3: DHCP Address Assignment
        cursor = db.execute("""
            INSERT INTO networks (name, description, subnet, netmask, gateway, dhcp_enabled, dhcp_start, dhcp_end, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Scenario 3: DHCP Address Assignment",
            "Demonstrates dynamic host configuration. End devices join the network with DHCP enabled and receive leases from the gateway.",
            "192.168.20.0/24", "255.255.255.0", "192.168.20.1", 1, "192.168.20.100", "192.168.20.120", now, now
        ))
        net_id = cursor.lastrowid

        r_id = _add_dev(db, net_id, "DHCP Router Server", "router", "192.168.20.1", "static", 1, 1, 350, 70)
        ap_id = _add_dev(db, net_id, "Wireless Access Point", "access_point", None, "static", 1, 1, 350, 200)
        phone = _add_dev(db, net_id, "Student Smartphone", "smartphone", "192.168.20.100", "dhcp", 1, 1, 220, 340)
        lap = _add_dev(db, net_id, "Campus Laptop", "laptop", "192.168.20.101", "dhcp", 1, 1, 480, 340)

        _add_conn(db, net_id, r_id, ap_id)
        _add_conn(db, net_id, ap_id, phone, link_type='wireless')
        _add_conn(db, net_id, ap_id, lap, link_type='wireless')

        # Insert leases
        db.execute("INSERT INTO dhcp_leases (network_id, device_id, ip_address, mac_address, lease_state, assigned_at) VALUES (?, ?, ?, ?, 'active', ?)",
                   (net_id, phone, "192.168.20.100", "02:20:AA:11:00:01", now))
        db.execute("INSERT INTO dhcp_leases (network_id, device_id, ip_address, mac_address, lease_state, assigned_at) VALUES (?, ?, ?, ?, 'active', ?)",
                   (net_id, lap, "192.168.20.101", "02:20:AA:11:00:02", now))

    elif scenario_id == 4:
        # Scenario 4: Disconnected Device & Path Diagnostics
        cursor = db.execute("""
            INSERT INTO networks (name, description, subnet, netmask, gateway, dhcp_enabled, dhcp_start, dhcp_end, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Scenario 4: Disconnected Device Diagnostics",
            "A departmental network where Accounting PC is disconnected from the switch. Ping tests illustrate link failure and diagnostic feedback.",
            "192.168.30.0/24", "255.255.255.0", "192.168.30.1", 1, "192.168.30.100", "192.168.30.150", now, now
        ))
        net_id = cursor.lastrowid

        r_id = _add_dev(db, net_id, "Department Gateway", "router", "192.168.30.1", "static", 1, 1, 350, 70)
        sw_id = _add_dev(db, net_id, "Department Switch", "switch", None, "static", 1, 1, 350, 200)
        pc1 = _add_dev(db, net_id, "Finance PC 01", "desktop", "192.168.30.10", "static", 1, 1, 200, 340)
        pc2 = _add_dev(db, net_id, "Accounting PC (Unplugged)", "desktop", "192.168.30.20", "static", 1, 1, 500, 340)

        _add_conn(db, net_id, r_id, sw_id)
        _add_conn(db, net_id, sw_id, pc1)
        # pc2 intentionally left unconnected!

    else:
        # Scenario 5: Unapproved Rogue Device
        cursor = db.execute("""
            INSERT INTO networks (name, description, subnet, netmask, gateway, dhcp_enabled, dhcp_start, dhcp_end, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Scenario 5: Unapproved Rogue Device",
            "An unauthorized laptop has connected to the office switch and claimed an IP, triggering security alerts for administrator review.",
            "192.168.40.0/24", "255.255.255.0", "192.168.40.1", 1, "192.168.40.100", "192.168.40.150", now, now
        ))
        net_id = cursor.lastrowid

        r_id = _add_dev(db, net_id, "Office Gateway", "router", "192.168.40.1", "static", 1, 1, 350, 70)
        sw_id = _add_dev(db, net_id, "Access Switch", "switch", None, "static", 1, 1, 350, 200)
        staff_pc = _add_dev(db, net_id, "Staff Workstation", "desktop", "192.168.40.10", "static", 1, 1, 200, 340)
        rogue_lap = _add_dev(db, net_id, "Unidentified Personal Laptop", "laptop", "192.168.40.77", "static", 1, 0, 500, 340)

        _add_conn(db, net_id, r_id, sw_id)
        _add_conn(db, net_id, sw_id, staff_pc)
        _add_conn(db, net_id, sw_id, rogue_lap)

        db.execute("""
            INSERT INTO alerts (network_id, alert_type, device_id, message, status, created_at)
            VALUES (?, 'unapproved_device', ?, ?, 'active', ?)
        """, (net_id, rogue_lap, "Security Alert: Unapproved device 'Unidentified Personal Laptop' connected to LAN.", now))

    # Evaluate any conflicts and log initial event
    detect_and_update_conflicts(db, net_id)

    db.execute("""
        INSERT INTO simulation_events (network_id, category, level, message, created_at)
        VALUES (?, 'network', 'info', ?, ?)
    """, (net_id, f"Loaded preset scenario: {scenario_id}", now))

    db.commit()
    return net_id


def _add_dev(db, net_id, name, dev_type, ip, ip_mode, is_online, is_approved, x, y):
    cursor = db.execute("""
        INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, subnet_mask, gateway, ip_mode, is_online, is_approved, pos_x, pos_y, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, '255.255.255.0', '192.168.10.1', ?, ?, ?, ?, ?, ?, ?)
    """, (net_id, name, dev_type, generate_virtual_mac(), ip, ip_mode, is_online, is_approved, x, y, _now(), _now()))
    return cursor.lastrowid


def _add_conn(db, net_id, da, db_id, link_type='wired'):
    db.execute("""
        INSERT INTO connections (network_id, device_a_id, device_b_id, link_type, status, created_at)
        VALUES (?, ?, ?, ?, 'active', ?)
    """, (net_id, da, db_id, link_type, _now()))
