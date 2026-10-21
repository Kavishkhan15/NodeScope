"""
tests/test_sim_addressing.py
Unit tests for subnet calculation, address validation, and candidate IP discovery.
"""
from simulator.addressing import (
    validate_network_settings, validate_device_ip,
    find_candidate_ip, generate_virtual_mac, is_valid_mac
)


def test_validate_valid_network_settings():
    valid, err, parsed = validate_network_settings(
        "192.168.10.0/24", "192.168.10.1", True, "192.168.10.100", "192.168.10.199"
    )
    assert valid is True
    assert err == ""
    assert parsed['subnet'] == "192.168.10.0/24"
    assert parsed['netmask'] == "255.255.255.0"
    assert parsed['gateway'] == "192.168.10.1"
    assert parsed['dhcp_enabled'] == 1


def test_validate_invalid_subnet():
    valid, err, _ = validate_network_settings("999.999.0.0/24", "192.168.10.1")
    assert valid is False
    assert "Invalid CIDR subnet" in err


def test_validate_gateway_outside_subnet():
    valid, err, _ = validate_network_settings("192.168.10.0/24", "10.0.0.1")
    assert valid is False
    assert "outside subnet" in err


def test_validate_gateway_is_broadcast():
    valid, err, _ = validate_network_settings("192.168.10.0/24", "192.168.10.255")
    assert valid is False
    assert "cannot be the broadcast address" in err


def test_validate_dhcp_range_inverted():
    valid, err, _ = validate_network_settings(
        "192.168.10.0/24", "192.168.10.1", True, "192.168.10.150", "192.168.10.100"
    )
    assert valid is False
    assert "cannot be greater than end IP" in err


def test_validate_device_ip_valid():
    valid, err = validate_device_ip("192.168.10.50", "192.168.10.0/24", "192.168.10.1")
    assert valid is True
    assert err == ""


def test_validate_device_ip_network_address():
    valid, err = validate_device_ip("192.168.10.0", "192.168.10.0/24", "192.168.10.1")
    assert valid is False
    assert "cannot be the subnet network address" in err


def test_find_candidate_ip_excludes_occupied():
    subnet = "192.168.10.0/24"
    gateway = "192.168.10.1"
    occupied = {"192.168.10.2", "192.168.10.3"}
    candidate = find_candidate_ip(subnet, gateway, occupied, "192.168.10.100", "192.168.10.199")
    assert candidate is not None
    assert candidate not in occupied
    assert candidate != gateway
    assert candidate != "192.168.10.0"
    assert candidate != "192.168.10.255"


def test_virtual_mac_generation():
    mac = generate_virtual_mac()
    assert is_valid_mac(mac)
    assert mac.startswith("02:")
