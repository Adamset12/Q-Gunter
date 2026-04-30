"""Backend abstracto + implementación para Claude Code con MCP remoto."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MessageType(Enum):
    TEXT = "text"
    TOOL_START = "tool_start"
    TOOL_RESULT = "tool_result"
    RESULT = "result"
    ERROR = "error"


@dataclass
class AgentMessage:
    type: MessageType
    content: Any
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentBackend(ABC):
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


class MCPRemoteBackend(AgentBackend):
    """
    Backend para Claude Code SDK con herramientas MCP redirigidas a Manos.

    Claude Code se ejecuta en Cerebro (con claude login) pero todas las
    herramientas (bash, read_file, write_file) se ejecutan en Manos
    a través del MCP Server HTTP/SSE que corre allí.
    """

    def __init__(
        self,
        working_directory: str,
        system_prompt: str,
        model: str,
        manos_url: str,
        manos_token: str,
        permission_mode: str = "bypassPermissions",
    ) -> None:
        self._cwd = working_directory
        self._system_prompt = system_prompt
        self._model = model
        self._manos_url = manos_url
        self._manos_token = manos_token
        self._permission_mode = permission_mode
        self._client: Any = None
        self._session_id: str | None = None

    def _mcp_servers(self) -> dict[str, Any]:
        return {
            "manos": {
                "type": "sse",
                "url": f"{self._manos_url}/sse",
                "headers": {
                    "Authorization": f"Bearer {self._manos_token}",
                },
            }
        }

    async def connect(self) -> None:
        import os
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

        env_overrides: dict[str, str] = {}
        if os.environ.get("ANTHROPIC_API_KEY"):
            env_overrides["ANTHROPIC_API_KEY"] = ""

        options = ClaudeAgentOptions(
            cwd=self._cwd,
            permission_mode=self._permission_mode,
            system_prompt=self._system_prompt,
            model=self._model,
            mcp_servers=self._mcp_servers(),
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
            raise RuntimeError("Backend no conectado")
        result = self._client.query(prompt)
        if result is not None:
            await result

    async def receive_messages(self) -> AsyncIterator[AgentMessage]:
        from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

        if not self._client:
            raise RuntimeError("Backend no conectado")

        async for msg in self._client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        yield AgentMessage(type=MessageType.TEXT, content=block.text)
                    elif isinstance(block, ToolUseBlock):
                        yield AgentMessage(
                            type=MessageType.TOOL_START,
                            content=None,
                            tool_name=block.name,
                            tool_args=block.input,
                        )
            elif isinstance(msg, ResultMessage):
                yield AgentMessage(
                    type=MessageType.RESULT,
                    content=None,
                    metadata={"cost_usd": getattr(msg, "total_cost_usd", 0)},
                )

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @property
    def supports_resume(self) -> bool:
        return True

    async def resume(self, session_id: str) -> bool:
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
            permission_mode=self._permission_mode,
            system_prompt=self._system_prompt,
            model=self._model,
            mcp_servers=self._mcp_servers(),
            resume=session_id,
            env=env_overrides,
        )
        self._client = ClaudeSDKClient(options=options)
        result = self._client.connect()
        if result is not None:
            await result
        self._session_id = session_id
        return True
