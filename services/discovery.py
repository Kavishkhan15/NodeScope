"""
services/discovery.py
Network discovery using ARP (via Scapy).
Falls back to demo mode when raw sockets are unavailable or NODESCOPE_DEMO=1.

IMPORTANT: ARP scanning only works on the local LAN segment.
Only scan networks you own or have explicit written permission to scan.
"""
import os
import ipaddress
import datetime

# Private IPv4 ranges — scanning is only permitted within these
_PRIVATE_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),
]

MAX_SCAN_HOSTS = 1024  # refuse to scan subnets larger than this


def is_demo_mode() -> bool:
    """Return True when NODESCOPE_DEMO env var is set to '1'."""
    return os.environ.get('NODESCOPE_DEMO', '0') == '1'


def validate_subnet(subnet: str) -> tuple:
    """
    Validate a CIDR subnet string.
    Returns (True, network_object) on success.
    Returns (False, error_message_string) on failure.
    """
    subnet = subnet.strip()
    if not subnet:
        return False, "Subnet is required."

    try:
        network = ipaddress.ip_network(subnet, strict=False)
    except ValueError:
        return False, f"'{subnet}' is not a valid CIDR subnet (e.g. 192.168.1.0/24)."

    if network.version != 4:
        return False, "Only IPv4 subnets are supported."

    # Must be a private range
    is_private = any(network.subnet_of(r) for r in _PRIVATE_RANGES)
    if not is_private:
        return False, (
            f"'{subnet}' is not a private network address range. "
            "NodeScope only scans private LAN subnets "
            "(10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)."
        )

    host_count = network.num_addresses - 2  # exclude network + broadcast
    if host_count > MAX_SCAN_HOSTS:
        return False, (
            f"Subnet {subnet} has {host_count} hosts, which exceeds the "
            f"maximum of {MAX_SCAN_HOSTS}. Use a smaller subnet (e.g. /22 or smaller)."
        )

    return True, network


def scan_subnet_arp(subnet: str, scan_id: int) -> tuple:
    """
    Perform an ARP scan of the given subnet using Scapy.
    Returns (observations, error_message).
    observations is a list of dicts: {ip, mac, observed_at}
    error_message is None on success, a string on partial/full failure.

    Falls back gracefully when Scapy is unavailable or permissions are missing.
    """
    observations = []
    error_message = None
    now = datetime.datetime.utcnow().isoformat() + 'Z'

    # Validate first
    ok, result = validate_subnet(subnet)
    if not ok:
        return [], result

    network = result

    try:
        from scapy.all import ARP, Ether, srp  # type: ignore
        import warnings
        warnings.filterwarnings('ignore')  # suppress Scapy interface warnings
    except ImportError:
        return [], (
            "Scapy is not installed. Install it with: pip install scapy. "
            "Use Demo Mode to explore NodeScope features without live scanning."
        )

    try:
        # Build ARP request packet
        arp_request = ARP(pdst=str(network))
        broadcast = Ether(dst='ff:ff:ff:ff:ff:ff')
        packet = broadcast / arp_request

        # Send and receive — timeout 3s, verbose off
        answered, _ = srp(packet, timeout=3, verbose=False)

        for _, response in answered:
            observations.append({
                'ip': response.psrc,
                'mac': response.hwsrc.upper(),
                'observed_at': now
            })

    except PermissionError:
        error_message = (
            "Permission denied: ARP scanning requires elevated privileges. "
            "On Windows, run VS Code / the terminal as Administrator. "
            "Alternatively, enable Demo Mode (NODESCOPE_DEMO=1) to explore without scanning."
        )
    except OSError as exc:
        error_message = (
            f"Network error during ARP scan: {exc}. "
            "Ensure Npcap (Windows) or libpcap (Linux/Mac) is installed. "
            "See the README Troubleshooting section."
        )
    except Exception as exc:  # noqa: BLE001
        error_message = f"Unexpected error during scan: {exc}"

    return observations, error_message


def get_demo_observations() -> list:
    """
    Return a fixed set of demo ARP observations.
    These mimic what a real scan would return on a home network.
    All are clearly marked as simulated — not from a real network.
    """
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    return [
        {'ip': '192.168.1.1',   'mac': 'AA:BB:CC:DD:EE:01', 'observed_at': now},
        {'ip': '192.168.1.100', 'mac': 'AA:BB:CC:DD:EE:02', 'observed_at': now},
        {'ip': '192.168.1.101', 'mac': 'AA:BB:CC:DD:EE:03', 'observed_at': now},
        {'ip': '192.168.1.102', 'mac': 'AA:BB:CC:DD:EE:04', 'observed_at': now},
        {'ip': '192.168.1.103', 'mac': 'AA:BB:CC:DD:EE:05', 'observed_at': now},
        # Unknown device — not in approved registry
        {'ip': '192.168.1.150', 'mac': 'FF:EE:DD:CC:BB:06', 'observed_at': now},
        # Conflict: 192.168.1.100 appears with a second MAC
        {'ip': '192.168.1.100', 'mac': '11:22:33:44:55:02', 'observed_at': now},
    ]
