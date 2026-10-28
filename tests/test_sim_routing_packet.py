"""
tests/test_sim_routing_packet.py
Comprehensive unit and integration tests for:
1. Topology generation (Star, Bus, Ring, Mesh, Tree, Hybrid)
2. Routing algorithms (BFS, Dijkstra, Distance Vector, Link State, RIP)
3. End-to-end packet transmission (DATA, PING, drops, dynamic rerouting)
4. Network failure and recovery (severed links, offline routers, link metric tuning)
"""
import pytest
from database.db import get_db
from simulator.topology_builder import generate_topology
from simulator.routing import (
    calculate_route_dispatch, get_network_graph,
    simulate_distance_vector, simulate_link_state
)
from simulator.packet import transmit_packet


@pytest.fixture
def test_network_id(app_ctx):
    db = get_db()
    cursor = db.execute("""
        INSERT INTO networks (name, subnet, netmask, gateway, dhcp_enabled, created_at, updated_at)
        VALUES ('Test Routing Lab', '192.168.10.0/24', '255.255.255.0', '192.168.10.1', 1, '2026-01-01', '2026-01-01')
    """)
    db.commit()
    return cursor.lastrowid


def test_topology_generators(app_ctx, test_network_id):
    db = get_db()
    topologies = ['star', 'bus', 'ring', 'mesh', 'tree', 'hybrid']

    for t_type in topologies:
        res = generate_topology(db, test_network_id, t_type)
        assert res['topology'] == t_type
        # Verify devices and connections were generated in database
        devs = db.execute("SELECT * FROM devices WHERE network_id = ?", (test_network_id,)).fetchall()
        conns = db.execute("SELECT * FROM connections WHERE network_id = ?", (test_network_id,)).fetchall()
        assert len(devs) >= 4, f"Topology {t_type} should have >= 4 devices"
        assert len(conns) >= 3, f"Topology {t_type} should have >= 3 connections"


def test_topology_node_count_scaling(app_ctx, test_network_id):
    """
    Verify that node count user parameter (3 to 8) dynamically scales
    the generated device count across all topology types.
    """
    db = get_db()
    for t_type in ['bus', 'mesh', 'tree', 'star', 'ring', 'hybrid']:
        for count in [3, 4, 6, 8]:
            generate_topology(db, test_network_id, t_type, options={'device_count': count})
            devs = db.execute("SELECT * FROM devices WHERE network_id = ?", (test_network_id,)).fetchall()
            assert len(devs) == count, f"Expected {count} nodes for {t_type}, got {len(devs)}"


