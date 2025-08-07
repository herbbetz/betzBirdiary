'''
chatGPT 2.8.2025
This code is for a simple HTTP server that streams JPEG images from a Raspberry Pi camera using the Picamera2 library.
python3 jpegserv.py
http://<your-pi-ip>:8000
''' 
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from threading import Thread
from PIL import Image
from picamera2 import Picamera2
import time

# Initialize camera
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
picam2.start()
time.sleep(2)  # Let camera warm up


class StreamingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/':
            self.send_error(404)
            return

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
                time.sleep(0.1)  # ~10 FPS
        except BrokenPipeError:
            print("Client disconnected.")
        except Exception as e:
            print(f"Error: {e}")


def run_server(host='0.0.0.0', port=8000):
    server = HTTPServer((host, port), StreamingHandler)
    print(f"Streaming on http://{host}:{port}")
    server.serve_forever()


# Run the server in a separate thread
server_thread = Thread(target=run_server, daemon=True)
server_thread.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Server stopped.")
