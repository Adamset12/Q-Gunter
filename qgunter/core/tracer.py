"""Tracer ligero para registrar actividad del agente."""

import threading
from collections.abc import Callable
from datetime import datetime
from typing import Any


class Tracer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._activities: list[dict[str, Any]] = []
        self._on_activity_callback: Callable[[dict[str, Any]], None] | None = None

    def set_activity_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        self._on_activity_callback = callback

    def track_message(self, message: str, message_type: str = "info") -> None:
        activity = {
            "type": "message", "message": message,
            "message_type": message_type, "timestamp": datetime.now(),
        }
        with self._lock:
            self._activities.append(activity)
        if self._on_activity_callback:
            self._on_activity_callback(activity)

    def track_tool_start(self, tool_name: str, args: dict[str, Any]) -> int:
        activity = {
            "type": "tool", "tool_name": tool_name, "args": args,
            "status": "running", "result": None, "timestamp": datetime.now(),
        }
        with self._lock:
            activity_id = len(self._activities)
            self._activities.append(activity)
        if self._on_activity_callback:
            self._on_activity_callback(activity)
        return activity_id

    def track_tool_complete(self, activity_id: int, result: Any = None, status: str = "completed") -> None:
        with self._lock:
            if 0 <= activity_id < len(self._activities):
                self._activities[activity_id]["status"] = status
                self._activities[activity_id]["result"] = result

    def track_agent_status(self, status: str, details: str | None = None) -> None:
        msg = f"Agent status: {status}" + (f" - {details}" if details else "")
        self.track_message(msg)

    def get_recent_activities(self, count: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return self._activities[-count:]

    def clear(self) -> None:
        with self._lock:
            self._activities.clear()


_global_tracer: Tracer | None = None
_tracer_lock = threading.Lock()


def get_global_tracer() -> Tracer:
    global _global_tracer
    if _global_tracer is None:
        with _tracer_lock:
            if _global_tracer is None:
                _global_tracer = Tracer()
    return _global_tracer