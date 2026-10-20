"""tests/test_history.py — Activity history and alert tests."""
import pytest
from services.activity_history import (
    record_event, get_events, create_alert,
    get_active_alerts, acknowledge_alert, dismiss_alert
)


@pytest.fixture(autouse=True)
def ctx(app_ctx):
    yield


def test_record_event_inserts(app_ctx):
    eid = record_event('device_discovered', 'AA:BB:CC:DD:EE:FF', '10.0.0.1', 'Test event')
    assert eid is not None
    events = get_events()
    assert any(e['description'] == 'Test event' for e in events)


def test_record_event_dedup_within_60s(app_ctx):
    record_event('ip_changed', 'AA:AA:AA:AA:AA:AA', '10.0.0.5', 'IP changed')
    result = record_event('ip_changed', 'AA:AA:AA:AA:AA:AA', '10.0.0.5', 'IP changed again')
    assert result is None  # deduplicated


def test_filter_by_event_type(app_ctx):
    record_event('device_approved', 'BB:BB:BB:BB:BB:BB', None, 'Approved device')
    record_event('ip_changed', 'CC:CC:CC:CC:CC:CC', '10.0.0.9', 'IP change')
    approved_events = get_events(event_type_filter='device_approved')
    assert all(e['event_type'] == 'device_approved' for e in approved_events)


def test_create_alert(app_ctx):
    aid = create_alert('unknown_device', 'DD:DD:DD:DD:DD:DD',
                       '10.0.0.20', 'Unknown device message')
    assert aid is not None
    alerts = get_active_alerts()
    assert any(a['id'] == aid for a in alerts)


def test_acknowledge_alert(app_ctx):
    aid = create_alert('ip_conflict', None, '10.0.0.30', 'Conflict alert')
    result = acknowledge_alert(aid, notes='Looked into it')
    assert result is True
    alerts = get_active_alerts()
    assert not any(a['id'] == aid for a in alerts)  # removed from active


def test_dismiss_alert(app_ctx):
    aid = create_alert('unknown_device', 'EE:EE:EE:EE:EE:EE', '10.0.0.40', 'Another alert')
    dismiss_alert(aid, notes='Not a threat')
    active = get_active_alerts()
    assert not any(a['id'] == aid for a in active)


def test_get_events_returns_list(app_ctx):
    result = get_events()
    assert isinstance(result, list)
