"""routes/dashboard.py — Overview dashboard."""
from flask import Blueprint, render_template, current_app
from database.db import get_db
from services.device_registry import get_stats
from services.conflict_detection import get_active_conflict_count
from services.activity_history import get_active_alerts, get_events

bp = Blueprint('dashboard', __name__)


@bp.route('/')
def index():
    db = get_db()

    stats = get_stats()
    active_conflicts = get_active_conflict_count()

    # Latest scan
    latest_scan = db.execute(
        "SELECT * FROM scans ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    latest_scan = dict(latest_scan) if latest_scan else None

    recent_alerts = get_active_alerts(limit=5)
    recent_events = get_events(limit=5)

    return render_template(
        'dashboard.html',
        stats=stats,
        active_conflicts=active_conflicts,
        latest_scan=latest_scan,
        recent_alerts=recent_alerts,
        recent_events=recent_events,
        demo_mode=current_app.config.get('DEMO_MODE', False)
    )
