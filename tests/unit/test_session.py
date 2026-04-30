"""Tests para SessionStore — fichero estaba vacío, ahora completo."""

from pathlib import Path
import pytest
from qgunter.core.session import SessionStatus, SessionStore


@pytest.mark.unit
class TestSessionStore:
    def test_create_session(self, temp_sessions_dir: Path) -> None:
        store = SessionStore(sessions_dir=temp_sessions_dir)
        session = store.create(target="test.example.com", task="test task", model="claude-haiku")
        assert session.session_id is not None
        assert session.target == "test.example.com"
        assert session.status == SessionStatus.RUNNING

    def test_save_and_load(self, temp_sessions_dir: Path) -> None:
        store = SessionStore(sessions_dir=temp_sessions_dir)
        session = store.create(target="test.example.com", task="task", model="model")
        loaded = store.load(session.session_id)
        assert loaded is not None
        assert loaded.target == "test.example.com"

    def test_load_nonexistent(self, temp_sessions_dir: Path) -> None:
        store = SessionStore(sessions_dir=temp_sessions_dir)
        result = store.load("nonexistent")
        assert result is None

    def test_add_flag(self, temp_sessions_dir: Path) -> None:
        store = SessionStore(sessions_dir=temp_sessions_dir)
        store.create(target="t", task="t", model="m")
        store.add_flag("flag{test}", "contexto")
        assert store.current is not None
        assert len(store.current.flags_found) == 1
        assert store.current.flags_found[0]["flag"] == "flag{test}"

    def test_update_status(self, temp_sessions_dir: Path) -> None:
        store = SessionStore(sessions_dir=temp_sessions_dir)
        store.create(target="t", task="t", model="m")
        store.update_status(SessionStatus.COMPLETED)
        assert store.current is not None
        assert store.current.status == SessionStatus.COMPLETED

    def test_add_cost(self, temp_sessions_dir: Path) -> None:
        store = SessionStore(sessions_dir=temp_sessions_dir)
        store.create(target="t", task="t", model="m")
        store.add_cost(0.05)
        store.add_cost(0.03)
        assert store.current is not None
        assert abs(store.current.total_cost_usd - 0.08) < 0.001

    def test_list_sessions(self, temp_sessions_dir: Path) -> None:
        store = SessionStore(sessions_dir=temp_sessions_dir)
        store.create(target="target-a", task="t", model="m")
        store.create(target="target-b", task="t", model="m")
        sessions = store.list_sessions()
        assert len(sessions) == 2

    def test_delete_session(self, temp_sessions_dir: Path) -> None:
        store = SessionStore(sessions_dir=temp_sessions_dir)
        session = store.create(target="t", task="t", model="m")
        sid = session.session_id
        assert store.delete(sid) is True
        assert store.load(sid) is None
