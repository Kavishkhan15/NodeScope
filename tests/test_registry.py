"""tests/test_registry.py — Device registry and rogue device detection tests."""
import pytest


@pytest.fixture(autouse=True)
def ctx(app_ctx):
    yield


def test_register_new_device(app_ctx):
    from services.device_registry import register_observation, get_device_by_mac
    result = register_observation('192.168.1.50', 'AA:BB:CC:DD:EE:FF',
                                  '2026-01-01T00:00:00Z', scan_id=1)
    assert result['is_new'] is True
    device = get_device_by_mac('AA:BB:CC:DD:EE:FF')
    assert device is not None
    assert device['ip_address'] == '192.168.1.50'
    assert device['approved'] == 0


def test_register_duplicate_does_not_duplicate(app_ctx):
    from services.device_registry import register_observation, get_all_devices
    mac = 'BB:BB:BB:BB:BB:BB'
    register_observation('10.0.0.1', mac, '2026-01-01T00:00:00Z', scan_id=1)
    register_observation('10.0.0.1', mac, '2026-01-01T01:00:00Z', scan_id=2)
    devices = [d for d in get_all_devices() if d['mac_address'] == mac]
    assert len(devices) == 1


def test_ip_change_detected(app_ctx):
    from services.device_registry import register_observation, get_device_by_mac
    mac = 'CC:CC:CC:CC:CC:CC'
    register_observation('192.168.1.10', mac, '2026-01-01T00:00:00Z', scan_id=1)
    result = register_observation('192.168.1.20', mac, '2026-01-01T01:00:00Z', scan_id=2)
    assert result['ip_changed'] is True
    device = get_device_by_mac(mac)
    assert device['ip_address'] == '192.168.1.20'


def test_approve_device(app_ctx):
    from services.device_registry import register_observation, approve_device, get_device_by_mac
    mac = 'DD:DD:DD:DD:DD:DD'
    register_observation('192.168.1.30', mac, '2026-01-01T00:00:00Z', scan_id=1)
    result = approve_device(mac, friendly_name='Test PC', notes='test')
    assert result is True
    device = get_device_by_mac(mac)
    assert device['approved'] == 1
    assert device['friendly_name'] == 'Test PC'


def test_unknown_device_detection(app_ctx):
    from services.device_registry import register_observation, check_unknown_devices
    mac_approved = 'EE:EE:EE:EE:EE:01'
    mac_unknown  = 'EE:EE:EE:EE:EE:02'
    from services.device_registry import approve_device
    register_observation('192.168.1.40', mac_approved, '2026-01-01T00:00:00Z', scan_id=1)
    approve_device(mac_approved, 'Approved Device')
    register_observation('192.168.1.41', mac_unknown, '2026-01-01T00:00:00Z', scan_id=1)

    observations = [
        {'ip': '192.168.1.40', 'mac': mac_approved, 'observed_at': '2026-01-01T00:00:00Z'},
        {'ip': '192.168.1.41', 'mac': mac_unknown,  'observed_at': '2026-01-01T00:00:00Z'},
    ]
    unknown = check_unknown_devices(observations)
    assert len(unknown) == 1
    assert unknown[0]['mac'] == mac_unknown


def test_approve_nonexistent_device_returns_false(app_ctx):
    from services.device_registry import approve_device
    result = approve_device('FF:FF:FF:FF:FF:FF', 'Ghost')
    assert result is False
