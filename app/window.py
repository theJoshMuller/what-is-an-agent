# app/window.py
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, GObject
import threading

from app import config
from app.chat_panel import ChatPanel
from app.sidebar import Sidebar
from app.settings_window import SettingsWindow
from app import tools as tool_registry


class AgentDemoWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("What is an Agent?")
        self.set_default_size(1000, 700)
        self.messages: list[dict] = []  # Conversation context

        self._build_ui()

    def _build_ui(self):
        # Root: ToolbarView wraps header + content
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        # Header bar
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        # Settings button (left side)
        settings_btn = Gtk.Button()
        settings_content = Adw.ButtonContent(icon_name="preferences-system-symbolic", label="Settings")
        settings_btn.set_child(settings_content)
        settings_btn.connect("clicked", self._on_settings)
        header.pack_start(settings_btn)

        # Clear context button
        clear_btn = Gtk.Button()
        clear_content = Adw.ButtonContent(icon_name="edit-clear-all-symbolic", label="Clear")
        clear_btn.set_child(clear_content)
        clear_btn.set_tooltip_text("Clear conversation")
        clear_btn.connect("clicked", self._on_clear)
        header.pack_end(clear_btn)

        # Sidebar toggle — right side, right-panel icon
        self._sidebar_toggle = Gtk.ToggleButton()
        toggle_content = Adw.ButtonContent(icon_name="view-right-pane-symbolic", label="Tools")
        self._sidebar_toggle.set_child(toggle_content)
        self._sidebar_toggle.set_tooltip_text("Show/Hide Tools")
        header.pack_end(self._sidebar_toggle)

        # Responsive split view: sidebar on right, chat on left
        self._split_view = Adw.OverlaySplitView()
        self._split_view.set_sidebar_position(Gtk.PackType.END)
        self._split_view.set_max_sidebar_width(300)
        self._split_view.set_min_sidebar_width(220)
        self._split_view.set_show_sidebar(True)
        toolbar_view.set_content(self._split_view)

        # Bind toggle button to split view show-sidebar property
        self._sidebar_toggle.bind_property(
            "active",
            self._split_view,
            "show-sidebar",
            GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE,
        )

        # Chat panel (main content area)
        self._chat = ChatPanel()
        self._split_view.set_content(self._chat)

        # Sidebar (tools + model + status + branding)
        self._sidebar = Sidebar(on_tool_toggled=self._on_tool_toggled)
        self._split_view.set_sidebar(self._sidebar)

        # Input row pinned to bottom
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_box.set_margin_start(12)
        input_box.set_margin_end(12)
        input_box.set_margin_top(8)
        input_box.set_margin_bottom(12)

        self._entry = Gtk.Entry()
        self._entry.set_hexpand(True)
        self._entry.set_placeholder_text("Type a message...")
        self._entry.connect("activate", self._on_send)
        input_box.append(self._entry)

        self._send_btn = Gtk.Button(label="Send")
        self._send_btn.add_css_class("suggested-action")
        self._send_btn.connect("clicked", self._on_send)
        input_box.append(self._send_btn)

        toolbar_view.add_bottom_bar(input_box)

    # ── Actions ───────────────────────────────────────────────────

    def _on_clear(self, *_):
        self.messages = []
        self._chat.clear()

    def _on_settings(self, *_):
        win = SettingsWindow()
        win.present(self)

    def _on_tool_toggled(self, tool_name: str, enabled: bool):
        """Toggling any tool clears context (tool schemas change)."""
        self._on_clear()

    def _on_send(self, *_):
        text = self._entry.get_text().strip()
        if not text:
            return
        self._entry.set_text("")
        self._set_input_sensitive(False)

        # Add user message to context and UI
        self.messages.append({"role": "user", "content": text})
        self._chat.add_user_message(text)

        # Start agentic loop in a daemon thread
        thread = threading.Thread(target=self._agent_loop, daemon=True)
        thread.start()

    def _set_input_sensitive(self, sensitive: bool):
        self._entry.set_sensitive(sensitive)
        self._send_btn.set_sensitive(sensitive)

    def _create_bubble_sync(self) -> int:
        """Create an assistant bubble on the main thread, safe to call from any thread."""
        result: list[int] = []
        event = threading.Event()

        def _create():
            result.append(self._chat.start_assistant_message())
            event.set()
            return False

        GLib.idle_add(_create)
        event.wait()
        return result[0]

    # ── Agentic loop ──────────────────────────────────────────────

    def _agent_loop(self):
        """
        Runs in a background thread.
        Uses GLib.idle_add() for all UI updates (thread-safe).

        Loop:
          1. POST to LLM with current context + enabled tool schemas
          2. Stream tokens into chat bubble
          3. If LLM returns tool_calls → execute each tool → append result → loop
          4. If no tool_calls → done
        """
        bubble_id = -1
        try:
            from app.llm import ollama, openrouter

            provider = config.get("provider", "ollama")
            llm_stream = ollama.stream if provider == "ollama" else openrouter.stream

            enabled_tools = [
                name for name in ["read_file", "write_txt_file", "tts_generate_audio"]
                if config.get(f"tools.{name}", False)
            ]
            tool_schemas = tool_registry.get_tool_schemas(enabled_tools)

            while True:
                # Create a new streaming assistant bubble (thread-safe)
                bubble_id = self._create_bubble_sync()
                full_text = ""
                pending_tool_calls = []

                GLib.idle_add(self._sidebar.set_status, "Thinking…")

                system = {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant with access to tools. "
                        "When the user asks you to read files, write files, or generate speech, "
                        "always use the appropriate tool — never say you cannot do something that a tool enables."
                    ),
                }
                for chunk in llm_stream([system] + self.messages, tool_schemas):
                    if chunk.error:
                        GLib.idle_add(
                            self._chat.append_text,
                            bubble_id,
                            f"\n\n⚠ Error: {chunk.error}"
                        )
                        GLib.idle_add(self._sidebar.set_status, "Error")
                        GLib.idle_add(self._set_input_sensitive, True)
                        return
                    if chunk.text:
                        full_text += chunk.text
                        GLib.idle_add(self._chat.append_text, bubble_id, chunk.text)
                    if chunk.tool_calls:
                        pending_tool_calls.extend(chunk.tool_calls)
                    if chunk.done:
                        break

                # Append completed assistant turn to context
                if full_text or pending_tool_calls:
                    assistant_msg = {"role": "assistant", "content": full_text}
                    if pending_tool_calls:
                        assistant_msg["tool_calls"] = [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {"name": tc.name, "arguments": tc.arguments},
                            }
                            for tc in pending_tool_calls
                        ]
                    self.messages.append(assistant_msg)

                # If no tool calls → conversation turn complete
                if not pending_tool_calls:
                    break

                # Execute each tool call
                for tc in pending_tool_calls:
                    GLib.idle_add(self._chat.add_tool_indicator, tc.name)
                    GLib.idle_add(self._sidebar.set_status, f"Running: {tc.name}")

                    result = tool_registry.dispatch(tc.name, tc.arguments)

                    # Append tool result to context
                    tool_content = (
                        result["result"] if not result.get("error")
                        else f"Error: {result['error']}"
                    )
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.name,
                        "content": tool_content,
                    })

                    # Show result card + optional play button in UI
                    audio_file = result.get("audio_file")
                    GLib.idle_add(
                        self._chat.add_tool_result,
                        tc.name,
                        result,
                        audio_file,
                    )

            # Done — restore input
            GLib.idle_add(self._sidebar.set_status, "Ready")
            GLib.idle_add(self._set_input_sensitive, True)
        except Exception as e:
            import traceback
            err_msg = f"\n\n⚠ Unexpected error: {e}"
            GLib.idle_add(self._chat.append_text, bubble_id, err_msg)
            GLib.idle_add(self._sidebar.set_status, "Error")
            GLib.idle_add(self._set_input_sensitive, True)
