"""
simulator/connectivity.py
Graph topology traversal and physical/data-link path discovery.
Evaluates whether an active communication path exists between two devices in the virtual LAN.
"""
from collections import deque


def get_adjacency_list(db, network_id: int) -> tuple[dict[int, list[int]], dict[int, dict]]:
    """
    Build graph of devices and their connections in the network.
    Returns (adj_list, devices_dict).
    """
    dev_rows = db.execute("SELECT * FROM devices WHERE network_id = ?", (network_id,)).fetchall()
    devices = {r['id']: dict(r) for r in dev_rows}

    conn_rows = db.execute("""
        SELECT * FROM connections 
        WHERE network_id = ? AND status = 'active'
    """, (network_id,)).fetchall()

    adj: dict[int, list[int]] = {dev_id: [] for dev_id in devices}
    for c in conn_rows:
        da = c['device_a_id']
        db_id = c['device_b_id']
        if da in adj and db_id in adj:
            adj[da].append(db_id)
            adj[db_id].append(da)

    return adj, devices


def find_path(db, network_id: int, src_id: int, dst_id: int) -> tuple[bool, list[dict], str]:
    """
    Find an active path from src_id to dst_id using BFS.
    Only traverses active connections and devices that are powered online (is_online=1).
    Returns (path_exists, path_device_dicts, diagnostic_message).
    """
    adj, devices = get_adjacency_list(db, network_id)

    if src_id not in devices:
        return False, [], "Source device does not exist."
    if dst_id not in devices:
        return False, [], "Destination device does not exist."

    src = devices[src_id]
    dst = devices[dst_id]

    if not src['is_online']:
        return False, [], f"Source device '{src['name']}' is powered OFF."
    if not dst['is_online']:
        return False, [], f"Destination device '{dst['name']}' is powered OFF."

    if src_id == dst_id:
        return True, [src], "Loopback communication (same host)."

    if not adj[src_id]:
        return False, [], f"Source device '{src['name']}' is not connected to any network link."
    if not adj[dst_id]:
        return False, [], f"Destination device '{dst['name']}' is not connected to any network link."

    # BFS traversal
    queue = deque([[src_id]])
    visited = {src_id}

    while queue:
        current_path = queue.popleft()
        node_id = current_path[-1]

        if node_id == dst_id:
            # Found path!
            path_devices = [devices[nid] for nid in current_path]
            names = " → ".join(d['name'] for d in path_devices)
            return True, path_devices, f"Path active: {names}"

        for neighbor_id in adj[node_id]:
            neighbor = devices[neighbor_id]
            # Device must be online to forward frames or be destination
            if not neighbor['is_online']:
                continue
            if neighbor_id not in visited:
                visited.add(neighbor_id)
                new_path = list(current_path)
                new_path.append(neighbor_id)
                queue.append(new_path)

    return False, [], f"No active physical or wireless link connects '{src['name']}' to '{dst['name']}'."
