"""Event bus para comunicación desacoplada entre componentes.

Patrón Pub/Sub: unos componentes "publican" eventos y otros se "suscriben"
para recibirlos. Así el CLI no necesita conocer directamente al agente
y viceversa.
"""

import contextlib
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Optional


class EventType(Enum):
    """Tipos de eventos disponibles."""

    # Agente → Interfaz
    STATE_CHANGED = auto()  # El agente cambió de estado (idle, running, etc.)
    MESSAGE = auto()        # El agente generó texto
    TOOL = auto()           # El agente usó una herramienta (bash, etc.)
    FLAG_FOUND = auto()     # Se detectó una bandera

    # Interfaz → Agente
    USER_COMMAND = auto()   # Comando del usuario (pause, resume, stop)
    USER_INPUT = auto()     # Texto del usuario (instrucciones)


@dataclass
class Event:
    """Contenedor de evento con tipo, datos y timestamp."""

    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class EventBus:
    """Bus de eventos thread-safe con patrón Singleton.

    Singleton significa que solo existe UNA instancia en toda la aplicación.
    Se accede con EventBus.get() desde cualquier parte del código.
    """

    _instance: Optional["EventBus"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[Callable[[Event], None]]] = {}
        self._handler_lock = threading.Lock()

    @classmethod
    def get(cls) -> "EventBus":
        """Obtiene la única instancia del EventBus."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Resetea la instancia (útil para tests)."""
        with cls._lock:
            cls._instance = None

    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """Suscribe una función a un tipo de evento.

        Cada vez que se emita un evento de ese tipo, se llamará a la función.
        """
        with self._handler_lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            if handler not in self._handlers[event_type]:
                self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """Desuscribe una función de un tipo de evento."""
        with self._handler_lock:
            if event_type in self._handlers:
                with contextlib.suppress(ValueError):
                    self._handlers[event_type].remove(handler)

    def emit(self, event: Event) -> None:
        """Emite un evento a todos los suscriptores.

        Si un handler falla, los demás siguen ejecutándose (no rompe la cadena).
        """
        with self._handler_lock:
            handlers = self._handlers.get(event.type, []).copy()

        for handler in handlers:
            with contextlib.suppress(Exception):
                handler(event)

    # === Métodos de conveniencia (para no crear objetos Event manualmente) ===

    def emit_state(self, state: str, details: str = "") -> None:
        self.emit(Event(EventType.STATE_CHANGED, {"state": state, "details": details}))

    def emit_message(self, text: str, msg_type: str = "info") -> None:
        self.emit(Event(EventType.MESSAGE, {"text": text, "type": msg_type}))

    def emit_tool(
        self, status: str, name: str,
        args: dict[str, Any] | None = None, result: Any | None = None,
    ) -> None:
        self.emit(Event(EventType.TOOL, {
            "status": status, "name": name, "args": args or {}, "result": result,
        }))

    def emit_flag(self, flag: str, context: str = "") -> None:
        self.emit(Event(EventType.FLAG_FOUND, {"flag": flag, "context": context}))

    def emit_command(self, command: str) -> None:
        self.emit(Event(EventType.USER_COMMAND, {"command": command}))

    def emit_input(self, text: str) -> None:
        self.emit(Event(EventType.USER_INPUT, {"text": text}))