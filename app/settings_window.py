# app/settings_window.py
import os
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from app import config


class SettingsWindow(Adw.PreferencesDialog):
    def __init__(self):
        super().__init__()
        self.set_title("Settings")
        self._build()

    def _build(self):
        self.add(self._build_llm_page())
        self.add(self._build_tools_page())
        self.add(self._build_tts_page())

    # ── LLM Page ──────────────────────────────────────────────────

    def _build_llm_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage()
        page.set_title("LLM")
        page.set_icon_name("computer-symbolic")

        # Ollama group
        ollama_group = Adw.PreferencesGroup()
        ollama_group.set_title("Ollama")
        ollama_group.set_description(
            "Local LLM server. Defaults to localhost — change the host to use a remote server."
        )
        page.add(ollama_group)

        ollama_host = Adw.EntryRow()
        ollama_host.set_title("Host")
        ollama_host.set_text(str(config.get("ollama.host", "localhost")))
        ollama_host.connect("changed", lambda r: config.set("ollama.host", r.get_text()))
        ollama_group.add(ollama_host)

        ollama_port = Adw.EntryRow()
        ollama_port.set_title("Port")
        ollama_port.set_text(str(config.get("ollama.port", 11434)))
        ollama_port.connect("changed", self._on_ollama_port_changed)
        ollama_group.add(ollama_port)

        ollama_model = Adw.EntryRow()
        ollama_model.set_title("Model")
        ollama_model.set_text(str(config.get("ollama.model", "gemma3:27b")))
        ollama_model.connect("changed", lambda r: config.set("ollama.model", r.get_text()))
        ollama_group.add(ollama_model)

        # OpenRouter group
        or_group = Adw.PreferencesGroup()
        or_group.set_title("OpenRouter")
        or_group.set_description(
            "Cloud LLM via openrouter.ai. Get a free API key at openrouter.ai."
        )
        page.add(or_group)

        or_model = Adw.EntryRow()
        or_model.set_title("Model")
        or_model.set_text(str(config.get("openrouter.model", "qwen/qwen3-235b-a22b-2507")))
        or_model.connect("changed", lambda r: config.set("openrouter.model", r.get_text()))
        or_group.add(or_model)

        or_key = Adw.PasswordEntryRow()
        or_key.set_title("API Key")
        stored_key = config.get("openrouter.api_key", "")
        env_key = os.environ.get("OPENROUTER_API_KEY", "")
        if stored_key and stored_key != "YOUR_OPENROUTER_API_KEY_HERE":
            or_key.set_text(stored_key)
        elif env_key:
            or_key.set_subtitle("Using $OPENROUTER_API_KEY from environment")
        else:
            or_key.set_subtitle("Set OPENROUTER_API_KEY env var or enter key here")
        or_key.connect("changed", lambda r: config.set("openrouter.api_key", r.get_text()))
        or_group.add(or_key)

        return page

    # ── Tools Page ────────────────────────────────────────────────

    def _build_tools_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage()
        page.set_title("Tools")
        page.set_icon_name("applications-engineering-symbolic")

        files_group = Adw.PreferencesGroup()
        files_group.set_title("File Tools")
        files_group.set_description(
            "Configure default filenames used by file tools."
        )
        page.add(files_group)

        read_filename = Adw.EntryRow()
        read_filename.set_title("Default read filename")
        read_filename.set_text(config.get("tools.default_read_filename", "note.txt"))
        read_filename.connect(
            "changed",
            lambda r: config.set("tools.default_read_filename", r.get_text())
        )
        files_group.add(read_filename)

        return page

    # ── TTS Page ──────────────────────────────────────────────────

    def _build_tts_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage()
        page.set_title("TTS")
        page.set_icon_name("audio-speakers-symbolic")

        kokoro_group = Adw.PreferencesGroup()
        kokoro_group.set_title("Kokoro TTS")
        kokoro_group.set_description(
            "Self-hosted text-to-speech server (Kokoro-FastAPI). "
            "Defaults to localhost — set up your own instance using the link below."
        )
        page.add(kokoro_group)

        # Setup guide link row
        setup_row = Adw.ActionRow()
        setup_row.set_title("Setup Guide")
        setup_row.set_subtitle("github.com/remsky/Kokoro-FastAPI")
        link_btn = Gtk.LinkButton(uri="https://github.com/remsky/Kokoro-FastAPI", label="Open →")
        link_btn.set_valign(Gtk.Align.CENTER)
        setup_row.add_suffix(link_btn)
        kokoro_group.add(setup_row)

        tts_host = Adw.EntryRow()
        tts_host.set_title("Host")
        tts_host.set_text(str(config.get("tts.host", "localhost")))
        tts_host.connect("changed", lambda r: config.set("tts.host", r.get_text()))
        kokoro_group.add(tts_host)

        tts_port = Adw.EntryRow()
        tts_port.set_title("Port")
        tts_port.set_text(str(config.get("tts.port", 8880)))
        tts_port.connect("changed", self._on_tts_port_changed)
        kokoro_group.add(tts_port)

        return page

    # ── Helpers ───────────────────────────────────────────────────

    def _on_ollama_port_changed(self, row):
        try:
            config.set("ollama.port", int(row.get_text()))
        except ValueError:
            pass  # Ignore non-integer input while user is typing

    def _on_tts_port_changed(self, row):
        try:
            config.set("tts.port", int(row.get_text()))
        except ValueError:
            pass