def test_dijkstra_link_cost_selection(app_ctx, test_network_id):
    """
    Test that Dijkstra selects the path with lowest total cost metric
    even if another path has fewer hops.
    Path 1: A -> B -> C (2 hops, costs: 10 + 10 = 20)
    Path 2: A -> D -> E -> C (3 hops, costs: 2 + 2 + 2 = 6)
    Dijkstra MUST choose Path 2!
    BFS MUST choose Path 1!
    """
    db = get_db()
    # Create nodes
    a = db.execute("INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, is_online, created_at, updated_at) VALUES (?, 'Node A', 'router', '02:00:00:00:00:0A', '192.168.10.10', 1, '2026-01-01', '2026-01-01')", (test_network_id,)).lastrowid
    b = db.execute("INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, is_online, created_at, updated_at) VALUES (?, 'Node B', 'router', '02:00:00:00:00:0B', '192.168.10.11', 1, '2026-01-01', '2026-01-01')", (test_network_id,)).lastrowid
    c = db.execute("INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, is_online, created_at, updated_at) VALUES (?, 'Node C', 'router', '02:00:00:00:00:0C', '192.168.10.12', 1, '2026-01-01', '2026-01-01')", (test_network_id,)).lastrowid
    d = db.execute("INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, is_online, created_at, updated_at) VALUES (?, 'Node D', 'router', '02:00:00:00:00:0D', '192.168.10.13', 1, '2026-01-01', '2026-01-01')", (test_network_id,)).lastrowid
    e = db.execute("INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, is_online, created_at, updated_at) VALUES (?, 'Node E', 'router', '02:00:00:00:00:0E', '192.168.10.14', 1, '2026-01-01', '2026-01-01')", (test_network_id,)).lastrowid

    # Path 1 links (High cost, few hops)
    db.execute("INSERT INTO connections (network_id, device_a_id, device_b_id, status, cost, created_at) VALUES (?, ?, ?, 'active', 10, '2026-01-01')", (test_network_id, a, b))
    db.execute("INSERT INTO connections (network_id, device_a_id, device_b_id, status, cost, created_at) VALUES (?, ?, ?, 'active', 10, '2026-01-01')", (test_network_id, b, c))

    # Path 2 links (Low cost, more hops)
    db.execute("INSERT INTO connections (network_id, device_a_id, device_b_id, status, cost, created_at) VALUES (?, ?, ?, 'active', 2, '2026-01-01')", (test_network_id, a, d))
    db.execute("INSERT INTO connections (network_id, device_a_id, device_b_id, status, cost, created_at) VALUES (?, ?, ?, 'active', 2, '2026-01-01')", (test_network_id, d, e))
    db.execute("INSERT INTO connections (network_id, device_a_id, device_b_id, status, cost, created_at) VALUES (?, ?, ?, 'active', 2, '2026-01-01')", (test_network_id, e, c))
    db.commit()

    # 1. Dijkstra check
    dijkstra_res = calculate_route_dispatch(db, test_network_id, a, c, algorithm='dijkstra')
    assert dijkstra_res['status'] == 'success'
    assert dijkstra_res['total_cost'] == 6
    assert [d['id'] for d in dijkstra_res['path']] == [a, d, e, c]

    # 2. BFS check (Should pick minimum hops = Path 1)
    bfs_res = calculate_route_dispatch(db, test_network_id, a, c, algorithm='bfs')
    assert bfs_res['status'] == 'success'
    assert bfs_res['hops'] == 2
    assert [d['id'] for d in bfs_res['path']] == [a, b, c]


def test_distance_vector_convergence(app_ctx, test_network_id):
    """
    Test Distance Vector (Bellman-Ford) routing convergence and table calculation.
    """
    db = get_db()
    # Generate mesh topology
    generate_topology(db, test_network_id, 'mesh')
    devices, edges, adj = get_network_graph(db, test_network_id)

    dv_res = simulate_distance_vector(devices, adj)
    assert dv_res['converged'] is True
    assert len(dv_res['convergence_rounds']) >= 2

    # Check routing tables for each node
    for nid, table in dv_res['routing_tables'].items():
        assert len(table['routes']) == len(devices) - 1
        for r in table['routes']:
            assert r['status'] == 'Active'
            assert r['next_hop_id'] is not None


def test_link_state_lsdb(app_ctx, test_network_id):
    """
    Test Link State routing (OSPF-style) LSDB creation and local SPF trees.
    """
    db = get_db()
    generate_topology(db, test_network_id, 'mesh')
    devices, edges, adj = get_network_graph(db, test_network_id)

    ls_res = simulate_link_state(devices, adj)
    assert len(ls_res['lsdb']) == len(devices)
    # Each node should have computed routing table
    assert len(ls_res['routing_tables']) == len(devices)


def test_rip_15_hop_limit(app_ctx, test_network_id):
    """
    Test RIP 15-hop limit enforcement (hop 16 = unreachable).
    """
    db = get_db()
    # Create chain of 18 routers
    prev = None
    first = None
    last = None

    for i in range(18):
        rid = db.execute("INSERT INTO devices (network_id, name, device_type, mac_address, ip_address, is_online, created_at, updated_at) VALUES (?, ?, 'router', ?, ?, 1, '2026-01-01', '2026-01-01')",
                         (test_network_id, f"R{i+1}", f"02:00:00:00:00:{i:02X}", f"192.168.10.{i+1}")).lastrowid
        if i == 0:
            first = rid
        if i == 17:
            last = rid
        if prev:
            db.execute("INSERT INTO connections (network_id, device_a_id, device_b_id, status, cost, created_at) VALUES (?, ?, ?, 'active', 1, '2026-01-01')", (test_network_id, prev, rid))
        prev = rid
    db.commit()

    # Route from R1 to R18 is 17 hops -> RIP MUST reject as unreachable (metric > 15)
    res = calculate_route_dispatch(db, test_network_id, first, last, algorithm='rip')
    assert res['status'] == 'failed'
    assert "exceeds maximum RIP limit of 15" in res['message']


