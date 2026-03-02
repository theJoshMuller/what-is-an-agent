# app/chat_panel.py
import re
import subprocess
from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Pango, GLib


def markdown_to_pango(text: str) -> str:
    """Convert a small subset of Markdown to Pango markup for GTK labels."""
    # 1. Escape Pango special characters in the raw text first
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")

    # 2. Code blocks (``` ... ```) — monospace, before inline code
    text = re.sub(r"```[^\n]*\n?(.*?)```", lambda m: f'<tt>{m.group(1)}</tt>',
                  text, flags=re.DOTALL)

    # 3. Inline code: `code`
    text = re.sub(r"`([^`]+)`", r"<tt>\1</tt>", text)

    # 4. Bold: **text** or __text__
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text, flags=re.DOTALL)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text, flags=re.DOTALL)

    # 5. Italic: *text* or _text_ (single, not double)
    text = re.sub(r"\*([^*\n]+)\*", r"<i>\1</i>", text)
    text = re.sub(r"_([^_\n]+)_", r"<i>\1</i>", text)

    # 6. Headers: ### ## # — bold (on their own line)
    text = re.sub(r"^#{1,3} (.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)

    return text


class MessageBubble(Gtk.Box):
    """A single chat message bubble (user or assistant)."""

    def __init__(self, role: str, text: str = ""):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(4)
        self.set_margin_bottom(4)

        is_user = role == "user"
        self._raw_text = text  # Accumulates plain text; markup re-rendered on each update

        # Text label
        self._label = Gtk.Label()
        self._label.set_wrap(True)
        self._label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._label.set_xalign(0)
        self._label.set_selectable(True)
        self._label.set_use_markup(True)
        if text:
            self._render()

        self._label.set_margin_start(12)
        self._label.set_margin_end(12)
        self._label.set_margin_top(8)
        self._label.set_margin_bottom(8)

        # Bubble container
        bubble = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bubble.append(self._label)
        bubble.add_css_class("card")

        if is_user:
            bubble.set_margin_start(60)
            bubble.set_halign(Gtk.Align.END)
            bubble.add_css_class("user-bubble")
        else:
            bubble.set_margin_end(60)
            bubble.set_halign(Gtk.Align.START)
            bubble.add_css_class("assistant-bubble")

        self.append(bubble)

    def _render(self):
        """Re-render _raw_text as Pango markup. Falls back to plain text on error."""
        markup = markdown_to_pango(self._raw_text)
        try:
            self._label.set_markup(markup)
        except Exception:
            self._label.set_text(self._raw_text)

    def append_text(self, text: str):
        self._raw_text += text
        self._render()


class ToolChip(Gtk.Box):
    """Inline indicator shown while a tool is being called."""

    def __init__(self, tool_name: str):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.set_margin_start(20)
        self.set_margin_top(2)
        self.set_margin_bottom(2)
        self.set_halign(Gtk.Align.START)

        icon = Gtk.Image.new_from_icon_name("system-run-symbolic")
        icon.set_pixel_size(14)

        label = Gtk.Label(label=f"Using tool: {tool_name}")
        label.add_css_class("caption")
        label.add_css_class("dim-label")

        self.append(icon)
        self.append(label)


class ToolResultCard(Gtk.Box):
    """Expandable card showing tool output, with optional audio play button."""

    def __init__(self, tool_name: str, result: dict, audio_file: str | None = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_margin_start(20)
        self.set_margin_end(12)
        self.set_margin_top(2)
        self.set_margin_bottom(6)

        has_error = bool(result.get("error"))
        status_icon = "dialog-error-symbolic" if has_error else "emblem-ok-symbolic"
        label_text = f"  {tool_name}"

        # Header row: icon + name
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header_box.set_halign(Gtk.Align.START)
        status_img = Gtk.Image.new_from_icon_name(status_icon)
        status_img.set_pixel_size(14)
        name_lbl = Gtk.Label(label=label_text)
        name_lbl.add_css_class("caption")
        name_lbl.add_css_class("dim-label")
        header_box.append(status_img)
        header_box.append(name_lbl)

        # Expandable content
        expander = Gtk.Expander()
        expander.set_label_widget(header_box)

        content_text = result.get("error") or result.get("result", "")
        if len(content_text) > 800:
            content_text = content_text[:800] + "\n… (truncated)"

        content_label = Gtk.Label(label=content_text)
        content_label.set_wrap(True)
        content_label.set_xalign(0)
        content_label.add_css_class("monospace")
        content_label.add_css_class("caption")
        content_label.set_margin_start(20)
        content_label.set_margin_top(4)
        content_label.set_margin_bottom(4)
        expander.set_child(content_label)

        self.append(expander)

        # Audio play button (only for TTS results with a valid file)
        if audio_file and Path(audio_file).exists():
            play_btn = Gtk.Button(label="▶  Play Audio")
            play_btn.set_halign(Gtk.Align.START)
            play_btn.set_margin_start(20)
            play_btn.set_margin_top(2)
            play_btn.add_css_class("pill")
            play_btn.connect("clicked", lambda *_: _play_audio(audio_file))
            self.append(play_btn)


def _play_audio(filepath: str):
    """Non-blocking audio playback via aplay."""
    subprocess.Popen(
        ["aplay", filepath],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class ChatPanel(Gtk.Box):
    """Scrollable chat message list with streaming support."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._bubbles: dict[int, MessageBubble] = {}
        self._next_id = 0

        # Scrollable container
        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_vexpand(True)
        self._scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.append(self._scroll)

        # Message list — valign=END keeps messages pinned to the bottom
        self._list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._list.set_valign(Gtk.Align.END)
        self._list.set_vexpand(True)
        self._list.set_margin_top(12)
        self._list.set_margin_bottom(4)
        self._scroll.set_child(self._list)

    # ── Public API (called from window.py via GLib.idle_add) ──────

    def add_user_message(self, text: str):
        bubble = MessageBubble("user", text)
        self._list.append(bubble)
        self._scroll_to_bottom()

    def start_assistant_message(self) -> int:
        """Create an empty assistant bubble and return its ID for streaming."""
        bubble_id = self._next_id
        self._next_id += 1
        bubble = MessageBubble("assistant", "")
        self._bubbles[bubble_id] = bubble
        self._list.append(bubble)
        self._scroll_to_bottom()
        return bubble_id

    def append_text(self, bubble_id: int, text: str):
        """Append a token to an existing assistant bubble."""
        bubble = self._bubbles.get(bubble_id)
        if bubble:
            bubble.append_text(text)
            self._scroll_to_bottom()

    def add_tool_indicator(self, tool_name: str):
        chip = ToolChip(tool_name)
        self._list.append(chip)
        self._scroll_to_bottom()

    def add_tool_result(self, tool_name: str, result: dict, audio_file: str | None = None):
        card = ToolResultCard(tool_name, result, audio_file)
        self._list.append(card)
        self._scroll_to_bottom()

    def clear(self):
        self._bubbles = {}
        self._next_id = 0
        child = self._list.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._list.remove(child)
            child = nxt

    # ── Internal ──────────────────────────────────────────────────

    def _scroll_to_bottom(self):
        """Schedule scroll-to-bottom after GTK processes pending layout."""
        GLib.idle_add(self._do_scroll)

    def _do_scroll(self):
        adj = self._scroll.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())
        return False  # Don't repeat
