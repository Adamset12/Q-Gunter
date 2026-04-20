"""Fixtures compartidos para tests de Q-Gunter."""

import tempfile
from pathlib import Path

import pytest

from qgunter.core.backend import AgentBackend, AgentMessage, MessageType
from qgunter.core.config import QGunterConfig
from qgunter.core.events import EventBus


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")


@pytest.fixture(autouse=True)
def reset_event_bus():
    """Resetea el EventBus entre tests para evitar interferencias."""
    EventBus.reset()
    yield
    EventBus.reset()


@pytest.fixture
def temp_sessions_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_working_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config(temp_working_dir: Path) -> QGunterConfig:
    return QGunterConfig(target="test.example.com", working_directory=temp_working_dir)


class MockBackend(AgentBackend):
    """Backend falso para tests. Devuelve mensajes predefinidos sin llamar a Claude."""

    def __init__(self) -> None:
        self._connected = False
        self._messages: list[AgentMessage] = []
        self._session_id = "mock-session-123"

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def query(self, prompt: str) -> None:
        pass

    async def receive_messages(self):
        for msg in self._messages:
            yield msg

    @property
    def session_id(self) -> str:
        return self._session_id

    async def resume(self, session_id: str) -> bool:
        return False

    def set_messages(self, messages: list[AgentMessage]) -> None:
        self._messages = messages


@pytest.fixture
def mock_backend() -> MockBackend:
    return MockBackend()
