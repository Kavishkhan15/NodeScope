"""
app.py — NodeScope Flask application entry point.

NodeScope: Smart LAN Monitoring, Rogue Device Detection
          and IP Conflict Resolution Assistance System

Usage:
    # Normal mode
    flask run

    # Demo mode (no network permissions required)
    $env:NODESCOPE_DEMO="1"; flask run

    # Or in one line on Windows PowerShell:
    $env:FLASK_APP="app"; $env:NODESCOPE_DEMO="1"; flask run
"""
import os
import click
from flask import Flask
from database.db import init_db, init_app as db_init_app


def create_app(test_config: dict | None = None) -> Flask:
    """Application factory. Pass test_config dict to override settings in tests."""
    app = Flask(__name__, instance_relative_config=True)

    # Default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('NODESCOPE_SECRET', 'dev-secret-change-in-prod'),
        DATABASE=os.path.join(app.instance_path, 'nodescope.db'),
        DEMO_MODE=os.environ.get('NODESCOPE_DEMO', '0') == '1',
    )

    if test_config is not None:
        app.config.update(test_config)

    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Register database helpers and CLI commands
    db_init_app(app)

    # Initialise DB tables on startup
    with app.app_context():
        init_db()

    # ----------------------------------------------------------------
    # Jinja2 helpers available in all templates
    # ----------------------------------------------------------------
    def event_type_badge(event_type: str) -> str:
        """Return a Bootstrap badge class for an activity event type."""
        mapping = {
            'device_discovered': 'bg-primary',
            'device_not_seen':   'bg-secondary',
            'ip_changed':        'bg-warning text-dark',
            'conflict_detected': 'ns-badge-conflict',
            'conflict_resolved': 'ns-badge-approved',
            'device_approved':   'ns-badge-approved',
            'alert_created':     'bg-info text-dark',
        }
        return mapping.get(event_type, 'bg-secondary')

    app.jinja_env.globals['event_type_badge'] = event_type_badge

    # Register blueprints
    from routes.dashboard import bp as dashboard_bp
    from routes.inventory import bp as inventory_bp
    from routes.scan import bp as scan_bp
    from routes.conflicts import bp as conflicts_bp
    from routes.history import bp as history_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(scan_bp)
    app.register_blueprint(conflicts_bp)
    app.register_blueprint(history_bp)

    # Register demo CLI commands
    @app.cli.command('seed-demo')
    def seed_demo_command():
        """Seed the database with demo data."""
        with app.app_context():
            from demo.seed import seed_demo_data
            counts = seed_demo_data()
            if 'message' in counts:
                click.echo(counts['message'])
            else:
                click.echo(f'Demo data seeded: {counts}')

    @app.cli.command('reset-demo')
    def reset_demo_command():
        """Delete all demo records from the database."""
        with app.app_context():
            from demo.seed import reset_demo
            counts = reset_demo()
            click.echo(f'Demo data removed: {counts}')

    return app


# Allow `flask run` and `python app.py` both to work
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
