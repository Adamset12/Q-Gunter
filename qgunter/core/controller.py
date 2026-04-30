"""Controlador del agente — modo distribuido.

CAMBIOS RESPECTO AL ORIGINAL:
- En run(): instancia MCPRemoteBackend en lugar de ClaudeCodeBackend
- El resto de la lógica (estados, pausa, flags, sesiones) es idéntica
"""

import asyncio
import re
from enum import Enum
from typing import Any, ClassVar

from qgunter.core.backend import AgentBackend, AgentMessage, MCPRemoteBackend, MessageType
from qgunter.core.config import QGunterConfig
from qgunter.core.events import Event, EventBus, EventType
from qgunter.core.session import SessionStatus, SessionStore


class AgentState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class AgentController:
    FLAG_PATTERNS: ClassVar[list[str]] = [
        r"flag\{[^\}]+\}",
        r"FLAG\{[^\}]+\}",
        r"HTB\{[^\}]+\}",
        r"CTF\{[^\}]+\}",
        r"[A-Za-z0-9_]+\{[^\}]+\}",
        r"\b[a-f0-9]{32}\b",
    ]

    def __init__(
        self,
        config: QGunterConfig,
        backend: AgentBackend | None = None,
        session_store: SessionStore | None = None,
        events: EventBus | None = None,
    ) -> None:
        self.config = config
        self.backend = backend
        self.sessions = session_store or SessionStore()
        self.events = events or EventBus.get()

        self._state = AgentState.IDLE
        self._pause_requested = False
        self._stop_requested = False
        self._resume_event = asyncio.Event()
        self._pending_instruction: str | None = None

        self.events.subscribe(EventType.USER_COMMAND, self._on_user_command)
        self.events.subscribe(EventType.USER_INPUT, self._on_user_input)

    @property
    def state(self) -> AgentState:
        return self._state

    def _set_state(self, state: AgentState, details: str = "") -> None:
        self._state = state
        self.events.emit_state(state.value, details)

    def pause(self) -> bool:
        if self._state == AgentState.RUNNING:
            self._pause_requested = True
            return True
        return False

    def resume(self, instruction: str | None = None) -> bool:
        if self._state == AgentState.PAUSED:
            self._pending_instruction = instruction
            self._pause_requested = False
            self._resume_event.set()
            return True
        return False

    def stop(self) -> bool:
        self._stop_requested = True
        self._resume_event.set()
        return True

    def inject(self, instruction: str) -> bool:
        if self._state in (AgentState.RUNNING, AgentState.PAUSED):
            self._pending_instruction = instruction
            if self._state == AgentState.RUNNING:
                self._pause_requested = True
            return True
        return False

    def _on_user_command(self, event: Event) -> None:
        cmd = event.data.get("command")
        if cmd == "pause":
            self.pause()
        elif cmd == "resume":
            self.resume()
        elif cmd == "stop":
            self.stop()

    def _on_user_input(self, event: Event) -> None:
        text = event.data.get("text", "")
        if text:
            self.inject(text)

    async def run(self, task: str, resume_session_id: str | None = None) -> dict[str, Any]:
        self._pause_requested = False
        self._stop_requested = False
        self._resume_event.clear()

        if resume_session_id:
            session = self.sessions.load(resume_session_id)
            if not session:
                return {"success": False, "error": f"Session {resume_session_id} not found"}
            if not task:
                task = session.task
        else:
            session = self.sessions.create(
                target=self.config.target,
                task=task,
                model=self.config.llm_model,
            )

        # ── CAMBIO PRINCIPAL ──────────────────────────────────────────────────
        # Antes: ClaudeCodeBackend (ejecuta herramientas localmente)
        # Ahora: MCPRemoteBackend  (redirige herramientas a Manos via HTTP/MCP)
        if self.backend is None:
            from qgunter.prompts.pentesting import get_system_prompt
            self.backend = MCPRemoteBackend(
                working_directory=str(self.config.working_directory),
                system_prompt=get_system_prompt(self.config.custom_instruction),
                model=self.config.llm_model,
                manos_url=self.config.manos_url,
                manos_token=self.config.manos_token,
            )
        # ─────────────────────────────────────────────────────────────────────

        try:
            self._set_state(AgentState.RUNNING, "Connecting...")

            if resume_session_id and self.backend.supports_resume:
                backend_session = session.backend_session_id or resume_session_id
                await self.backend.resume(backend_session)
                self.events.emit_message(f"Resumed session {resume_session_id}", "info")
            else:
                await self.backend.connect()

            if self.backend.session_id:
                self.sessions.set_backend_session_id(self.backend.session_id)

            await self.backend.query(task)
            self.sessions.update_status(SessionStatus.RUNNING)

            output_parts: list[str] = []
            flags_found: list[str] = []

            async for msg in self.backend.receive_messages():
                if self._stop_requested:
                    self._set_state(AgentState.IDLE, "Stopped by user")
                    self.sessions.update_status(SessionStatus.PAUSED)
                    break

                if self._pause_requested:
                    self._pause_requested = False
                    self._set_state(AgentState.PAUSED, "Paused — waiting for input")
                    self.sessions.update_status(SessionStatus.PAUSED)
                    await self._resume_event.wait()
                    self._resume_event.clear()
                    if self._stop_requested:
                        break
                    self._set_state(AgentState.RUNNING, "Resumed")
                    self.sessions.update_status(SessionStatus.RUNNING)
                    if self._pending_instruction:
                        self.sessions.add_instruction(self._pending_instruction)
                        await self.backend.query(self._pending_instruction)
                        self._pending_instruction = None

                await self._process_message(msg, output_parts, flags_found)

            if not self._stop_requested:
                self._set_state(AgentState.COMPLETED)
                self.sessions.update_status(SessionStatus.COMPLETED)

            return {
                "success": True,
                "output": "\n".join(output_parts),
                "flags_found": flags_found,
                "session_id": session.session_id,
                "cost_usd": session.total_cost_usd,
            }

        except Exception as e:
            self._set_state(AgentState.ERROR, str(e))
            self.sessions.set_error(str(e))
            self.sessions.update_status(SessionStatus.ERROR)
            return {"success": False, "error": str(e)}

        finally:
            if self.backend:
                await self.backend.disconnect()

    async def _process_message(
        self,
        msg: AgentMessage,
        output_parts: list[str],
        flags_found: list[str],
    ) -> None:
        if msg.type == MessageType.TEXT:
            output_parts.append(msg.content)
            self.events.emit_message(msg.content)
            for flag in self._detect_flags(msg.content):
                if flag not in flags_found:
                    flags_found.append(flag)
                    self.sessions.add_flag(flag, msg.content[:200])
                    self.events.emit_flag(flag, msg.content[:200])

        elif msg.type == MessageType.TOOL_START:
            self.events.emit_tool(
                status="start",
                name=msg.tool_name or "unknown",
                args=msg.tool_args,
            )

        elif msg.type == MessageType.TOOL_RESULT:
            self.events.emit_tool(
                status="complete",
                name=msg.tool_name or "unknown",
                result=msg.content,
            )

        elif msg.type == MessageType.RESULT:
            cost = msg.metadata.get("cost_usd", 0)
            if cost > 0:
                self.sessions.add_cost(cost)

    def _detect_flags(self, text: str) -> list[str]:
        flags = []
        for pattern in self.FLAG_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                flag = match.group(0)
                if flag not in flags:
                    flags.append(flag)
        return flags
