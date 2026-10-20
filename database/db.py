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
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Create all tables using schema.sql if they don't already exist."""
    db = get_db()
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r') as f:
        db.executescript(f.read())
    db.commit()


def init_db_command():
    """Flask CLI command: flask init-db"""
    init_db()
    click.echo('Database initialised.')


def init_app(app):
    """Register database teardown and CLI commands with the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(click.command('init-db')(init_db_command))
