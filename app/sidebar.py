# app/sidebar.py
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from app import config


TOOL_INFO = {
    "read_file": (
        "document-open-symbolic",
        "read_file",
        "Read a file from the working directory",
    ),
    "write_txt_file": (
        "document-save-symbolic",
        "write_txt_file",
        "Write a text file to the working directory",
    ),
    "tts_generate_audio": (
        "audio-speakers-symbolic",
        "tts_generate_audio",
        "Generate speech audio via Kokoro TTS",
    ),
}


class Sidebar(Gtk.Box):
    def __init__(self, on_tool_toggled=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._on_tool_toggled = on_tool_toggled
        self._status_label = None
        self._model_row = None
        self._build()

    def _build(self):
        self.set_size_request(220, -1)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(scroll)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scroll.set_child(content)

        # ── Tools ─────────────────────────────────────────────────
        tools_group = Adw.PreferencesGroup()
        tools_group.set_title("Tools")
        tools_group.set_margin_start(12)
        tools_group.set_margin_end(12)
        tools_group.set_margin_top(16)
        content.append(tools_group)

        for tool_key, (icon_name, config_key, description) in TOOL_INFO.items():
            row = Adw.SwitchRow()
            row.set_title(tool_key)
            row.set_subtitle(description)
            row.set_icon_name(icon_name)
            row.set_active(config.get(f"tools.{config_key}", False))
            row.connect("notify::active", self._on_switch_changed, config_key)
            tools_group.add(row)

        # ── Provider (above model name) ────────────────────────────────
        provider_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        provider_outer.set_margin_start(12)
        provider_outer.set_margin_end(12)
        provider_outer.set_margin_top(16)

        provider_label = Gtk.Label(label="Provider")
        provider_label.set_xalign(0)
        provider_label.add_css_class("heading")
        provider_outer.append(provider_label)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        btn_row.add_css_class("linked")

        self._ollama_btn = Gtk.ToggleButton(label="Ollama")
        self._ollama_btn.set_hexpand(True)
        self._openrouter_btn = Gtk.ToggleButton(label="OpenRouter")
        self._openrouter_btn.set_hexpand(True)
        self._openrouter_btn.set_group(self._ollama_btn)

        current_provider = config.get("provider", "ollama")
        self._ollama_btn.set_active(current_provider == "ollama")
        self._openrouter_btn.set_active(current_provider == "openrouter")

        self._ollama_btn.connect("toggled", self._on_provider_toggled, "ollama")
        self._openrouter_btn.connect("toggled", self._on_provider_toggled, "openrouter")

        btn_row.append(self._ollama_btn)
        btn_row.append(self._openrouter_btn)
        provider_outer.append(btn_row)
        content.append(provider_outer)

        # ── Model name ──────────────────────────────────────────────────
        model_group = Adw.PreferencesGroup()
        model_group.set_title("Model")
        model_group.set_margin_start(12)
        model_group.set_margin_end(12)
        model_group.set_margin_top(8)
        content.append(model_group)

        # Current model name display
        self._model_row = Adw.ActionRow()
        self._model_row.set_title("Active")
        self._update_model_subtitle()
        model_group.add(self._model_row)

        # ── Status ─────────────────────────────────────────────────
        status_group = Adw.PreferencesGroup()
        status_group.set_title("Status")
        status_group.set_margin_start(12)
        status_group.set_margin_end(12)
        status_group.set_margin_top(16)
        content.append(status_group)

        status_row = Adw.ActionRow()
        status_row.set_title("State")

        self._status_label = Gtk.Label(label="Ready")
        self._status_label.set_valign(Gtk.Align.CENTER)
        self._status_label.add_css_class("success")
        status_row.add_suffix(self._status_label)
        status_group.add(status_row)

        # ── Branding ───────────────────────────────────────────────
        branding_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        branding_box.set_margin_top(24)
        branding_box.set_margin_bottom(16)
        branding_box.set_margin_start(12)
        branding_box.set_margin_end(12)
        branding_box.set_halign(Gtk.Align.CENTER)

        # Spacer pushes branding to the bottom
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        content.append(spacer)

        made_by = Gtk.Label(label="Made by Josh Müller")
        made_by.add_css_class("caption")
        made_by.add_css_class("dim-label")

        website_btn = Gtk.LinkButton(uri="https://joshmuller.ca", label="joshmuller.ca")
        website_btn.add_css_class("caption")
        website_btn.set_halign(Gtk.Align.CENTER)

        branding_box.append(made_by)
        branding_box.append(website_btn)
        content.append(branding_box)

    # ── Callbacks ──────────────────────────────────────────────────

    def _on_switch_changed(self, row, _param, config_key: str):
        active = row.get_active()
        config.set(f"tools.{config_key}", active)
        if self._on_tool_toggled:
            self._on_tool_toggled(config_key, active)

    def _on_provider_toggled(self, btn: Gtk.ToggleButton, provider: str):
        if btn.get_active():
            config.set("provider", provider)
            self._update_model_subtitle()

    def _update_model_subtitle(self):
        if self._model_row is None:
            return
        provider = config.get("provider", "ollama")
        model = (
            config.get("ollama.model", "ministral-3:14b-instruct-2512-q8_0")
            if provider == "ollama"
            else config.get("openrouter.model", "qwen/qwen3-235b-a22b-2507")
        )
        # Show only the part before ":" (e.g. "ministral-3" not "ministral-3:14b-instruct-...")
        display = model.split(":")[0]
        self._model_row.set_subtitle(display)

    # ── Public API ─────────────────────────────────────────────────

    def set_status(self, text: str):
        if self._status_label is None:
            return
        self._status_label.set_text(text)
        # Color-code by state
        for cls in ("success", "warning", "error"):
            self._status_label.remove_css_class(cls)
        if text == "Ready":
            self._status_label.add_css_class("success")
        elif text.startswith("Error"):
            self._status_label.add_css_class("error")
        else:
            self._status_label.add_css_class("warning")
