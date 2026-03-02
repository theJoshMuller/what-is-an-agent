# app/settings_window.py
# Stub — full implementation in Task 8
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw


class SettingsWindow(Adw.PreferencesDialog):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Settings (coming soon)")
