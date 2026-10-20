"""
tests/conftest.py
Pytest fixtures for NodeScope tests.
Uses an in-memory SQLite database — no real network access required.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture()
def app():
    """Create a Flask test app with an in-memory SQLite database."""
    from app import create_app
    test_app = create_app({
        'TESTING': True,
        'DATABASE': ':memory:',
        'DEMO_MODE': False,
        'SECRET_KEY': 'test-secret',
    })
    yield test_app


@pytest.fixture()
def client(app):
    """Flask test client — DB is initialised inside the pushed context."""
    with app.app_context():
        from database.db import init_db
        init_db()
        yield app.test_client()


@pytest.fixture()
def app_ctx(app):
    """
    Active application context with a freshly initialised in-memory DB.
    Each test that uses this fixture gets a clean database.
    """
    with app.app_context():
        from database.db import init_db
        init_db()
        yield app
