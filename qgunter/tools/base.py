"""Framework de herramientas extensible (placeholder).

Actualmente Claude Code gestiona las herramientas directamente.
Este framework está preparado para futuras extensiones.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        pass


class TerminalTool(BaseTool):
    def __init__(self) -> None:
        super().__init__("terminal_execute", "Execute shell commands")

    async def execute(self, command: str = "", **kwargs: Any) -> dict[str, Any]:
        return {"success": True, "command": command, "result": "Executed via Claude Code"}