"""
routes/views.py
HTML Template Views for the NodeScope Virtual LAN Simulator.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database.db import get_db
from simulator.scenarios import load_example_scenario
from simulator.conflicts import detect_and_update_conflicts

bp = Blueprint('views', __name__)


@bp.route('/')
def welcome():
    """Welcome page: Create network, Saved networks, and Example scenarios."""
    db = get_db()
    networks = db.execute("""
        SELECT n.*,
               (SELECT COUNT(*) FROM devices WHERE network_id = n.id) AS device_count,
               (SELECT COUNT(*) FROM connections WHERE network_id = n.id) AS connection_count,
               (SELECT COUNT(*) FROM ip_conflicts WHERE network_id = n.id AND status = 'active') AS conflict_count
        FROM networks n
        ORDER BY n.updated_at DESC
    """).fetchall()

    return render_template('index.html', networks=[dict(n) for n in networks])


@bp.route('/workspace/<int:network_id>')
def workspace(network_id: int):
    """Main interactive network topology workspace and simulation lab."""
    db = get_db()
    network = db.execute("SELECT * FROM networks WHERE id = ?", (network_id,)).fetchone()
    if not network:
        flash("Network project not found.", "danger")
        return redirect(url_for('views.welcome'))

    # Evaluate any live conflicts so the workspace opens in sync
    detect_and_update_conflicts(db, network_id)

    return render_template('workspace.html', network=dict(network))


@bp.route('/history/<int:network_id>')
def history(network_id: int):
    """Full-page event log and alert history for a specific network."""
    db = get_db()
    network = db.execute("SELECT * FROM networks WHERE id = ?", (network_id,)).fetchone()
    if not network:
        flash("Network project not found.", "danger")
        return redirect(url_for('views.welcome'))

    events = db.execute("""
        SELECT * FROM simulation_events 
        WHERE network_id = ? 
        ORDER BY id DESC
    """, (network_id,)).fetchall()

    alerts = db.execute("""
        SELECT * FROM alerts 
        WHERE network_id = ? 
        ORDER BY id DESC
    """, (network_id,)).fetchall()

    return render_template('history.html',
                           network=dict(network),
                           events=[dict(e) for e in events],
                           alerts=[dict(a) for a in alerts])


@bp.route('/scenario/load/<int:scenario_id>', methods=['POST'])
def load_scenario(scenario_id: int):
    """Helper route to load a preset scenario from the welcome screen."""
    db = get_db()
    net_id = load_example_scenario(db, scenario_id)
    flash(f"Loaded educational scenario {scenario_id} successfully!", "success")
    return redirect(url_for('views.workspace', network_id=net_id))
