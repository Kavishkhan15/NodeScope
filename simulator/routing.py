"""
simulator/routing.py
Comprehensive routing algorithm simulation engine for NodeScope:
1. Shortest-Path Baseline (BFS for minimum hops, Dijkstra for weighted link metrics)
2. Distance Vector Routing (Bellman-Ford with router exchange rounds, split horizon, poison reverse, count-to-infinity)
3. Link State Routing (OSPF-style Link State Database [LSDB] and per-node Dijkstra SPF trees)
4. RIP (Routing Information Protocol with hop-count metric and 15-hop boundary / 16 = unreachable)
"""
import heapq
from collections import deque


def get_network_graph(db, network_id: int, include_all_devices: bool = False):
    """
    Build graph of devices and links for a given network.
    Returns (devices_dict, edges_list, adj_dict).
    Edges only include active links between online devices unless include_all_devices=True.
    """
    dev_rows = db.execute("SELECT * FROM devices WHERE network_id = ?", (network_id,)).fetchall()
    devices = {r['id']: dict(r) for r in dev_rows}

    conn_rows = db.execute("SELECT * FROM connections WHERE network_id = ?", (network_id,)).fetchall()

    adj = {dev_id: [] for dev_id in devices}
    edges = []

    for c in conn_rows:
        c_dict = dict(c)
        # Default cost and delay if missing
        c_dict['cost'] = c_dict.get('cost') or 1
        c_dict['delay_ms'] = c_dict.get('delay_ms') or 2

        da = c_dict['device_a_id']
        db_id = c_dict['device_b_id']

        if da in devices and db_id in devices:
            edges.append(c_dict)
            is_active = (c_dict['status'] == 'active')
            if include_all_devices or (is_active and devices[da]['is_online'] and devices[db_id]['is_online']):
                adj[da].append({'neighbor_id': db_id, 'link_id': c_dict['id'], 'cost': c_dict['cost'], 'delay_ms': c_dict['delay_ms'], 'link_type': c_dict['link_type'], 'status': c_dict['status']})
                adj[db_id].append({'neighbor_id': da, 'link_id': c_dict['id'], 'cost': c_dict['cost'], 'delay_ms': c_dict['delay_ms'], 'link_type': c_dict['link_type'], 'status': c_dict['status']})

    return devices, edges, adj


def calculate_shortest_path_bfs(devices, adj, src_id, dst_id):
    """
    Graph-based baseline: Breadth-First Search for minimum-hop path (unweighted).
    """
    if src_id not in devices or dst_id not in devices:
        return {'status': 'failed', 'message': 'Device not found in network.', 'path': [], 'links': [], 'hops': 0, 'total_cost': 0}
    if not devices[src_id]['is_online']:
        return {'status': 'failed', 'message': f"Source '{devices[src_id]['name']}' is powered OFF.", 'path': [], 'links': [], 'hops': 0, 'total_cost': 0}
    if not devices[dst_id]['is_online']:
        return {'status': 'failed', 'message': f"Destination '{devices[dst_id]['name']}' is powered OFF.", 'path': [], 'links': [], 'hops': 0, 'total_cost': 0}
    if src_id == dst_id:
        return {'status': 'success', 'message': 'Loopback communication (same host).', 'path': [devices[src_id]], 'links': [], 'hops': 0, 'total_cost': 0}

    queue = deque([([src_id], [])])
    visited = {src_id}

    while queue:
        path_nodes, path_links = queue.popleft()
        curr = path_nodes[-1]

        if curr == dst_id:
            path_devs = [devices[nid] for nid in path_nodes]
            hops = len(path_devs) - 1
            return {
                'status': 'success',
                'algorithm': 'bfs',
                'path': path_devs,
                'path_ids': path_nodes,
                'links': path_links,
                'hops': hops,
                'total_cost': hops,
                'message': f"BFS path found ({hops} hops): " + " → ".join(d['name'] for d in path_devs),
                'explanation': f"Shortest path baseline traversed unweighted graph using BFS to find the minimum number of hops ({hops} hops)."
            }

        for edge in adj.get(curr, []):
            nbr = edge['neighbor_id']
            if nbr not in visited:
                visited.add(nbr)
                queue.append((path_nodes + [nbr], path_links + [edge['link_id']]))

    return {
        'status': 'failed',
        'algorithm': 'bfs',
        'message': f"No active route exists between '{devices[src_id]['name']}' and '{devices[dst_id]['name']}'.",
        'path': [],
        'links': [],
        'hops': 0,
        'total_cost': 0,
        'explanation': "BFS queue exhausted without reaching destination. Check for disconnected links or offline intermediate forwarders."
    }


