"""
database/db.py
SQLite connection helpers for NodeScope.
Uses Flask's g object for per-request connection pooling.
"""
import sqlite3
import os
import click
from flask import current_app, g


def get_db():
    """Return the database connection for the current request context."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row  # rows behave like dicts
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")  # better concurrent reads
    return g.db


def close_db(e=None):
    """Close the database connection at end of request."""
    try:
        db = g.pop('db', None)
        if db is not None:
            db.close()
    except Exception:
        pass


def init_db():
    """Create all tables using schema.sql if they don't already exist."""
    db = get_db()
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r') as f:
        db.executescript(f.read())

    # Schema migration helper for existing databases: ensure cost and delay_ms columns exist
    try:
        cols = [r['name'] for r in db.execute("PRAGMA table_info(connections)").fetchall()]
        if 'cost' not in cols:
            db.execute("ALTER TABLE connections ADD COLUMN cost INTEGER NOT NULL DEFAULT 1")
        if 'delay_ms' not in cols:
            db.execute("ALTER TABLE connections ADD COLUMN delay_ms INTEGER NOT NULL DEFAULT 2")
    except Exception:
        pass

    db.commit()


def init_db_command():
    """Flask CLI command: flask init-db"""
    init_db()
    click.echo('Database initialised.')


def init_app(app):
    """Register database teardown and CLI commands with the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(click.command('init-db')(init_db_command))
