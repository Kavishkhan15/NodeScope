"""
simulator/packet.py
End-to-End Packet Transmission and ICMP Diagnostic Simulator for NodeScope.
Models:
1. Generic Simulated Data Packets (DATA)
2. ICMP Echo Request & Echo Reply (PING) with sequential two-way hop journey
3. Dynamic packet drop at broken links or powered-off intermediate routers
4. Hop-by-hop animation telemetry for frontend canvas rendering
"""
import datetime
import json
import uuid
import ipaddress
from simulator.routing import calculate_route_dispatch, get_network_graph


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def transmit_packet(db, network_id: int, src_id: int, dst_id: int, packet_type: str = 'DATA', algorithm: str = 'dijkstra', options: dict = None) -> dict:
    """
    Simulate end-to-end packet transmission from src_id to dst_id.
    Returns complete packet telemetry dict including unique simulation ID,
    calculated route, hop-by-hop steps, status, latency, and failure diagnostics.
    """
    options = options or {}
    now_str = _now()
    pkt_id = f"PKT-{str(uuid.uuid4())[:8].upper()}"

    net = db.execute("SELECT * FROM networks WHERE id = ?", (network_id,)).fetchone()
    if not net:
        return {'status': 'failed', 'packet_id': pkt_id, 'message': 'Network not found.', 'hops': []}

    src = db.execute("SELECT * FROM devices WHERE id = ? AND network_id = ?", (src_id, network_id)).fetchone()
    dst = db.execute("SELECT * FROM devices WHERE id = ? AND network_id = ?", (dst_id, network_id)).fetchone()

    if not src or not dst:
        return {'status': 'failed', 'packet_id': pkt_id, 'message': 'Source or destination device not found.', 'hops': []}

    src_dict = dict(src)
    dst_dict = dict(dst)

    # 1. Source Power Check
    if not src_dict['is_online']:
        msg = f"Transmission aborted: Source '{src_dict['name']}' is powered OFF."
        _log_packet_event(db, network_id, pkt_id, packet_type, src_dict['name'], dst_dict['name'], 'failed', msg)
        return {'status': 'failed', 'packet_id': pkt_id, 'message': msg, 'failure_reason': 'Source device offline', 'hops': []}

    # 2. Destination Power Check
    if not dst_dict['is_online']:
        msg = f"Transmission failed: Destination '{dst_dict['name']}' is powered OFF (Host Unreachable)."
        _log_packet_event(db, network_id, pkt_id, packet_type, src_dict['name'], dst_dict['name'], 'failed', msg)
        return {'status': 'failed', 'packet_id': pkt_id, 'message': msg, 'failure_reason': 'Destination device offline', 'hops': []}

    # 3. Security NAC Check (Preserving Access Control)
    if not src_dict['is_approved']:
        msg = f"Transmission blocked: Source '{src_dict['name']}' is UNAPPROVED (Network Access Control blocked rogue host)."
        _log_packet_event(db, network_id, pkt_id, packet_type, src_dict['name'], dst_dict['name'], 'failed', msg)
        return {'status': 'failed', 'packet_id': pkt_id, 'message': msg, 'failure_reason': 'Source unapproved (NAC block)', 'hops': []}

    if not dst_dict['is_approved']:
        msg = f"Transmission blocked: Destination '{dst_dict['name']}' is UNAPPROVED (Network Access Control blocked rogue host)."
        _log_packet_event(db, network_id, pkt_id, packet_type, src_dict['name'], dst_dict['name'], 'failed', msg)
        return {'status': 'failed', 'packet_id': pkt_id, 'message': msg, 'failure_reason': 'Destination unapproved (NAC block)', 'hops': []}

    # 4. IP Conflict Check
    conflict_rows = db.execute("SELECT ip_address FROM ip_conflicts WHERE network_id = ? AND status = 'active'", (network_id,)).fetchall()
    conflict_ips = {r['ip_address'] for r in conflict_rows}

    if src_dict['ip_address'] and src_dict['ip_address'] in conflict_ips:
        msg = f"Transmission failed: Source IP {src_dict['ip_address']} has an active address collision (ARP ambiguity)."
        _log_packet_event(db, network_id, pkt_id, packet_type, src_dict['name'], dst_dict['name'], 'failed', msg)
        return {'status': 'failed', 'packet_id': pkt_id, 'message': msg, 'failure_reason': 'Source IP conflict', 'hops': []}

    if dst_dict['ip_address'] and dst_dict['ip_address'] in conflict_ips:
        msg = f"Transmission failed: Destination IP {dst_dict['ip_address']} has an active address collision (ARP ambiguity)."
        _log_packet_event(db, network_id, pkt_id, packet_type, src_dict['name'], dst_dict['name'], 'failed', msg)
        return {'status': 'failed', 'packet_id': pkt_id, 'message': msg, 'failure_reason': 'Destination IP conflict', 'hops': []}

    # 5. Route Calculation via Selected Routing Algorithm
    route_res = calculate_route_dispatch(db, network_id, src_id, dst_id, algorithm=algorithm, options=options)

    if route_res['status'] != 'success' or not route_res['path']:
        msg = f"Routing failure ({algorithm.upper()}): {route_res.get('message', 'No active path found.')}"
        _log_packet_event(db, network_id, pkt_id, packet_type, src_dict['name'], dst_dict['name'], 'failed', msg)
        return {
            'status': 'failed',
            'packet_id': pkt_id,
            'message': msg,
            'failure_reason': 'No route to host / Destination unreachable',
            'algorithm': algorithm,
            'hops': [],
            'explanation': route_res.get('explanation', 'No path through active links.')
        }

    path_devs = route_res['path']
    link_ids = route_res['links']

    # 6. Build Hop-by-Hop Sequence
    forward_hops = []
    total_delay = 0

    for i in range(len(path_devs) - 1):
        u_dev = path_devs[i]
        v_dev = path_devs[i + 1]
        link_id = link_ids[i] if i < len(link_ids) else None

        # Fetch link details
        conn_row = db.execute("SELECT * FROM connections WHERE id = ?", (link_id,)).fetchone()
        conn_dict = dict(conn_row) if conn_row else {'cost': 1, 'delay_ms': 2, 'status': 'active'}

        hop_delay = conn_dict.get('delay_ms') or 2
        total_delay += hop_delay

        forward_hops.append({
            'hop_index': i + 1,
            'from_node_id': u_dev['id'],
            'from_node_name': u_dev['name'],
            'from_node_type': u_dev['device_type'],
            'from_ip': u_dev['ip_address'] or 'N/A',
            'to_node_id': v_dev['id'],
            'to_node_name': v_dev['name'],
            'to_node_type': v_dev['device_type'],
            'to_ip': v_dev['ip_address'] or 'N/A',
            'link_id': link_id,
            'link_cost': conn_dict.get('cost') or 1,
            'delay_ms': hop_delay,
            'action': 'forward',
            'subpacket_type': 'ICMP Echo Request' if packet_type == 'PING' else packet_type
        })

    # 7. Check ICMP PING Two-Way Journey
    return_hops = []
    is_ping = (packet_type.upper() == 'PING')

    if is_ping:
        # Reverse route calculation from dst back to src
        rev_route = calculate_route_dispatch(db, network_id, dst_id, src_id, algorithm=algorithm, options=options)

        if rev_route['status'] != 'success' or not rev_route['path']:
            # Echo Request reached destination, but Echo Reply dropped on return path!
            msg = f"ICMP Ping request reached '{dst_dict['name']}', but Echo Reply failed on return path (Request Timed Out)."
            _log_packet_event(db, network_id, pkt_id, 'PING', src_dict['name'], dst_dict['name'], 'failed', msg)
            return {
                'status': 'timeout',
                'packet_id': pkt_id,
                'packet_type': 'PING',
                'source': src_dict,
                'destination': dst_dict,
                'algorithm': algorithm,
                'forward_hops': forward_hops,
                'return_hops': [],
                'hops': forward_hops,
                'total_hops': len(forward_hops),
                'rtt_ms': total_delay * 2,
                'message': msg,
                'failure_reason': 'Return path broken (Echo Reply dropped)',
                'request_delivered': True,
                'reply_delivered': False
            }

        rev_devs = rev_route['path']
        rev_links = rev_route['links']

        for j in range(len(rev_devs) - 1):
            u_dev = rev_devs[j]
            v_dev = rev_devs[j + 1]
            link_id = rev_links[j] if j < len(rev_links) else None

            conn_row = db.execute("SELECT * FROM connections WHERE id = ?", (link_id,)).fetchone()
            conn_dict = dict(conn_row) if conn_row else {'cost': 1, 'delay_ms': 2, 'status': 'active'}
            hop_delay = conn_dict.get('delay_ms') or 2
            total_delay += hop_delay

            return_hops.append({
                'hop_index': len(forward_hops) + j + 1,
                'from_node_id': u_dev['id'],
                'from_node_name': u_dev['name'],
                'from_node_type': u_dev['device_type'],
                'from_ip': u_dev['ip_address'] or 'N/A',
                'to_node_id': v_dev['id'],
                'to_node_name': v_dev['name'],
                'to_node_type': v_dev['device_type'],
                'to_ip': v_dev['ip_address'] or 'N/A',
                'link_id': link_id,
                'link_cost': conn_dict.get('cost') or 1,
                'delay_ms': hop_delay,
                'action': 'forward',
                'subpacket_type': 'ICMP Echo Reply'
            })

    # Combined hops for animation
    all_hops = forward_hops + return_hops
    hops_count = len(forward_hops)

    if is_ping:
        msg = f"ICMP Ping successful: Reply from {dst_dict['ip_address']}: bytes=32 time={total_delay}ms TTL=64 ({algorithm.upper()} path: {' → '.join(d['name'] for d in path_devs)})"
    else:
        msg = f"Packet {pkt_id} ({packet_type}) successfully delivered from '{src_dict['name']}' to '{dst_dict['name']}' in {hops_count} hops (Latency: {total_delay}ms)."

    _log_packet_event(db, network_id, pkt_id, packet_type, src_dict['name'], dst_dict['name'], 'delivered', msg, [d['name'] for d in path_devs])

    return {
        'status': 'delivered',
        'packet_id': pkt_id,
        'packet_type': packet_type,
        'source': src_dict,
        'destination': dst_dict,
        'algorithm': algorithm,
        'forward_hops': forward_hops,
        'return_hops': return_hops,
        'hops': all_hops,
        'total_hops': len(all_hops),
        'forward_path': [d['name'] for d in path_devs],
        'forward_path_ids': [d['id'] for d in path_devs],
        'links_used': link_ids,
        'total_cost': route_res['total_cost'],
        'rtt_ms': total_delay,
        'message': msg,
        'explanation': route_res.get('explanation', f"Calculated using {algorithm.upper()} algorithm."),
        'request_delivered': True,
        'reply_delivered': True if is_ping else None
    }


def _log_packet_event(db, network_id: int, pkt_id: str, ptype: str, src: str, dst: str, status: str, message: str, path: list = None):
    level = 'success' if status == 'delivered' else 'danger'
    db.execute("""
        INSERT INTO simulation_events (network_id, category, level, message, details, created_at)
        VALUES (?, 'packet', ?, ?, ?, ?)
    """, (
        network_id,
        level,
        message,
        json.dumps({'packet_id': pkt_id, 'type': ptype, 'source': src, 'destination': dst, 'status': status, 'path': path or []}),
        _now()
    ))
    db.commit()