def calculate_dijkstra(devices, adj, src_id, dst_id):
    """
    Dijkstra's shortest path algorithm using link costs as metrics.
    """
    if src_id not in devices or dst_id not in devices:
        return {'status': 'failed', 'message': 'Device not found in network.', 'path': [], 'links': [], 'hops': 0, 'total_cost': 0}
    if not devices[src_id]['is_online']:
        return {'status': 'failed', 'message': f"Source '{devices[src_id]['name']}' is powered OFF.", 'path': [], 'links': [], 'hops': 0, 'total_cost': 0}
    if not devices[dst_id]['is_online']:
        return {'status': 'failed', 'message': f"Destination '{devices[dst_id]['name']}' is powered OFF.", 'path': [], 'links': [], 'hops': 0, 'total_cost': 0}
    if src_id == dst_id:
        return {'status': 'success', 'message': 'Loopback communication (same host).', 'path': [devices[src_id]], 'links': [], 'hops': 0, 'total_cost': 0}

    # Priority queue stores (cumulative_cost, current_node_id, path_nodes, path_links)
    pq = [(0, src_id, [src_id], [])]
    min_cost = {src_id: 0}

    while pq:
        cost, curr, path_nodes, path_links = heapq.heappop(pq)

        if curr == dst_id:
            path_devs = [devices[nid] for nid in path_nodes]
            hops = len(path_devs) - 1
            return {
                'status': 'success',
                'algorithm': 'dijkstra',
                'path': path_devs,
                'path_ids': path_nodes,
                'links': path_links,
                'hops': hops,
                'total_cost': cost,
                'message': f"Dijkstra lowest-cost path found (metric: {cost}, {hops} hops): " + " → ".join(d['name'] for d in path_devs),
                'explanation': f"Dijkstra's algorithm selected this path because its cumulative link cost metric ({cost}) is strictly minimal among all active topology paths."
            }

        if cost > min_cost.get(curr, float('inf')):
            continue

        for edge in adj.get(curr, []):
            nbr = edge['neighbor_id']
            edge_cost = edge['cost']
            new_cost = cost + edge_cost

            if new_cost < min_cost.get(nbr, float('inf')):
                min_cost[nbr] = new_cost
                heapq.heappush(pq, (new_cost, nbr, path_nodes + [nbr], path_links + [edge['link_id']]))

    return {
        'status': 'failed',
        'algorithm': 'dijkstra',
        'message': f"No active route found between '{devices[src_id]['name']}' and '{devices[dst_id]['name']}'.",
        'path': [],
        'links': [],
        'hops': 0,
        'total_cost': 0,
        'explanation': "Dijkstra SPF found no reachable path. Check whether intermediate switches/routers are active and unsevered."
    }


