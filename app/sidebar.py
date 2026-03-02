# app/sidebar.py
# Stub — full implementation in Task 7
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


class Sidebar(Gtk.Box):
    def __init__(self, on_tool_toggled=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        label = Gtk.Label(label="Sidebar (coming soon)")
        self.append(label)

    def set_status(self, text: str):
        pass
