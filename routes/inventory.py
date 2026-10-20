"""routes/inventory.py — Device inventory and approval."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from services.device_registry import get_all_devices, approve_device, get_device_by_mac

bp = Blueprint('inventory', __name__, url_prefix='/inventory')


@bp.route('/')
def list_devices():
    search = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'last_seen')

    devices = get_all_devices(search=search or None)

    # Sort in Python (simple, avoids SQL injection risks)
    valid_sorts = {'mac_address', 'ip_address', 'friendly_name', 'last_seen', 'first_seen', 'approved'}
    if sort not in valid_sorts:
        sort = 'last_seen'

    reverse = sort in ('last_seen', 'first_seen')
    try:
        devices.sort(key=lambda d: (d.get(sort) or ''), reverse=reverse)
    except Exception:
        pass

    return render_template(
        'inventory.html',
        devices=devices,
        search=search,
        sort=sort,
        demo_mode=current_app.config.get('DEMO_MODE', False)
    )


@bp.route('/approve', methods=['POST'])
def approve():
    mac = request.form.get('mac', '').strip()
    friendly_name = request.form.get('friendly_name', '').strip() or None
    notes = request.form.get('notes', '').strip() or None

    if not mac:
        flash('MAC address is required.', 'danger')
        return redirect(url_for('inventory.list_devices'))

    # Basic MAC format validation
    mac_clean = mac.replace(':', '').replace('-', '').upper()
    if len(mac_clean) != 12 or not all(c in '0123456789ABCDEF' for c in mac_clean):
        flash(f'Invalid MAC address format: {mac}', 'danger')
        return redirect(url_for('inventory.list_devices'))

    # Normalise to colon-separated
    mac_norm = ':'.join(mac_clean[i:i+2] for i in range(0, 12, 2))
    result = approve_device(mac_norm, friendly_name, notes)

    if result:
        label = friendly_name or mac_norm
        flash(f'Device "{label}" has been approved.', 'success')
    else:
        flash(f'Device with MAC {mac_norm} not found in the database.', 'warning')

    return redirect(url_for('inventory.list_devices'))


@bp.route('/device/<mac>')
def device_detail(mac):
    device = get_device_by_mac(mac)
    if not device:
        flash(f'Device {mac} not found.', 'warning')
        return redirect(url_for('inventory.list_devices'))

    from database.db import get_db
    db = get_db()

    # Recent observations for this device
    observations = db.execute(
        """SELECT o.*, s.subnet FROM device_observations o
           JOIN scans s ON o.scan_id = s.id
           WHERE o.mac_address = ?
           ORDER BY o.observed_at DESC LIMIT 20""",
        (mac.upper(),)
    ).fetchall()

    # Active alerts for this device
    alerts = db.execute(
        "SELECT * FROM alerts WHERE device_mac = ? ORDER BY created_at DESC LIMIT 10",
        (mac.upper(),)
    ).fetchall()

    return render_template(
        'device_detail.html',
        device=device,
        observations=[dict(o) for o in observations],
        alerts=[dict(a) for a in alerts],
        demo_mode=current_app.config.get('DEMO_MODE', False)
    )
