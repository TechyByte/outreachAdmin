import pytest
from app import app, db
from init_db import initialise_database
from models import School, User, Program, TemplateCourse, TemplateEvent, TemplateAgendaItem


@pytest.fixture
def test_client():
    """Fixture to set up a test client and temporary database."""
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.session.remove()
            db.drop_all()

def test_initialize_database(test_client):
    """Test the database initialization process."""
    with app.app_context():
        initialise_database()

        assert School.query.count() > 0
        assert User.query.count() > 0
        assert Program.query.count() > 0
        assert TemplateCourse.query.count() > 0
        assert TemplateEvent.query.count() > 0
        assert TemplateAgendaItem.query.count() > 0
        assert TemplateCourse.query.count () > 0
        assert TemplateEvent.query.count() > 0
        assert User.query.filter_by(username='admin').first() is not None