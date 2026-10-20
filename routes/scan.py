"""routes/scan.py — Network scan page."""
import datetime
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, current_app, jsonify)
from database.db import get_db
from services.discovery import validate_subnet, scan_subnet_arp, get_demo_observations, is_demo_mode
from services.device_registry import register_observation, check_unknown_devices
from services.conflict_detection import process_scan_conflicts

bp = Blueprint('scan', __name__, url_prefix='/scan')


def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + 'Z'


def _run_scan_pipeline(observations: list, subnet: str, scan_id: int,
                        is_demo: int = 0) -> dict:
    """
    Process a list of observations through the full pipeline:
    register devices → detect unknown → detect conflicts.
    Returns a summary dict.
    """
    new_devices = 0
    ip_changes = 0

    for obs in observations:
        result = register_observation(
            ip=obs['ip'], mac=obs['mac'],
            observed_at=obs['observed_at'],
            scan_id=scan_id, is_demo=is_demo
        )
        if result['is_new']:
            new_devices += 1
        if result['ip_changed']:
            ip_changes += 1

    # Insert observation rows
    db = get_db()
    for obs in observations:
        db.execute(
            """INSERT INTO device_observations
                   (scan_id, ip_address, mac_address, observed_at, is_demo)
               VALUES (?, ?, ?, ?, ?)""",
            (scan_id, obs['ip'], obs['mac'].upper(), obs['observed_at'], is_demo)
        )
    db.commit()

    unknown = check_unknown_devices(observations, is_demo)
    conflicts = process_scan_conflicts(observations, is_demo)

    return {
        'device_count': len(set(o['mac'] for o in observations)),
        'new_devices': new_devices,
        'ip_changes': ip_changes,
        'unknown_count': len(unknown),
        'conflicts_found': len(conflicts),
        'observations': observations,
        'unknown': unknown,
        'conflicts': conflicts,
    }


@bp.route('/', methods=['GET'])
def scan_page():
    return render_template(
        'scan.html',
        result=None,
        error=None,
        demo_mode=current_app.config.get('DEMO_MODE', False)
    )


@bp.route('/', methods=['POST'])
def run_scan():
    subnet = request.form.get('subnet', '').strip()

    # Validate
    ok, result = validate_subnet(subnet)
    if not ok:
        return render_template('scan.html', result=None, error=result,
                               demo_mode=current_app.config.get('DEMO_MODE', False))

    # Check authorisation checkbox
    if not request.form.get('authorised'):
        return render_template('scan.html', result=None,
                               error='You must confirm you are authorised to scan this network.',
                               demo_mode=current_app.config.get('DEMO_MODE', False))

    db = get_db()
    db.execute(
        "INSERT INTO scans (subnet, started_at, status) VALUES (?, ?, 'running')",
        (subnet, _now())
    )
    db.commit()
    scan_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Run ARP scan
    observations, error_message = scan_subnet_arp(subnet, scan_id)

    if error_message and not observations:
        db.execute(
            "UPDATE scans SET status='failed', completed_at=?, error_message=? WHERE id=?",
            (_now(), error_message, scan_id)
        )
        db.commit()
        return render_template('scan.html', result=None, error=error_message,
                               demo_mode=current_app.config.get('DEMO_MODE', False))

    summary = _run_scan_pipeline(observations, subnet, scan_id, is_demo=0)

    db.execute(
        """UPDATE scans SET status='completed', completed_at=?, device_count=?
           WHERE id=?""",
        (_now(), summary['device_count'], scan_id)
    )
    db.commit()

    if error_message:
        flash(f'Scan completed with a warning: {error_message}', 'warning')

    return render_template(
        'scan.html',
        result=summary,
        subnet=subnet,
        error=None,
        demo_mode=current_app.config.get('DEMO_MODE', False)
    )


@bp.route('/demo', methods=['POST'])
def demo_scan():
    """Load demo observations and run the full pipeline."""
    from demo.seed import seed_demo_data
    db = get_db()

    # Clear existing demo data first
    from demo.seed import reset_demo
    reset_demo()

    result = seed_demo_data()

    if 'message' in result and 'already' in result.get('message', ''):
        flash('Demo data loaded.', 'info')
    else:
        flash('Demo data seeded successfully.', 'success')

    return redirect(url_for('dashboard.index'))
