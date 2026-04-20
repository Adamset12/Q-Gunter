from pathlib import Path
import pytest
from qgunter.core.backend import AgentMessage, MessageType
from qgunter.core.config import QGunterConfig
from qgunter.core.controller import AgentController, AgentState
from qgunter.core.session import SessionStore
from tests.conftest import MockBackend


@pytest.mark.integration
class TestController:
    @pytest.fixture
    def controller(self, temp_working_dir: Path, mock_backend: MockBackend, temp_sessions_dir: Path):
        config = QGunterConfig(target="test.example.com", working_directory=temp_working_dir)
        sessions = SessionStore(sessions_dir=temp_sessions_dir)
        return AgentController(config=config, backend=mock_backend, session_store=sessions)

    def test_initial_state(self, controller: AgentController):
        assert controller.state == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_run_success(self, controller: AgentController, mock_backend: MockBackend):
        mock_backend.set_messages([
            AgentMessage(type=MessageType.TEXT, content="Found flag{test123}!"),
            AgentMessage(type=MessageType.RESULT, content=None, metadata={"cost_usd": 0.5}),
        ])
        result = await controller.run("Test task")
        assert result["success"] is True
        assert "flag{test123}" in result["flags_found"]

    @pytest.mark.asyncio
    async def test_multiple_flags(self, controller: AgentController, mock_backend: MockBackend):
        mock_backend.set_messages([
            AgentMessage(type=MessageType.TEXT, content="flag{abc}"),
            AgentMessage(type=MessageType.TEXT, content="HTB{xyz}"),
            AgentMessage(type=MessageType.RESULT, content=None, metadata={}),
        ])
        result = await controller.run("Find flags")
        assert "flag{abc}" in result["flags_found"]
        assert "HTB{xyz}" in result["flags_found"]

    @pytest.mark.asyncio
    async def test_session_not_found(self, controller: AgentController):
        result = await controller.run("Task", resume_session_id="nonexistent")
        assert result["success"] is False

    def test_pause_wrong_state(self, controller: AgentController):
        assert controller.pause() is False  # Can't pause when IDLE