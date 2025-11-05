#!/usr/bin/env python3
# widget-img.py — simple GTK3 image widget for Wayfire
import os
import time
import json
import gi

# --- Wait for Wayland display to appear before GTK init ---
wayland_display = os.environ.get("WAYLAND_DISPLAY", "wayland-0")
sock_path = f"/run/user/{os.getuid()}/{wayland_display}"
for _ in range(60):  # wait up to ~30s
    if os.path.exists(sock_path):
        break
    time.sleep(0.5)

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

# Paths
RAMDISK = os.path.expanduser("~/station3/ramdisk")
VIDMSG_JSON = os.path.join(RAMDISK, "vidmsg.json")

# Settings
IMG_SIZE = (320, 240)
UPDATE_INTERVAL = 1000  # ms

class ImageWidget(Gtk.Window):
    def __init__(self):
        super().__init__(title="camera img")
        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_accept_focus(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.stick()

        # Try to get transparency
        screen = self.get_screen()
        visual = screen.get_rgba_visual() if screen else None
        if visual:
            self.set_visual(visual)

        # Image box
        self.image = Gtk.Image()
        self.add(self.image)
        self.set_size_request(*IMG_SIZE)

        # Position near top center
        screen = Gdk.Screen.get_default()
        if screen:
            monitor = screen.get_primary_monitor()
            geometry = screen.get_monitor_geometry(monitor)
            x = geometry.x + (geometry.width - IMG_SIZE[0]) // 2
            y = geometry.y + 10
            self.move(x, y)

        self.show_all()

        # Periodic update
        GLib.timeout_add(UPDATE_INTERVAL, self.update_image)
        self.update_image()

    def update_image(self):
        """Read vidmsg.json and show the latest image."""
        try:
            with open(VIDMSG_JSON) as f:
                imgid = json.load(f).get("imgid", 0)
        except Exception:
            imgid = 0

        img_path = os.path.join(RAMDISK, f"{imgid}.jpg")
        if os.path.exists(img_path):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(img_path, *IMG_SIZE)
                self.image.set_from_pixbuf(pixbuf)
            except Exception:
                pass

        return True  # continue periodic updates


if __name__ == "__main__":
    win = ImageWidget()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