def simulate_distance_vector(devices, adj, options=None):
    """
    Distance Vector (Bellman-Ford) routing simulation.
    Routers exchange distance vectors with neighbors in synchronized rounds until convergence.
    Supports options:
      - split_horizon: bool (default True)
      - poison_reverse: bool (default False)
      - max_rounds: int (default 15)
      - count_to_infinity: bool (default False)
    Returns:
      - routing_tables: dict[router_id -> list of table entries]
      - convergence_rounds: list of round snapshots
      - converged: bool
    """
    options = options or {}
    split_horizon = options.get('split_horizon', True)
    poison_reverse = options.get('poison_reverse', False)
    max_rounds = options.get('max_rounds', 16)
    count_to_infinity = options.get('count_to_infinity', False)
    max_metric = 16 if (options.get('is_rip') or count_to_infinity) else 999

    # Nodes that run routing (routers primarily, but we compute for all online devices so hosts know next hops)
    nodes = [nid for nid, d in devices.items() if d['is_online']]

    # Initialize Distance Tables: dv[u][dest] = {'cost': int, 'next_hop': int or None, 'link_id': int or None}
    dv = {}
    for u in nodes:
        dv[u] = {}
        for v in nodes:
            if u == v:
                dv[u][v] = {'cost': 0, 'next_hop': u, 'link_id': None}
            else:
                dv[u][v] = {'cost': max_metric, 'next_hop': None, 'link_id': None}

        # Initialize directly connected neighbors
        for edge in adj.get(u, []):
            nbr = edge['neighbor_id']
            if nbr in nodes:
                c = edge['cost']
                if c < dv[u][nbr]['cost']:
                    dv[u][nbr] = {'cost': c, 'next_hop': nbr, 'link_id': edge['link_id']}

    convergence_rounds = []
    converged = False

    # Snapshot Round 0 (Initial local discovery)
    convergence_rounds.append({
        'round': 0,
        'description': 'Initial direct neighbor discovery',
        'tables': _format_dv_tables(dv, devices, max_metric)
    })

    # Iterative Distance Vector exchange
    for r in range(1, max_rounds):
        changed = False
        new_dv = {u: {v: dict(dv[u][v]) for v in nodes} for u in nodes}

        for u in nodes:
            for edge in adj.get(u, []):
                nbr = edge['neighbor_id']
                if nbr not in nodes:
                    continue
                link_cost = edge['cost']
                link_id = edge['link_id']

                # Receive vector from nbr
                for dest in nodes:
                    nbr_cost = dv[nbr][dest]['cost']
                    nbr_next_hop = dv[nbr][dest]['next_hop']

                    # Split horizon: do not accept a route if neighbor routes through us
                    if split_horizon and not count_to_infinity:
                        if nbr_next_hop == u:
                            if poison_reverse:
                                nbr_cost = max_metric
                            else:
                                continue

                    offered_cost = link_cost + nbr_cost
                    if offered_cost > max_metric:
                        offered_cost = max_metric

                    # Bellman-Ford update check
                    current_cost = new_dv[u][dest]['cost']
                    if offered_cost < current_cost:
                        new_dv[u][dest] = {'cost': offered_cost, 'next_hop': nbr, 'link_id': link_id}
                        changed = True
                    elif new_dv[u][dest]['next_hop'] == nbr and offered_cost != current_cost:
                        # Cost through current next_hop changed
                        new_dv[u][dest] = {'cost': offered_cost, 'next_hop': nbr if offered_cost < max_metric else None, 'link_id': link_id if offered_cost < max_metric else None}
                        changed = True

        dv = new_dv
        convergence_rounds.append({
            'round': r,
            'description': f"Round {r} vector exchange {'(Changes detected)' if changed else '(Converged)'}",
            'tables': _format_dv_tables(dv, devices, max_metric)
        })

        if not changed:
            converged = True
            break

    # Build final formatted routing tables
    final_tables = _format_dv_tables(dv, devices, max_metric)
    return {
        'routing_tables': final_tables,
        'convergence_rounds': convergence_rounds,
        'converged': converged,
        'max_metric': max_metric
    }


def _format_dv_tables(dv, devices, max_metric):
    formatted = {}
    for u, destinations in dv.items():
        u_name = devices[u]['name']
        formatted[u] = {
            'device_id': u,
            'device_name': u_name,
            'device_type': devices[u]['device_type'],
            'routes': []
        }
        for dest_id, route in destinations.items():
            if dest_id == u:
                continue
            is_unreachable = (route['cost'] >= max_metric or route['next_hop'] is None)
            formatted[u]['routes'].append({
                'destination_id': dest_id,
                'destination_name': devices[dest_id]['name'],
                'destination_ip': devices[dest_id]['ip_address'] or 'N/A',
                'cost': '∞ (Unreachable)' if is_unreachable else route['cost'],
                'cost_val': route['cost'],
                'next_hop_id': None if is_unreachable else route['next_hop'],
                'next_hop_name': 'None' if is_unreachable else devices[route['next_hop']]['name'],
                'link_id': route['link_id'],
                'status': 'Unreachable' if is_unreachable else 'Active'
            })
    return formatted


