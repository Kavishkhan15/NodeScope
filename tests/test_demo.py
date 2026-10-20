"""tests/test_demo.py — Demo seeding and reset tests."""
import pytest
from demo.seed import seed_demo_data, reset_demo
from database.db import get_db


@pytest.fixture(autouse=True)
def ctx(app_ctx):
    yield


def test_seed_populates_devices(app_ctx):
    counts = seed_demo_data()
    assert 'devices' in counts
    assert counts['devices'] == 6


def test_seed_populates_conflicts(app_ctx):
    seed_demo_data()
    db = get_db()
    n = db.execute("SELECT COUNT(*) FROM ip_conflicts WHERE is_demo=1").fetchone()[0]
    assert n >= 1


def test_seed_populates_alerts(app_ctx):
    seed_demo_data()
    db = get_db()
    n = db.execute("SELECT COUNT(*) FROM alerts WHERE is_demo=1").fetchone()[0]
    assert n >= 2


def test_seed_populates_events(app_ctx):
    seed_demo_data()
    db = get_db()
    n = db.execute("SELECT COUNT(*) FROM activity_events WHERE is_demo=1").fetchone()[0]
    assert n >= 3


def test_reset_removes_only_demo_records(app_ctx):
    # Insert a real (non-demo) device
    db = get_db()
    db.execute(
        """INSERT INTO devices (mac_address, ip_address, approved, first_seen, last_seen, is_demo)
           VALUES ('00:11:22:33:44:55', '10.0.0.1', 1, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z', 0)"""
    )
    db.commit()

    seed_demo_data()
    reset_demo()

    real_count = db.execute("SELECT COUNT(*) FROM devices WHERE is_demo=0").fetchone()[0]
    demo_count = db.execute("SELECT COUNT(*) FROM devices WHERE is_demo=1").fetchone()[0]
    assert real_count >= 1
    assert demo_count == 0


def test_seed_idempotent_message(app_ctx):
    seed_demo_data()
    result = seed_demo_data()  # second call
    assert 'message' in result  # returns "already exists" message


def test_demo_scan_endpoint(client):
    """POST /scan/demo should redirect to dashboard."""
    response = client.post('/scan/demo', follow_redirects=True)
    assert response.status_code == 200
