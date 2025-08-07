'''
chatGPT 2.8.2025
This code is for a simple HTTP mjpeg server adjusting gain/exposure by webpage from a Raspberry Pi camera using the Picamera2 library.
python3 cam_contr_server.py
http://<your-pi-ip>:8000
'''
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from threading import Thread
from urllib.parse import urlparse, parse_qs
from PIL import Image
from picamera2 import Picamera2
import time

# Init camera
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
picam2.start()
time.sleep(2)

# Default settings
gain = 4.0
exposure = 10000


class StreamingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global gain, exposure

        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <head><title>Camera Control</title></head>
                <body>
                <h1>MJPEG Stream with Controls</h1>
                <img src="/stream" width="640" height="480"><br><br>

                <label>Analogue Gain</label>
                <input type="range" min="1" max="16" step="0.1" value="4" id="gain" oninput="updateGain(this.value)">
                <span id="gainVal">4.0</span><br><br>

                <label>Exposure Time (µs)</label>
                <input type="range" min="100" max="1000000" step="1000" value="10000" id="exposure" oninput="updateExposure(this.value)">
                <span id="expVal">10000</span>

                <script>
                    function updateGain(val) {
                        document.getElementById('gainVal').textContent = val;
                        fetch('/set?gain=' + val);
                    }
                    function updateExposure(val) {
                        document.getElementById('expVal').textContent = val;
                        fetch('/set?exposure=' + val);
                    }
                </script>
                </body>
                </html>
            """)
        elif parsed.path == "/stream":
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    frame = picam2.capture_array()
                    image = Image.fromarray(frame)
                    buffer = BytesIO()
                    image.save(buffer, format='JPEG')
                    jpg_data = buffer.getvalue()

                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(jpg_data)))
                    self.end_headers()
                    self.wfile.write(jpg_data)
                    self.wfile.write(b'\r\n')
                    time.sleep(0.1)
            except Exception:
                pass
        elif parsed.path == "/set":
            qs = parse_qs(parsed.query)
            if "gain" in qs:
                try:
                    gain = float(qs["gain"][0])
                    picam2.set_controls({"AeEnable": False, "AnalogueGain": gain, "ExposureTime": exposure})
                except ValueError:
                    pass
            if "exposure" in qs:
                try:
                    exposure = int(qs["exposure"][0])
                    picam2.set_controls({"AeEnable": False, "AnalogueGain": gain, "ExposureTime": exposure})
                except ValueError:
                    pass
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error(404)


def run_server(host='0.0.0.0', port=8000):
    server = HTTPServer((host, port), StreamingHandler)
    print(f"Server running at http://{host}:{port}")
    server.serve_forever()


# Run server in background
server_thread = Thread(target=run_server, daemon=True)
server_thread.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down.")