def simulate_link_state(devices, adj):
    """
    Link State Routing simulation (OSPF-style):
    1. Each node builds its Link State Advertisement (LSA) of local incident links.
    2. Flooding produces a synchronized Link State Database (LSDB) identical across all nodes.
    3. Each node executes Dijkstra's SPF locally to compute its own shortest path tree and next hops.
    """
    nodes = [nid for nid, d in devices.items() if d['is_online']]

    # 1. Build LSDB (Global graph of all link state advertisements)
    lsdb = []
    for u in nodes:
        lsa_links = []
        for edge in adj.get(u, []):
            nbr = edge['neighbor_id']
            if nbr in nodes:
                lsa_links.append({
                    'neighbor_id': nbr,
                    'neighbor_name': devices[nbr]['name'],
                    'cost': edge['cost'],
                    'link_id': edge['link_id'],
                    'link_type': edge['link_type']
                })
        lsdb.append({
            'router_id': u,
            'router_name': devices[u]['name'],
            'router_type': devices[u]['device_type'],
            'links': lsa_links,
            'seq_num': 1
        })

    # 2. Each node computes its SPF tree using local Dijkstra
    routing_tables = {}
    for u in nodes:
        routing_tables[u] = {
            'device_id': u,
            'device_name': devices[u]['name'],
            'device_type': devices[u]['device_type'],
            'routes': []
        }
        for dest in nodes:
            if dest == u:
                continue
            res = calculate_dijkstra(devices, adj, u, dest)
            if res['status'] == 'success' and len(res['path_ids']) >= 2:
                next_hop_id = res['path_ids'][1]
                routing_tables[u]['routes'].append({
                    'destination_id': dest,
                    'destination_name': devices[dest]['name'],
                    'destination_ip': devices[dest]['ip_address'] or 'N/A',
                    'cost': res['total_cost'],
                    'cost_val': res['total_cost'],
                    'hops': res['hops'],
                    'next_hop_id': next_hop_id,
                    'next_hop_name': devices[next_hop_id]['name'],
                    'link_id': res['links'][0] if res['links'] else None,
                    'status': 'Active'
                })
            else:
                routing_tables[u]['routes'].append({
                    'destination_id': dest,
                    'destination_name': devices[dest]['name'],
                    'destination_ip': devices[dest]['ip_address'] or 'N/A',
                    'cost': '∞ (Unreachable)',
                    'cost_val': 999,
                    'hops': 0,
                    'next_hop_id': None,
                    'next_hop_name': 'None',
                    'link_id': None,
                    'status': 'Unreachable'
                })

    return {
        'lsdb': lsdb,
        'routing_tables': routing_tables,
        'explanation': "In Link State routing, every router maintains an identical Link State Database (LSDB) via flooded LSAs, then computes an independent shortest-path tree using Dijkstra's algorithm."
    }


