#!/usr/bin/env python3
# startup script for widget on wayfire desktop
# started by ~/.config/systemd/user/widgets.service
# Disable accessibility bus (not needed for this widget)

import os
os.environ['NO_AT_BRIDGE'] = '1' # env to disable AT-SPI (accessibility) warning
import time
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import json

'''
# --- Wait for Wayland display to be ready --- not neccessary, if script is started by desktop link
wayland_display = os.environ.get("WAYLAND_DISPLAY", "wayland-0")
timeout = 60  # seconds
interval = 1.0
elapsed = 0

while not os.path.exists(f"/run/user/{os.getuid()}/{wayland_display}") and elapsed < timeout:
    time.sleep(interval)
    elapsed += interval

if elapsed >= timeout:
    print(f"[widgets.py] Warning: Wayland display {wayland_display} not found after {timeout}s")

print("[widgets.py] Attempting to initialize GTK...")
if not Gtk.init_check(None)[0]:
    print("[widgets.py] Error: Failed to initialize GTK")
    print(f"[widgets.py] WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY', 'not set')}")
    exit(1)
print("[widgets.py] GTK initialized successfully")
'''
# --- Paths to your JSON files ---
VID_JSON = os.path.expanduser("~/station3/ramdisk/vidmsg.json")
ENV_JSON = os.path.expanduser("~/station3/ramdisk/env.json")
SYSMON_JSON = os.path.expanduser("~/station3/ramdisk/sysmon.json")

luxLevels = ["dim", "cloudy", "shiny", "sunny", "dark", "blazing"]

# --- Update interval in milliseconds ---
# update is also active, if desktop is not viewed by VNC client or HDMI monitor and data have not changed. However CPU load is minimal.
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

        # --- Transparent background setup ---
        gdk_screen = self.get_screen()
        visual = gdk_screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)

        self.connect("draw", self.on_draw)

        # --- Label for text output ---
        self.label = Gtk.Label()
        self.label.set_xalign(0)
        self.label.set_yalign(0)
        self.label.set_name("widget-label")  # styled via CSS
        self.add(self.label)

        self.set_size_request(300, 200)

        # --- Position widget: 10px from left, halfway down screen ---
        display = Gdk.Display.get_default()
        if display:
            monitor = display.get_primary_monitor()
            if monitor:
                geometry = monitor.get_geometry()
                x = geometry.x + 10
                y = geometry.y + geometry.height // 2
                self.move(x, y)
            else:
                self.move(10, 400)  # fallback
        else:
            self.move(10, 400)  # fallback if no display info

        self.show_all()

        # --- CSS styling for font and color ---
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
            gdk_screen,
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # --- Start periodic update ---
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
        vidmsg = self.read_json(VID_JSON)
        env = self.read_json(ENV_JSON)
        sysmon = self.read_json(SYSMON_JSON)

        # --- Build display text ---
        text = "Camera\n"
        text += f"Illumination: {vidmsg.get('luxraw', '?')}\n"
        if 'lux' in vidmsg:
            value = int(vidmsg['lux'])
            label = luxLevels[value - 1] if 0 < value < len(luxLevels) else '?'
            recordReady = "ready" if 0 < value <= 4 else "inactive"
            text += f"Luxlevel: {value} {label} {recordReady}\n"

        text += f"Browser active: {vidmsg.get('clientactive', '?')}\n"
        text += f"Standby: {vidmsg.get('standby', '?')}\n\n"

        text += "Environment\n"
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