def test_packet_transmission_and_rerouting(app_ctx, test_network_id):
    """
    Test end-to-end packet transmission and dynamic rerouting upon link failure in a Ring topology.
    """
    db = get_db()
    generate_topology(db, test_network_id, 'ring', options={'device_count': 5})
    devs = db.execute("SELECT * FROM devices WHERE network_id = ?", (test_network_id,)).fetchall()
    src = devs[0]
    dst = devs[2]

    # 1. Normal transmission (healthy ring)
    res1 = transmit_packet(db, test_network_id, src['id'], dst['id'], packet_type='DATA', algorithm='dijkstra')
    assert res1['status'] == 'delivered'
    assert len(res1['hops']) >= 1
    assert res1['forward_path'][0] == src['name']
    assert res1['forward_path'][-1] == dst['name']

    # 2. Break one of the links used in the primary path
    broken_link_id = res1['links_used'][0]
    db.execute("UPDATE connections SET status = 'down' WHERE id = ?", (broken_link_id,))
    db.commit()

    # 3. Transmit again -> Should find alternate route around the other side of the ring!
    res2 = transmit_packet(db, test_network_id, src['id'], dst['id'], packet_type='DATA', algorithm='dijkstra')
    assert res2['status'] == 'delivered'
    assert broken_link_id not in res2['links_used']


def test_packet_drop_when_isolated(app_ctx, test_network_id):
    """
    Test packet fails when all links or destination is isolated.
    """
    db = get_db()
    generate_topology(db, test_network_id, 'star', options={'device_count': 4})
    devs = db.execute("SELECT * FROM devices WHERE network_id = ?", (test_network_id,)).fetchall()
    star_host = [d for d in devs if 'Star Host 1' in d['name']][0]
    router = [d for d in devs if 'Gateway Router' in d['name']][0]

    # Disconnect star host completely
    db.execute("UPDATE connections SET status = 'down' WHERE device_a_id = ? OR device_b_id = ?", (star_host['id'], star_host['id']))
    db.commit()

    res = transmit_packet(db, test_network_id, star_host['id'], router['id'], packet_type='DATA')
    assert res['status'] == 'failed'
    assert "Destination unreachable" in res['failure_reason'] or "Routing failure" in res['message']


def test_icmp_ping_roundtrip(app_ctx, test_network_id):
    """
    Test two-way ICMP Echo Request and Echo Reply in packet simulator.
    """
    db = get_db()
    generate_topology(db, test_network_id, 'mesh')
    devs = db.execute("SELECT * FROM devices WHERE network_id = ?", (test_network_id,)).fetchall()
    src = devs[0]
    dst = devs[1]

    res = transmit_packet(db, test_network_id, src['id'], dst['id'], packet_type='PING', algorithm='dijkstra')
    assert res['status'] == 'delivered'
    assert res['packet_type'] == 'PING'
    assert len(res['forward_hops']) >= 1
    assert len(res['return_hops']) >= 1
    assert res['request_delivered'] is True
    assert res['reply_delivered'] is True
    assert res['rtt_ms'] > 0


def test_link_update_api(client, app_ctx, test_network_id):
    """
    Test PUT /api/connections/:id API endpoint to toggle status and cost.
    """
    db = get_db()
    generate_topology(db, test_network_id, 'star')
    conn = db.execute("SELECT * FROM connections WHERE network_id = ?", (test_network_id,)).fetchone()
    conn_id = conn['id']

    # Update status to down and cost to 15
    res = client.put(f'/api/connections/{conn_id}', json={'status': 'down', 'cost': 15})
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['connection']['status'] == 'down'
    assert data['connection']['cost'] == 15
