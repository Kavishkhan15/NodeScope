"""tests/test_resolution.py — Guided IP conflict resolution tests."""
import pytest
from services.conflict_detection import record_conflict
from services.resolution import suggest_resolution, record_resolution_attempt, verify_resolution


@pytest.fixture(autouse=True)
def ctx(app_ctx):
    yield


def _make_conflict(ip='192.168.1.100'):
    obs = [{'ip': ip, 'mac': 'AA:AA:AA:AA:AA:01', 'observed_at': '2026-01-01T00:00:00Z'}]
    return record_conflict(ip, 'AA:AA:AA:AA:AA:01', 'BB:BB:BB:BB:BB:02', obs)


def test_suggest_resolution_returns_dict(app_ctx):
    cid = _make_conflict()
    result = suggest_resolution(cid)
    assert isinstance(result, dict)
    assert 'conflict_ip' in result
    assert 'steps' in result
    assert 'warnings' in result


def test_suggest_resolution_can_suggest(app_ctx):
    cid = _make_conflict('192.168.1.50')
    result = suggest_resolution(cid)
    # Should be able to find a free address in /24 with minimal observations
    assert result['can_suggest'] is True
    assert result['suggested_ip'] is not None


def test_suggested_ip_not_network_broadcast_or_gateway(app_ctx):
    cid = _make_conflict('192.168.1.10')
    result = suggest_resolution(cid)
    if result['can_suggest']:
        ip = result['suggested_ip']
        last_octet = int(ip.split('.')[-1])
        assert last_octet not in (0, 1, 255), \
            f"Suggested IP {ip} should not be network/gateway/broadcast"


def test_suggested_ip_in_same_subnet(app_ctx):
    cid = _make_conflict('192.168.5.10')
    result = suggest_resolution(cid)
    if result['can_suggest']:
        assert result['suggested_ip'].startswith('192.168.5.')


def test_record_resolution_attempt(app_ctx):
    cid = _make_conflict('192.168.1.70')
    suggestion = suggest_resolution(cid)
    action_id = record_resolution_attempt(
        cid,
        recommended_ip=suggestion.get('suggested_ip'),
        action_taken='Changed static IP on desktop PC',
        admin_notes='Device at 192.168.1.70 reconfigured'
    )
    assert isinstance(action_id, int)


def test_verify_resolution_not_present(app_ctx):
    cid = _make_conflict('192.168.1.80')
    record_resolution_attempt(cid, '192.168.1.90', 'Changed IP', None)
    result = verify_resolution(cid, still_present=False, admin_notes='Verified clean')
    assert result is True
    from services.conflict_detection import get_conflict_by_id
    conflict = get_conflict_by_id(cid)
    assert conflict['status'] == 'resolved'


def test_suggest_nonexistent_conflict(app_ctx):
    result = suggest_resolution(99999)
    assert result.get('can_suggest') is False
    assert 'error' in result
