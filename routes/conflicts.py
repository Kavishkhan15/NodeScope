"""routes/conflicts.py — IP conflict management and guided resolution."""
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, current_app)
from services.conflict_detection import (
    get_all_conflicts, get_conflict_by_id, update_conflict_status
)
from services.resolution import (
    suggest_resolution, record_resolution_attempt, verify_resolution
)

bp = Blueprint('conflicts', __name__, url_prefix='/conflicts')


@bp.route('/')
def list_conflicts():
    status_filter = request.args.get('status', '').strip() or None
    conflicts = get_all_conflicts(status_filter=status_filter)
    return render_template(
        'conflicts.html',
        conflicts=conflicts,
        status_filter=status_filter or 'all',
        demo_mode=current_app.config.get('DEMO_MODE', False)
    )


@bp.route('/<int:conflict_id>')
def conflict_detail(conflict_id):
    conflict = get_conflict_by_id(conflict_id)
    if not conflict:
        flash('Conflict not found.', 'warning')
        return redirect(url_for('conflicts.list_conflicts'))

    suggestion = suggest_resolution(conflict_id)

    return render_template(
        'conflict_detail.html',
        conflict=conflict,
        suggestion=suggestion,
        demo_mode=current_app.config.get('DEMO_MODE', False)
    )


@bp.route('/<int:conflict_id>/investigate', methods=['POST'])
def investigate(conflict_id):
    notes = request.form.get('notes', '').strip() or None
    if not notes:
        flash('Please provide investigation notes before marking as under investigation.', 'warning')
        return redirect(url_for('conflicts.conflict_detail', conflict_id=conflict_id))

    update_conflict_status(conflict_id, 'under_investigation', notes)
    flash('Conflict status updated to Under Investigation.', 'info')
    return redirect(url_for('conflicts.conflict_detail', conflict_id=conflict_id))


@bp.route('/<int:conflict_id>/resolve', methods=['POST'])
def resolve(conflict_id):
    recommended_ip = request.form.get('recommended_ip', '').strip() or None
    action_taken = request.form.get('action_taken', '').strip()
    admin_notes = request.form.get('admin_notes', '').strip() or None

    if not action_taken:
        flash('Please describe the action taken before recording a resolution attempt.', 'warning')
        return redirect(url_for('conflicts.conflict_detail', conflict_id=conflict_id))

    record_resolution_attempt(conflict_id, recommended_ip, action_taken, admin_notes)
    flash('Resolution attempt recorded. Run a follow-up scan then click Verify Resolution.', 'success')
    return redirect(url_for('conflicts.conflict_detail', conflict_id=conflict_id))


@bp.route('/<int:conflict_id>/verify', methods=['POST'])
def verify(conflict_id):
    still_present_raw = request.form.get('still_present', 'yes')
    still_present = still_present_raw.lower() == 'yes'
    admin_notes = request.form.get('admin_notes', '').strip() or None

    verify_resolution(conflict_id, still_present, admin_notes)

    if still_present:
        flash('Conflict still observed — marked as Under Investigation. Continue investigating.', 'warning')
    else:
        flash('Conflict resolved and verified. Case closed.', 'success')

    return redirect(url_for('conflicts.conflict_detail', conflict_id=conflict_id))
