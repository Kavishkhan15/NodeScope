"""
simulator/arp.py
Educational Virtual ARP Table inspection.
Maps IP addresses to MAC addresses and flags collisions/ambiguities.
"""
from collections import defaultdict


def get_virtual_arp_table(db, network_id: int) -> list[dict]:
    """
    Generate the virtual ARP resolution table for the network.
    Shows: IP, MAC(s), Device Name(s), Interface Type, Status (Valid / Ambiguous Conflict).
    """
    dev_rows = db.execute("""
        SELECT * FROM devices 
        WHERE network_id = ? AND ip_address IS NOT NULL AND ip_address != '' AND is_online = 1
        ORDER BY ip_address ASC
    """, (network_id,)).fetchall()

    ip_map = defaultdict(list)
    for dev in dev_rows:
        ip_map[dev['ip_address'].strip()].append(dict(dev))

    arp_entries = []
    for ip, devs in sorted(ip_map.items()):
        is_ambiguous = len(devs) > 1
        for dev in devs:
            arp_entries.append({
                'ip_address': ip,
                'mac_address': dev['mac_address'],
                'device_id': dev['id'],
                'device_name': dev['name'],
                'device_type': dev['device_type'],
                'is_approved': bool(dev['is_approved']),
                'status': 'AMBIGUOUS (IP Conflict)' if is_ambiguous else 'DYNAMIC (Resolved)',
                'is_conflict': is_ambiguous,
                'notes': f"Multiple hosts ({', '.join(d['name'] for d in devs)}) claim {ip}" if is_ambiguous else "Normal ARP binding"
            })

    return arp_entries
