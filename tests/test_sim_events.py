"""
tests/test_sim_events.py
Tests for simulation event audit logging and alert triage.
"""
from database.db import get_db
from simulator.events import record_simulation_event, get_recent_events, get_active_alerts, create_device_alert


def test_simulation_events_and_alerts(app_ctx):
    db = get_db()
    net_id = db.execute("""
        INSERT INTO networks (name, subnet, netmask, gateway, created_at, updated_at)
        VALUES ('Lab', '192.168.10.0/24', '255.255.255.0', '192.168.10.1', '2026-01-01', '2026-01-01')
    """).lastrowid

    # Record event
    ev_id = record_simulation_event(db, net_id, 'device', 'info', "Test device event")
    assert ev_id > 0

    events = get_recent_events(db, net_id)
    assert len(events) == 1
    assert events[0]['message'] == "Test device event"

    # Create alert
    al_id = create_device_alert(db, net_id, 'unapproved_device', 1, "Unapproved device detected")
    assert al_id > 0

    alerts = get_active_alerts(db, net_id)
    assert len(alerts) == 1
    assert alerts[0]['status'] == 'active'

    # Dismiss alert
    db.execute("UPDATE alerts SET status = 'dismissed' WHERE id = ?", (al_id,))
    active = get_active_alerts(db, net_id)
    assert len(active) == 0
