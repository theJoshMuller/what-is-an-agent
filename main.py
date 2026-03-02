# main.py
import sys
from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw
from app import config
from app.window import AgentDemoWindow


class AgentDemoApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="ca.joshmuller.agent-demo")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        config.load()
        win = AgentDemoWindow(application=app)

        # Load CSS
        css_provider = Gtk.CssProvider()
        css_file = Path(__file__).parent / "app" / "style.css"
        if css_file.exists():
            css_provider.load_from_path(str(css_file))
        Gtk.StyleContext.add_provider_for_display(
            win.get_display(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        win.present()


def main():
    app = AgentDemoApp()
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()
