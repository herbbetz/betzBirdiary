# startup script for widget on wayfire desktop
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango
import json
import os

# Paths to your JSON files
ENV_JSON = os.path.expanduser("~/station3/ramdisk/env.json")
SYSMON_JSON = os.path.expanduser("~/station3/ramdisk/sysmon.json")

# Update interval in milliseconds
UPDATE_INTERVAL = 60000

class DesktopWidget(Gtk.Window):
    def __init__(self):
        super().__init__(title="bird values")
        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_accept_focus(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.stick()

        # Transparent background
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        
        self.connect("draw", self.on_draw)

        # Label for text output
        self.label = Gtk.Label()
        self.label.set_xalign(0)
        self.label.set_yalign(0)
        self.label.set_name("widget-label")  # styled via CSS
        self.add(self.label)

        self.set_size_request(300, 200)
        self.move(20, 40)  # position on screen
        self.show_all()

        # CSS styling for font and color
        css = b"""
        #widget-label {
            font-family: Monospace;
            font-size: 11px;
            color: white;
        }
        """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            screen,
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Start periodic update
        GLib.timeout_add(UPDATE_INTERVAL, self.update)
        self.update()  # initial draw

    def on_draw(self, widget, cr):
        # Semi-transparent background
        cr.set_source_rgba(0, 0, 0, 0.3)  # black, 30% opacity
        cr.paint()
        return False

    def read_json(self, path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return {}

    def update(self):
        env = self.read_json(ENV_JSON)
        sysmon = self.read_json(SYSMON_JSON)

        text = "Environment\n"
        text += f"Date: {env.get('date', '?')}\n"
        text += f"Temp: {env.get('temperature', '?')} °C\n"
        text += f"Humidity: {env.get('humidity', '?')} %\n\n"

        text += "System\n"
        text += f"Date: {sysmon.get('date', '?')}\n"
        text += f"Uptime: {sysmon.get('uptime', '?')}\n"
        text += f"Wi-Fi: {sysmon.get('wlan0', '?')}\n"
        text += f"CPU V: {sysmon.get('cpuvolt', '?')}\n"
        text += f"CPU T: {sysmon.get('cputemp', '?')}\n"
        text += f"CPU Load: {sysmon.get('cpuload', '?')}\n"

        self.label.set_text(text)
        return True  # continue periodic update

if __name__ == "__main__":
    win = DesktopWidget()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
