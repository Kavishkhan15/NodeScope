"""tests/test_discovery.py — Subnet validation and demo observation tests."""
import pytest
from services.discovery import validate_subnet, get_demo_observations, is_demo_mode


class TestValidateSubnet:
    def test_valid_192_168_slash24(self):
        ok, result = validate_subnet('192.168.1.0/24')
        assert ok is True

    def test_valid_10_x_slash24(self):
        ok, result = validate_subnet('10.0.0.0/24')
        assert ok is True

    def test_valid_172_16_slash24(self):
        ok, result = validate_subnet('172.16.0.0/24')
        assert ok is True

    def test_rejects_public_ip(self):
        ok, msg = validate_subnet('8.8.8.0/24')
        assert ok is False
        assert 'private' in msg.lower()

    def test_rejects_too_large_subnet(self):
        # 10.0.0.0/20 has 4096 hosts, over the 1024 limit
        ok, msg = validate_subnet('10.0.0.0/20')
        assert ok is False
        assert 'maximum' in msg.lower() or 'exceed' in msg.lower()

    def test_rejects_invalid_string(self):
        ok, msg = validate_subnet('not-a-subnet')
        assert ok is False

    def test_rejects_empty(self):
        ok, msg = validate_subnet('')
        assert ok is False

    def test_rejects_ipv6(self):
        ok, msg = validate_subnet('::1/128')
        assert ok is False
        assert 'IPv4' in msg or 'private' in msg.lower()

    def test_slash_22_accepted(self):
        # /22 = 1022 hosts, just under the 1024 limit
        ok, result = validate_subnet('192.168.0.0/22')
        assert ok is True

    def test_slash_21_rejected(self):
        # /21 = 2046 hosts, over the limit
        ok, msg = validate_subnet('192.168.0.0/21')
        assert ok is False


class TestDemoObservations:
    def test_returns_list(self):
        obs = get_demo_observations()
        assert isinstance(obs, list)
        assert len(obs) >= 5

    def test_each_has_ip_mac_timestamp(self):
        for obs in get_demo_observations():
            assert 'ip' in obs
            assert 'mac' in obs
            assert 'observed_at' in obs

    def test_contains_conflict(self):
        """Demo data must include two observations with the same IP."""
        obs = get_demo_observations()
        from collections import Counter
        ip_counts = Counter(o['ip'] for o in obs)
        assert any(count >= 2 for count in ip_counts.values()), \
            "Demo observations must include at least one duplicate IP"

    def test_macs_uppercase(self):
        for obs in get_demo_observations():
            assert obs['mac'] == obs['mac'].upper()


def test_demo_mode_env(monkeypatch):
    monkeypatch.setenv('NODESCOPE_DEMO', '1')
    assert is_demo_mode() is True

def test_live_mode_env(monkeypatch):
    monkeypatch.setenv('NODESCOPE_DEMO', '0')
    assert is_demo_mode() is False
