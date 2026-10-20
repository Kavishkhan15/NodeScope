"""routes/history.py — Activity history and alert management."""
from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, current_app)
from services.activity_history import (
    get_events, get_all_alerts, acknowledge_alert, dismiss_alert
)

bp = Blueprint('history', __name__)


@bp.route('/history')
def history():
    event_type = request.args.get('type', '').strip() or None
    events = get_events(event_type_filter=event_type, limit=100)

    event_types = [
        'device_discovered', 'device_not_seen', 'ip_changed',
        'conflict_detected', 'conflict_resolved', 'device_approved', 'alert_created'
    ]

    return render_template(
        'history.html',
        events=events,
        event_type_filter=event_type or 'all',
        event_types=event_types,
        demo_mode=current_app.config.get('DEMO_MODE', False)
    )


@bp.route('/alerts')
def alerts():
    all_alerts = get_all_alerts(limit=100)
    return render_template(
        'alerts.html',
        alerts=all_alerts,
        demo_mode=current_app.config.get('DEMO_MODE', False)
    )


@bp.route('/alerts/<int:alert_id>/acknowledge', methods=['POST'])
def acknowledge(alert_id):
    notes = request.form.get('notes', '').strip() or None
    acknowledge_alert(alert_id, notes)
    flash('Alert acknowledged.', 'success')
    return redirect(url_for('history.alerts'))


@bp.route('/alerts/<int:alert_id>/dismiss', methods=['POST'])
def dismiss(alert_id):
    notes = request.form.get('notes', '').strip() or None
    dismiss_alert(alert_id, notes)
    flash('Alert dismissed.', 'success')
    return redirect(url_for('history.alerts'))
