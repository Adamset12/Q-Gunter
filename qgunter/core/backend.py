"""Backend abstracto + implementación para Claude Code Subscription.

La clase abstracta AgentBackend define QUÉ métodos debe tener cualquier backend.
ClaudeCodeBackend es la implementación concreta para Claude Code CLI.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MessageType(Enum):
    """Tipos de mensaje que el backend puede producir."""
    TEXT = "text"
    TOOL_START = "tool_start"
    TOOL_RESULT = "tool_result"
    RESULT = "result"
    ERROR = "error"


@dataclass
class AgentMessage:
    """Mensaje genérico del backend (independiente del framework)."""
    type: MessageType
    content: Any
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentBackend(ABC):
    """Interfaz abstracta. Cualquier backend (Claude, OpenAI, etc.) debe implementarla."""

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def query(self, prompt: str) -> None: ...

    @abstractmethod
    def receive_messages(self) -> AsyncIterator[AgentMessage]: ...

    @property
    @abstractmethod
    def session_id(self) -> str | None: ...

    @property
    def supports_resume(self) -> bool:
        return False

    @abstractmethod
    async def resume(self, session_id: str) -> bool: ...


class ClaudeCodeBackend(AgentBackend):
    """Implementación para Claude Code Subscription (claude login)."""

    def __init__(self, working_directory: str, system_prompt: str, model: str,
                 permission_mode: str = "bypassPermissions"):
        self._cwd = working_directory
        self._system_prompt = system_prompt
        self._model = model
        self._permission_mode = permission_mode
        self._client: Any = None
        self._session_id: str | None = None

    async def connect(self) -> None:
        """Conecta con Claude Code CLI usando el token OAuth de 'claude login'."""
        import os
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

        env_overrides: dict[str, str] = {}
        # Limpiar API key para que use OAuth (el token de claude login)
        if os.environ.get("ANTHROPIC_API_KEY"):
            env_overrides["ANTHROPIC_API_KEY"] = ""

        options = ClaudeAgentOptions(
            cwd=self._cwd,
            permission_mode=self._permission_mode,  # type: ignore[arg-type]
            system_prompt=self._system_prompt,
            model=self._model,
            env=env_overrides,
        )
        self._client = ClaudeSDKClient(options=options)
        result = self._client.connect()
        if result is not None:
            await result

    async def disconnect(self) -> None:
        if self._client:
            result = self._client.disconnect()
            if result is not None:
                await result
            self._client = None

    async def query(self, prompt: str) -> None:
        if not self._client:
            raise RuntimeError("Backend not connected")
        result = self._client.query(prompt)
        if result is not None:
            await result

    async def receive_messages(self) -> AsyncIterator[AgentMessage]:
        """Convierte mensajes del SDK de Claude a nuestro formato genérico."""
        from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

        if not self._client:
            raise RuntimeError("Backend not connected")

        async for msg in self._client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        yield AgentMessage(type=MessageType.TEXT, content=block.text)
                    elif isinstance(block, ToolUseBlock):
                        yield AgentMessage(
                            type=MessageType.TOOL_START, content=None,
                            tool_name=block.name, tool_args=block.input,
                        )
            elif isinstance(msg, ResultMessage):
                yield AgentMessage(
                    type=MessageType.RESULT, content=None,
                    metadata={"cost_usd": getattr(msg, "total_cost_usd", 0)},
                )

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @property
    def supports_resume(self) -> bool:
        return True

    async def resume(self, session_id: str) -> bool:
        """Reanuda una sesión anterior de Claude Code."""
        import os
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

        if self._client:
            result = self._client.disconnect()
            if result is not None:
                await result

        env_overrides: dict[str, str] = {}
        if os.environ.get("ANTHROPIC_API_KEY"):
            env_overrides["ANTHROPIC_API_KEY"] = ""

        options = ClaudeAgentOptions(
            cwd=self._cwd,
            permission_mode=self._permission_mode,  # type: ignore[arg-type]
            system_prompt=self._system_prompt,
            model=self._model,
            resume=session_id,
            env=env_overrides,
        )
        self._client = ClaudeSDKClient(options=options)
        result = self._client.connect()
        if result is not None:
            await result
        self._session_id = session_id
        return True