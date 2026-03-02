# app/chat_panel.py
# Stub — full implementation in Task 6
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class ChatPanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        label = Gtk.Label(label="Chat panel (coming soon)")
        self.append(label)
        self._bubbles = {}
        self._next_id = 0

    def add_user_message(self, text: str):
        pass

    def start_assistant_message(self) -> int:
        bubble_id = self._next_id
        self._next_id += 1
        return bubble_id

    def append_text(self, bubble_id: int, text: str):
        pass

    def add_tool_indicator(self, tool_name: str):
        pass

    def add_tool_result(self, tool_name: str, result: dict, audio_file=None):
        pass

    def clear(self):
        pass
