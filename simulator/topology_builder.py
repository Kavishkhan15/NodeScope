"""
simulator/topology_builder.py
Automated network topology generation engine for NodeScope.
Supports:
1. Star Topology (Central switch with radial workstations & gateway router)
2. Bus Topology (Clean linear shared backbone cable connecting stations sequentially)
3. Ring Topology (Closed circular loop with neighboring bidirectional links)
4. Mesh Topology (Full mesh with user-selected node count and diverse link metrics)
5. Tree Topology (Hierarchical core router, distribution switches, and workstation leaves)
6. Hybrid Topology (Multi-cluster Star-Router-Star enterprise network)
"""
import math
import datetime
from simulator.addressing import generate_virtual_mac


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def clear_network_devices(db, network_id: int):
    """Remove existing devices and connections for a network prior to generating new topology."""
    db.execute("DELETE FROM devices WHERE network_id = ?", (network_id,))
    db.execute("DELETE FROM connections WHERE network_id = ?", (network_id,))
    db.execute("DELETE FROM dhcp_leases WHERE network_id = ?", (network_id,))
    db.execute("DELETE FROM ip_conflicts WHERE network_id = ?", (network_id,))
    db.commit()


def generate_topology(db, network_id: int, topology_type: str, options: dict = None) -> dict:
    """
    Master generator dispatcher for requested topology type.
    """
    options = options or {}
    t_type = topology_type.lower().strip()

    clear_network_devices(db, network_id)

    # Get network base subnet info
    net = db.execute("SELECT * FROM networks WHERE id = ?", (network_id,)).fetchone()
    base_prefix = "192.168.10"
    if net and net['subnet']:
        parts = net['subnet'].split('/')[0].split('.')
        if len(parts) >= 3:
            base_prefix = f"{parts[0]}.{parts[1]}.{parts[2]}"

    if t_type == 'star':
        return _build_star(db, network_id, base_prefix, options)
    elif t_type == 'bus':
        return _build_bus(db, network_id, base_prefix, options)
    elif t_type == 'ring':
        return _build_ring(db, network_id, base_prefix, options)
    elif t_type == 'mesh':
        return _build_mesh(db, network_id, base_prefix, options)
    elif t_type == 'tree':
        return _build_tree(db, network_id, base_prefix, options)
    elif t_type == 'hybrid':
        return _build_hybrid(db, network_id, base_prefix, options)
    else:
        return _build_star(db, network_id, base_prefix, options)


def _add_device(db, network_id, name, dev_type, ip, x, y, ip_mode='static', is_online=1, is_approved=1):
    now = _now()
    cursor = db.execute("""
        INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, subnet_mask, gateway, ip_mode, is_online, is_approved, pos_x, pos_y, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, '255.255.255.0', '192.168.10.1', ?, ?, ?, ?, ?, ?, ?)
    """, (network_id, name, dev_type, generate_virtual_mac(), ip, ip_mode, is_online, is_approved, x, y, now, now))
    return cursor.lastrowid


