import pytest
from qgunter.core.events import Event, EventBus, EventType


@pytest.mark.unit
class TestEventBus:
    def test_singleton(self):
        assert EventBus.get() is EventBus.get()

    def test_subscribe_and_emit(self):
        bus = EventBus.get()
        received: list[Event] = []
        bus.subscribe(EventType.MESSAGE, lambda e: received.append(e))
        bus.emit(Event(EventType.MESSAGE, {"text": "Hello"}))
        assert len(received) == 1
        assert received[0].data["text"] == "Hello"

    def test_unsubscribe(self):
        bus = EventBus.get()
        received: list[Event] = []
        handler = lambda e: received.append(e)
        bus.subscribe(EventType.MESSAGE, handler)
        bus.unsubscribe(EventType.MESSAGE, handler)
        bus.emit(Event(EventType.MESSAGE, {"text": "Hello"}))
        assert len(received) == 0

    def test_handler_exception_doesnt_break_others(self):
        bus = EventBus.get()
        results: list[Event] = []
        bus.subscribe(EventType.MESSAGE, lambda e: (_ for _ in ()).throw(Exception("boom")))
        bus.subscribe(EventType.MESSAGE, lambda e: results.append(e))
        bus.emit_message("Test")
        assert len(results) == 1

    def test_emit_flag(self):
        bus = EventBus.get()
        received: list[Event] = []
        bus.subscribe(EventType.FLAG_FOUND, lambda e: received.append(e))
        bus.emit_flag("flag{test123}", "Found in output")
        assert received[0].data["flag"] == "flag{test123}"