"""
simulator/addressing.py
IPv4 network calculation, validation, candidate IP discovery, and MAC utilities.
Uses Python's built-in ipaddress module.
"""
import ipaddress
import random
import re


def validate_network_settings(subnet_str: str, gateway_str: str,
                              dhcp_enabled: bool = True,
                              dhcp_start_str: str = None,
                              dhcp_end_str: str = None) -> tuple[bool, str, dict]:
    """
    Validate all parameters for a virtual LAN.
    Returns (is_valid, error_message, parsed_dict).
    """
    subnet_str = (subnet_str or '').strip()
    gateway_str = (gateway_str or '').strip()

    if not subnet_str:
        return False, "Subnet is required (e.g., 192.168.10.0/24).", {}

    try:
        network = ipaddress.ip_network(subnet_str, strict=False)
    except ValueError as e:
        return False, f"Invalid CIDR subnet: {e}", {}

    if network.version != 4:
        return False, "Only IPv4 subnets are supported.", {}

    if network.prefixlen > 30:
        return False, "Subnet prefix must be /30 or larger (e.g., /24).", {}

    if network.prefixlen < 16:
        return False, "Subnet prefix cannot be larger than /16 for simulation performance.", {}

    # Validate Gateway
    if not gateway_str:
        return False, "Default gateway IP is required.", {}

    try:
        gateway_ip = ipaddress.ip_address(gateway_str)
    except ValueError:
        return False, f"Invalid gateway IP format: '{gateway_str}'.", {}

    if gateway_ip not in network:
        return False, f"Gateway {gateway_ip} is outside subnet {network}.", {}

    if gateway_ip == network.network_address:
        return False, f"Gateway cannot be the network address ({network.network_address}).", {}

    if gateway_ip == network.broadcast_address:
        return False, f"Gateway cannot be the broadcast address ({network.broadcast_address}).", {}

    parsed = {
        'subnet': str(network),
        'netmask': str(network.netmask),
        'gateway': str(gateway_ip),
        'dhcp_enabled': int(bool(dhcp_enabled)),
        'dhcp_start': None,
        'dhcp_end': None,
    }

    if dhcp_enabled:
        dhcp_start_str = (dhcp_start_str or '').strip()
        dhcp_end_str = (dhcp_end_str or '').strip()

        if not dhcp_start_str or not dhcp_end_str:
            return False, "DHCP Start and End IP addresses are required when DHCP is enabled.", {}

        try:
            start_ip = ipaddress.ip_address(dhcp_start_str)
            end_ip = ipaddress.ip_address(dhcp_end_str)
        except ValueError as e:
            return False, f"Invalid DHCP pool IP format: {e}", {}

        if start_ip not in network or end_ip not in network:
            return False, "DHCP pool range must be within the network subnet.", {}

        if start_ip > end_ip:
            return False, f"DHCP start IP ({start_ip}) cannot be greater than end IP ({end_ip}).", {}

        if start_ip == network.network_address or end_ip == network.broadcast_address:
            return False, "DHCP pool cannot include the network or broadcast address.", {}

        if start_ip <= gateway_ip <= end_ip:
            return False, f"DHCP pool cannot contain the default gateway address ({gateway_ip}).", {}

        parsed['dhcp_start'] = str(start_ip)
        parsed['dhcp_end'] = str(end_ip)

    return True, "", parsed


def validate_device_ip(ip_str: str, subnet_str: str, gateway_str: str) -> tuple[bool, str]:
    """
    Check if a device IP is technically valid in the given subnet.
    """
    ip_str = (ip_str or '').strip()
    if not ip_str:
        return False, "IP address cannot be empty."

    try:
        network = ipaddress.ip_network(subnet_str, strict=False)
        ip = ipaddress.ip_address(ip_str)
    except ValueError as e:
        return False, f"Invalid IP address format: {e}"

    if ip not in network:
        return False, f"IP {ip} is outside the subnet {network}."

    if ip == network.network_address:
        return False, f"IP cannot be the subnet network address ({network.network_address})."

    if ip == network.broadcast_address:
        return False, f"IP cannot be the subnet broadcast address ({network.broadcast_address})."

    return True, ""


def find_candidate_ip(subnet_str: str, gateway_str: str,
                      occupied_ips: set[str],
                      dhcp_start: str = None, dhcp_end: str = None,
                      prefer_static_outside_dhcp: bool = True) -> str | None:
    """
    Find a free, valid candidate IPv4 in the subnet.
    Excludes network, broadcast, gateway, and all occupied_ips.
    If prefer_static_outside_dhcp is True and DHCP range is defined,
    prefers addresses outside the DHCP pool.
    """
    try:
        network = ipaddress.ip_network(subnet_str, strict=False)
        gateway = ipaddress.ip_address(gateway_str)
    except ValueError:
        return None

    dhcp_range = set()
    if dhcp_start and dhcp_end:
        try:
            s = int(ipaddress.ip_address(dhcp_start))
            e = int(ipaddress.ip_address(dhcp_end))
            dhcp_range = {str(ipaddress.ip_address(val)) for val in range(s, e + 1)}
        except ValueError:
            pass

    # Excluded set
    reserved = {str(network.network_address), str(network.broadcast_address), str(gateway)}
    all_taken = reserved | set(occupied_ips)

    candidates_outside_dhcp = []
    candidates_in_dhcp = []

    for host in network.hosts():
        ip_str = str(host)
        if ip_str in all_taken:
            continue
        if ip_str in dhcp_range:
            candidates_in_dhcp.append(ip_str)
        else:
            candidates_outside_dhcp.append(ip_str)

    if prefer_static_outside_dhcp and candidates_outside_dhcp:
        return candidates_outside_dhcp[0]

    if candidates_in_dhcp:
        return candidates_in_dhcp[0]

    if candidates_outside_dhcp:
        return candidates_outside_dhcp[0]

    return None


def generate_virtual_mac() -> str:
    """
    Generate a random, locally-administered unicast MAC address.
    Format: 02:xx:xx:xx:xx:xx (02 ensures local + unicast).
    """
    octets = [0x02] + [random.randint(0x00, 0xFF) for _ in range(5)]
    return ':'.join(f'{b:02X}' for b in octets)


def is_valid_mac(mac_str: str) -> bool:
    """Validate MAC address format."""
    return bool(re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', mac_str or ''))