def _add_link(db, network_id, dev_a, dev_b, link_type='wired', status='active', cost=1, delay_ms=2):
    now = _now()
    cursor = db.execute("""
        INSERT INTO connections (network_id, device_a_id, device_b_id, link_type, status, cost, delay_ms, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (network_id, dev_a, dev_b, link_type, status, cost, delay_ms, now))
    return cursor.lastrowid


def _build_star(db, network_id, prefix, options):
    """
    Star Topology: Central switch with radial workstations and default gateway.
    Total nodes: count (clamped 3 to 8).
    """
    count = int(options.get('device_count', 5))
    count = max(3, min(count, 8))

    # Center Switch at (450, 230)
    sw_id = _add_device(db, network_id, "Central Switch", "switch", None, 450, 230)

    # Top: Default Gateway Router
    r_id = _add_device(db, network_id, "Gateway Router", "router", f"{prefix}.1", 450, 65)
    _add_link(db, network_id, sw_id, r_id, cost=1)

    # Radial workstations (count - 2 workstations)
    host_count = count - 2
    host_types = ['desktop', 'laptop', 'server', 'printer', 'smartphone', 'desktop']
    radius = 175
    center_x, center_y = 450, 230

    for i in range(host_count):
        if host_count == 1:
            x, y = 450, 395
        elif host_count == 2:
            x = 300 if i == 0 else 600
            y = 350
        else:
            angle = (2 * math.pi / (host_count + 1)) * (i + 1) + (math.pi / 2)
            x = int(center_x + radius * math.cos(angle))
            y = int(center_y + radius * math.sin(angle))
            x = max(90, min(x, 810))
            y = max(110, min(y, 440))

        dtype = host_types[i % len(host_types)]
        ip = f"{prefix}.{10 + i + 1}"
        d_id = _add_device(db, network_id, f"Star Host {i+1}", dtype, ip, x, y)
        _add_link(db, network_id, sw_id, d_id, cost=1)

    db.commit()
    return {
        'topology': 'star',
        'title': 'Star Topology Generated',
        'description': f'Generated star topology with {count} total nodes (1 central switch, 1 gateway router, and {host_count} workstations).'
    }


def _build_bus(db, network_id, prefix, options):
    """
    Bus Topology: Simple, clean linear shared backbone cable connecting stations sequentially.
    Total nodes: count (clamped 3 to 8).
    """
    count = int(options.get('device_count', 4))
    count = max(3, min(count, 8))

    y = 230
    start_x = 120
    available_w = 660
    spacing = int(available_w / max(1, count - 1))

    host_configs = [
        ("Bus Station 1", "router", f"{prefix}.1"),
        ("Bus Station 2", "desktop", f"{prefix}.11"),
        ("Bus Station 3", "server", f"{prefix}.12"),
        ("Bus Station 4", "laptop", f"{prefix}.13"),
        ("Bus Station 5", "desktop", f"{prefix}.14"),
        ("Bus Station 6", "printer", f"{prefix}.15"),
        ("Bus Station 7", "laptop", f"{prefix}.16"),
        ("Bus Station 8", "server", f"{prefix}.17"),
    ]

    station_ids = []
    for i in range(count):
        x = start_x + (i * spacing)
        name, dtype, ip = host_configs[i % len(host_configs)]
        if i >= len(host_configs):
            name = f"Bus Station {i+1}"
            ip = f"{prefix}.{10 + i}"
        sid = _add_device(db, network_id, name, dtype, ip, x, y)
        station_ids.append(sid)

    # Connect nodes linearly along the shared backbone cable
    for i in range(len(station_ids) - 1):
        _add_link(db, network_id, station_ids[i], station_ids[i+1], link_type='backbone', cost=1, delay_ms=2)

    db.commit()
    return {
        'topology': 'bus',
        'title': 'Bus Topology Generated',
        'description': f'Generated clean linear bus topology with {count} stations directly interconnected along a single shared backbone cable.'
    }


def _build_ring(db, network_id, prefix, options):
    """
    Ring Topology: Closed circular loop where each device is connected to two neighbors.
    Total nodes: count (clamped 3 to 8).
    """
    count = int(options.get('device_count', 5))
    count = max(3, min(count, 8))

    center_x, center_y = 450, 240
    radius = 175
    node_ids = []

    dev_types = ['router', 'laptop', 'desktop', 'server', 'router', 'laptop', 'desktop', 'server']

    for i in range(count):
        angle = (2 * math.pi / count) * i - (math.pi / 2)
        x = int(center_x + radius * math.cos(angle))
        y = int(center_y + radius * math.sin(angle))
        x = max(80, min(x, 820))
        y = max(80, min(y, 440))

        ip = f"{prefix}.{30 + i + 1}"
        dtype = dev_types[i % len(dev_types)]
        d_id = _add_device(db, network_id, f"Ring Node {i+1}", dtype, ip, x, y)
        node_ids.append(d_id)

    # Connect nodes in a ring loop
    for i in range(count):
        next_i = (i + 1) % count
        _add_link(db, network_id, node_ids[i], node_ids[next_i], cost=2, delay_ms=3)

    db.commit()
    return {
        'topology': 'ring',
        'title': 'Ring Topology Generated',
        'description': f'Generated circular ring topology with {count} nodes. If one link fails, traffic reroutes in the reverse direction around the ring.'
    }


def _build_mesh(db, network_id, prefix, options):
    """
    Mesh Topology: Fully connected mesh with varied link metrics.
    Total nodes: count (clamped 3 to 8).
    """
    count = int(options.get('device_count', 4))
    count = max(3, min(count, 8))

    center_x, center_y = 450, 240
    radius = 175 if count <= 5 else 195
    node_ids = []

    configs = [
        ("Router Alpha", "router"),
        ("Router Beta", "router"),
        ("Router Gamma", "router"),
        ("Router Delta", "router"),
        ("Core Server", "server"),
        ("Node Epsilon", "desktop"),
        ("Router Zeta", "router"),
        ("Backup Server", "server"),
    ]

    for i in range(count):
        angle = (2 * math.pi / count) * i - (math.pi / 2)
        x = int(center_x + radius * math.cos(angle))
        y = int(center_y + radius * math.sin(angle))
        x = max(80, min(x, 820))
        y = max(80, min(y, 440))

        name, dtype = configs[i % len(configs)]
        ip = f"{prefix}.{40 + i + 1}"
        d_id = _add_device(db, network_id, name, dtype, ip, x, y)
        node_ids.append(d_id)

    # Connect all pairs of nodes (Full Mesh)
    link_count = 0
    for i in range(count):
        for j in range(i + 1, count):
            cost = ((i * 2 + j * 3) % 5) + 1
            _add_link(db, network_id, node_ids[i], node_ids[j], cost=cost, delay_ms=cost * 2)
            link_count += 1

    db.commit()
    return {
        'topology': 'mesh',
        'title': 'Mesh Topology Generated',
        'description': f'Generated fully connected mesh topology with {count} nodes and {link_count} links. Rich multi-path redundancy for Dijkstra and Distance Vector routing.'
    }


def _build_tree(db, network_id, prefix, options):
    """
    Tree Topology: Hierarchical Core Router -> Distribution Switches -> Workstation Leaves.
    Total nodes: count (clamped 3 to 8).
    """
    count = int(options.get('device_count', 5))
    count = max(3, min(count, 8))

    # Level 0: Root Core Router
    root_id = _add_device(db, network_id, "Core Root Router", "router", f"{prefix}.1", 450, 65)

    if count == 3:
        # Root Router + 2 Leaves
        h1 = _add_device(db, network_id, "Branch Workstation 1", "desktop", f"{prefix}.10", 280, 240)
        h2 = _add_device(db, network_id, "Branch Server 2", "server", f"{prefix}.11", 620, 240)
        _add_link(db, network_id, root_id, h1, cost=1)
        _add_link(db, network_id, root_id, h2, cost=1)

    elif count == 4:
        # Root Router + 1 Switch + 2 Leaves
        sw_id = _add_device(db, network_id, "Distribution Switch", "switch", None, 450, 190)
        _add_link(db, network_id, root_id, sw_id, cost=2)
        h1 = _add_device(db, network_id, "Branch PC 1", "desktop", f"{prefix}.10", 300, 330)
        h2 = _add_device(db, network_id, "Branch PC 2", "laptop", f"{prefix}.11", 600, 330)
        _add_link(db, network_id, sw_id, h1, cost=1)
        _add_link(db, network_id, sw_id, h2, cost=1)

    else:
        # count >= 5: Root Router + 2 Distribution Switches + (count - 3) Leaves
        sw_left = _add_device(db, network_id, "Dist Switch West", "switch", None, 280, 180)
        sw_right = _add_device(db, network_id, "Dist Switch East", "switch", None, 620, 180)
        _add_link(db, network_id, root_id, sw_left, cost=2, delay_ms=2)
        _add_link(db, network_id, root_id, sw_right, cost=2, delay_ms=2)

        leaf_count = count - 3
        left_leaves = (leaf_count + 1) // 2
        right_leaves = leaf_count - left_leaves

        types = ['desktop', 'laptop', 'server', 'printer', 'smartphone']
        # West branch leaves
        for i in range(left_leaves):
            x = 150 + i * int(260 / max(1, left_leaves - 1)) if left_leaves > 1 else 280
            dtype = types[i % len(types)]
            lid = _add_device(db, network_id, f"West Host {i+1}", dtype, f"{prefix}.{10 + i + 1}", x, 330)
            _add_link(db, network_id, sw_left, lid, cost=1)

        # East branch leaves
        for j in range(right_leaves):
            x = 490 + j * int(260 / max(1, right_leaves - 1)) if right_leaves > 1 else 620
            dtype = types[(j + 2) % len(types)]
            lid = _add_device(db, network_id, f"East Host {j+1}", dtype, f"{prefix}.{20 + j + 1}", x, 330)
            _add_link(db, network_id, sw_right, lid, cost=1)

    db.commit()
    return {
        'topology': 'tree',
        'title': 'Tree Topology Generated',
        'description': f'Generated hierarchical tree topology with {count} total nodes. Core router connects to distribution switches which branch into endpoint hosts.'
    }


def _build_hybrid(db, network_id, prefix, options):
    """
    Hybrid Topology: Two departmental clusters bridged via an inter-router backbone link.
    Total nodes: count (clamped 3 to 8).
    """
    count = int(options.get('device_count', 6))
    count = max(3, min(count, 8))

    # Cluster A Router & Cluster B Router connected directly
    r_a = _add_device(db, network_id, "Router West", "router", f"{prefix}.1", 280, 90)
    r_b = _add_device(db, network_id, "Router East", "router", f"{prefix}.2", 620, 90)
    _add_link(db, network_id, r_a, r_b, link_type='backbone', cost=3, delay_ms=5)

    remaining = count - 2
    types = ['desktop', 'laptop', 'server', 'printer', 'smartphone']

    if remaining == 1:
        h = _add_device(db, network_id, "West Workstation", "desktop", f"{prefix}.11", 280, 250)
        _add_link(db, network_id, r_a, h, cost=1)
    elif remaining == 2:
        h1 = _add_device(db, network_id, "West Workstation", "desktop", f"{prefix}.11", 280, 250)
        h2 = _add_device(db, network_id, "East Workstation", "laptop", f"{prefix}.21", 620, 250)
        _add_link(db, network_id, r_a, h1, cost=1)
        _add_link(db, network_id, r_b, h2, cost=1)
    else:
        sw_a = _add_device(db, network_id, "Switch West", "switch", None, 280, 200)
        sw_b = _add_device(db, network_id, "Switch East", "switch", None, 620, 200)
        _add_link(db, network_id, r_a, sw_a, cost=1)
        _add_link(db, network_id, r_b, sw_b, cost=1)

        leaf_count = remaining - 2
        left_leaves = (leaf_count + 1) // 2
        right_leaves = leaf_count - left_leaves

        for i in range(left_leaves):
            x = 160 + i * int(240 / max(1, left_leaves - 1)) if left_leaves > 1 else 280
            dtype = types[i % len(types)]
            lid = _add_device(db, network_id, f"West Station {i+1}", dtype, f"{prefix}.{10 + i + 1}", x, 330)
            _add_link(db, network_id, sw_a, lid, cost=1)

        for j in range(right_leaves):
            x = 500 + j * int(240 / max(1, right_leaves - 1)) if right_leaves > 1 else 620
            dtype = types[(j + 2) % len(types)]
            lid = _add_device(db, network_id, f"East Station {j+1}", dtype, f"{prefix}.{20 + j + 1}", x, 330)
            _add_link(db, network_id, sw_b, lid, cost=1)

    db.commit()
    return {
        'topology': 'hybrid',
        'title': 'Hybrid (Star-Router-Star) Topology Generated',
        'description': f'Generated hybrid topology with {count} nodes across two departmental clusters bridged via a high-speed router backbone.'
    }
