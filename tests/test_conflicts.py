"""tests/test_conflicts.py — IP conflict detection tests."""
import pytest
from services.conflict_detection import detect_conflicts, record_conflict, get_all_conflicts


@pytest.fixture(autouse=True)
def ctx(app_ctx):
    yield


def test_detect_conflict_two_macs_same_ip():
    obs = [
        {'ip': '192.168.1.100', 'mac': 'AA:AA:AA:AA:AA:01', 'observed_at': '2026-01-01T00:00:00Z'},
        {'ip': '192.168.1.100', 'mac': 'BB:BB:BB:BB:BB:02', 'observed_at': '2026-01-01T00:00:00Z'},
        {'ip': '192.168.1.200', 'mac': 'CC:CC:CC:CC:CC:03', 'observed_at': '2026-01-01T00:00:00Z'},
    ]
    conflicts = detect_conflicts(obs)
    assert len(conflicts) == 1
    assert conflicts[0]['ip'] == '192.168.1.100'
    assert len(conflicts[0]['macs']) == 2


def test_no_conflict_single_mac_per_ip():
    obs = [
        {'ip': '192.168.1.10', 'mac': 'AA:AA:AA:AA:AA:01', 'observed_at': '2026-01-01T00:00:00Z'},
        {'ip': '192.168.1.11', 'mac': 'BB:BB:BB:BB:BB:02', 'observed_at': '2026-01-01T00:00:00Z'},
    ]
    conflicts = detect_conflicts(obs)
    assert len(conflicts) == 0


def test_conflict_three_macs_same_ip():
    obs = [
        {'ip': '10.0.0.1', 'mac': 'AA:AA:AA:AA:AA:01', 'observed_at': '2026-01-01T00:00:00Z'},
        {'ip': '10.0.0.1', 'mac': 'BB:BB:BB:BB:BB:02', 'observed_at': '2026-01-01T00:00:00Z'},
        {'ip': '10.0.0.1', 'mac': 'CC:CC:CC:CC:CC:03', 'observed_at': '2026-01-01T00:00:00Z'},
    ]
    conflicts = detect_conflicts(obs)
    assert len(conflicts) == 1
    assert len(conflicts[0]['macs']) == 3


def test_record_conflict_creates_row(app_ctx):
    obs = [{'ip': '192.168.1.50', 'mac': 'AA:AA:AA:AA:AA:01', 'observed_at': '2026-01-01T00:00:00Z'}]
    cid = record_conflict('192.168.1.50', 'AA:AA:AA:AA:AA:01', 'BB:BB:BB:BB:BB:02', obs)
    assert isinstance(cid, int)
    conflicts = get_all_conflicts()
    assert any(c['id'] == cid for c in conflicts)


def test_record_conflict_updates_existing(app_ctx):
    obs = [{'ip': '192.168.1.60', 'mac': 'AA:AA:AA:AA:AA:01', 'observed_at': '2026-01-01T00:00:00Z'}]
    cid1 = record_conflict('192.168.1.60', 'AA:AA:AA:AA:AA:01', 'BB:BB:BB:BB:BB:02', obs)
    cid2 = record_conflict('192.168.1.60', 'AA:AA:AA:AA:AA:01', 'CC:CC:CC:CC:CC:03', obs)
    # Should update existing row, not create a duplicate
    conflicts = [c for c in get_all_conflicts() if c['ip_address'] == '192.168.1.60']
    assert len(conflicts) == 1


def test_detect_conflicts_empty_input():
    assert detect_conflicts([]) == []