def calculate_route_dispatch(db, network_id: int, src_id: int, dst_id: int, algorithm: str = 'dijkstra', options: dict = None):
    """
    Master route calculation dispatcher for NodeScope.
    Dispatches to requested algorithm: 'bfs', 'dijkstra', 'distance_vector', 'link_state', or 'rip'.
    Returns comprehensive route result dict including hop-by-hop nodes, links, costs, and explanation.
    """
    options = options or {}
    devices, edges, adj = get_network_graph(db, network_id)

    algo = algorithm.lower().strip()

    if algo in ('bfs', 'shortest_path'):
        return calculate_shortest_path_bfs(devices, adj, src_id, dst_id)

    elif algo == 'dijkstra':
        return calculate_dijkstra(devices, adj, src_id, dst_id)

    elif algo == 'distance_vector':
        dv_res = simulate_distance_vector(devices, adj, options=options)
        # Trace path hop-by-hop using computed distance-vector tables
        path_ids = [src_id]
        path_links = []
        total_cost = 0
        curr = src_id
        visited = {src_id}
        unreachable = False

        while curr != dst_id:
            table = dv_res['routing_tables'].get(curr)
            if not table:
                unreachable = True
                break
            route_entry = next((r for r in table['routes'] if r['destination_id'] == dst_id), None)
            if not route_entry or route_entry['status'] == 'Unreachable' or not route_entry['next_hop_id']:
                unreachable = True
                break
            nxt = route_entry['next_hop_id']
            if nxt in visited:
                # Routing loop detected
                unreachable = True
                break
            visited.add(nxt)
            path_ids.append(nxt)
            path_links.append(route_entry['link_id'])
            curr = nxt

        if unreachable or path_ids[-1] != dst_id:
            return {
                'status': 'failed',
                'algorithm': 'distance_vector',
                'message': f"Distance Vector could not establish a valid route from '{devices[src_id]['name']}' to '{devices[dst_id]['name']}'.",
                'path': [],
                'links': [],
                'hops': 0,
                'total_cost': 0,
                'routing_tables': dv_res['routing_tables'],
                'convergence_rounds': dv_res['convergence_rounds'],
                'explanation': "Destination is either partitioned or metric has exceeded maximum infinity boundary."
            }

        path_devs = [devices[nid] for nid in path_ids]
        hops = len(path_devs) - 1
        # Sum costs along path
        for i in range(len(path_ids) - 1):
            u, v = path_ids[i], path_ids[i+1]
            edge = next((e for e in adj.get(u, []) if e['neighbor_id'] == v), None)
            if edge:
                total_cost += edge['cost']

        return {
            'status': 'success',
            'algorithm': 'distance_vector',
            'path': path_devs,
            'path_ids': path_ids,
            'links': path_links,
            'hops': hops,
            'total_cost': total_cost,
            'routing_tables': dv_res['routing_tables'],
            'convergence_rounds': dv_res['convergence_rounds'],
            'message': f"Distance Vector route converged ({hops} hops, metric: {total_cost}): " + " → ".join(d['name'] for d in path_devs),
            'explanation': f"Bellman-Ford vector exchanges converged in {len(dv_res['convergence_rounds'])-1} rounds. Next hops were chosen based on minimum reported neighbor distance."
        }

    elif algo == 'link_state':
        ls_res = simulate_link_state(devices, adj)
        # Use Dijkstra on the LSDB graph
        dijk_res = calculate_dijkstra(devices, adj, src_id, dst_id)
        dijk_res['algorithm'] = 'link_state'
        dijk_res['lsdb'] = ls_res['lsdb']
        dijk_res['routing_tables'] = ls_res['routing_tables']
        dijk_res['explanation'] = f"Link State calculated route using local Dijkstra SPF over synchronized LSDB ({dijk_res['hops']} hops, total metric: {dijk_res['total_cost']})."
        return dijk_res

    elif algo == 'rip':
        # RIP is Distance Vector with hop count metric (1 per hop) and 15-hop limit (16 = infinity)
        rip_adj = {}
        for u, edges_list in adj.items():
            rip_adj[u] = []
            for e in edges_list:
                copy_e = dict(e)
                copy_e['cost'] = 1  # RIP strictly uses hop count
                rip_adj[u].append(copy_e)

        dv_res = simulate_distance_vector(devices, rip_adj, options={'is_rip': True, 'max_metric': 16})
        # Check Dijkstra hop count
        bfs_res = calculate_shortest_path_bfs(devices, rip_adj, src_id, dst_id)
        if bfs_res['status'] != 'success' or bfs_res['hops'] > 15:
            return {
                'status': 'failed',
                'algorithm': 'rip',
                'message': f"RIP route failed: Hop count {bfs_res.get('hops', 16)} exceeds maximum RIP limit of 15 (Metric 16 = Unreachable).",
                'path': [],
                'links': [],
                'hops': bfs_res.get('hops', 16),
                'total_cost': 16,
                'routing_tables': dv_res['routing_tables'],
                'explanation': "RIP enforces a maximum hop count of 15 to prevent routing loops. Metric 16 represents an unreachable network."
            }
        bfs_res['algorithm'] = 'rip'
        bfs_res['routing_tables'] = dv_res['routing_tables']
        bfs_res['message'] = f"RIP route active ({bfs_res['hops']} hops, valid metric <= 15): " + " → ".join(d['name'] for d in bfs_res['path'])
        bfs_res['explanation'] = f"RIP hop-count vector converged with {bfs_res['hops']} hops (within permissible 1-15 hop boundary)."
        return bfs_res

    else:
        # Default fallback
        return calculate_dijkstra(devices, adj, src_id, dst_id)
