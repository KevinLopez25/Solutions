import pytest

from core import dependencies


class DummySession:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class DummySessionFactory:
    def __init__(self, session):
        self.session = session
        self.called = False

    def __call__(self):
        self.called = True
        return self.session


def test_get_db_yields_session_and_closes(monkeypatch):
    dummy = DummySession()
    factory = DummySessionFactory(dummy)
    monkeypatch.setattr(dependencies, 'SessionLocal', factory)

    generator = dependencies.get_db()
    session = next(generator)

    assert session is dummy
    assert factory.called

    with pytest.raises(StopIteration):
        next(generator)

    assert dummy.closed
