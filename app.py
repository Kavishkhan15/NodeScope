"""
app.py — NodeScope: Interactive LAN Simulator and Network Troubleshooting Lab

Usage:
    # Direct execution on Windows:
    python app.py

    # Or with Flask CLI:
    flask run
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
        SECRET_KEY=os.environ.get('NODESCOPE_SECRET', 'nodescope-simulator-dev-key-2026'),
        DATABASE=os.path.join(app.instance_path, 'nodescope.db'),
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

    # Register blueprints
    from routes.views import bp as views_bp
    from routes.api import api_bp

    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)

    # Register CLI commands for scenarios
    @app.cli.command('seed-scenarios')
    def seed_scenarios_command():
        """Pre-populate the database with all 5 educational scenarios."""
        with app.app_context():
            from database.db import get_db
            from simulator.scenarios import load_example_scenario
            db = get_db()
            for s_id in range(1, 6):
                load_example_scenario(db, s_id)
            click.echo('All 5 educational scenarios successfully seeded!')

    return app


# Root application instance for `python app.py` or WSGI servers
app = create_app()

if __name__ == '__main__':
    print("=================================================================")
    print("  NodeScope: Interactive LAN Simulator & Troubleshooting Lab")
    print("  Server running at: http://127.0.0.1:5000/")
    print("=================================================================")
    app.run(debug=True, host='127.0.0.1', port=5000)
