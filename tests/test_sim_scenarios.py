"""
tests/test_sim_scenarios.py
Unit tests for the 5 educational scenarios.
"""
from database.db import get_db
from simulator.scenarios import load_example_scenario


def test_load_all_five_scenarios(app_ctx):
    db = get_db()
    for s_id in range(1, 6):
        net_id = load_example_scenario(db, s_id)
        assert net_id > 0

        # Check network exists
        net = db.execute("SELECT * FROM networks WHERE id = ?", (net_id,)).fetchone()
        assert net is not None
        assert f"Scenario {s_id}" in net['name']

        # Check devices were created
        devs = db.execute("SELECT * FROM devices WHERE network_id = ?", (net_id,)).fetchall()
        assert len(devs) >= 2

        # Special scenario validations
        if s_id == 2:
            # Should have an active conflict
            conflicts = db.execute("SELECT * FROM ip_conflicts WHERE network_id = ? AND status = 'active'", (net_id,)).fetchall()
            assert len(conflicts) == 1
            assert conflicts[0]['ip_address'] == '192.168.10.50'

        if s_id == 5:
            # Should have an unapproved device
            unapproved = db.execute("SELECT * FROM devices WHERE network_id = ? AND is_approved = 0", (net_id,)).fetchall()
            assert len(unapproved) >= 1
