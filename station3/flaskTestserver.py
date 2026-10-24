import os
import psutil
from flask import Flask, request, jsonify, send_from_directory, Response
import subprocess
from datetime import datetime
# Import the entire module so you can use the module prefix
import stations.rarebrds4srvpag as rb
from sharedBird import prev_month

# Initialize Flask app
# We explicitly set static_folder=None so it doesn't conflict with our custom root route
app = Flask(__name__)
app = Flask(__name__, static_folder='.')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 # disable cacheing
# Get the absolute path of the directory where server.py lives
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
VK_SCRIPT_RUNNING = False # flag OUTSIDE the function context to keep track of state across multiple browser refreshes.

def has_active_ssh():
    """Checks for established TCP connections on port 22."""
    for conn in psutil.net_connections(kind='tcp'):
        # Check if local or remote port is 22 and state is ESTABLISHED
        if conn.status == psutil.CONN_ESTABLISHED:
            if conn.laddr.port == 22 or (conn.raddr and conn.raddr.port == 22):
                return True
    return False

@app.route('/')
def hello():
    return "Hello, World! Head over to your HTML dropdown page to submit a station."

@app.route('/<path:filename>')
def serve_static(filename):
    """
    Serves supporting static files (like stations.js, script.js, style.css) 
    from the same directory.
    """
    return send_from_directory(BASE_DIR, filename)

@app.route('/shutdown')
def shutdown():
    if has_active_ssh():
        # Active SSH/SFTP connection detected -> return warning page
        return send_from_directory(app.static_folder, 'shutdownNot.html')
    else:
        return send_from_directory(app.static_folder, 'shutdown.html')

@app.route("/ping")
def ping():
    def gen():
        p = subprocess.Popen(["ping", "-c", "20", "-i", "0.5", "wiediversistmeingarten.org"], stdout=subprocess.PIPE, text=True)
        for line in p.stdout: yield line
    return Response(gen(), mimetype="text/plain")

@app.route("/curl")
def curl():
    fmt = "%{time_namelookup} %{time_connect} %{time_appconnect} %{time_starttransfer} %{time_total} %{http_code}"
    r = subprocess.run(["curl", "-o", "/dev/null", "-s", "-w", fmt, "https://wiediversistmeingarten.org"], capture_output=True, text=True, timeout=30)
    try: dns, tcp, tls, ttfb, total, code = r.stdout.split()
    except ValueError: return Response(f"<pre>curl failed: {r.stderr}</pre>", status=502, mimetype="text/html")
    t = [float(x) * 1000 for x in (dns, tcp, tls, ttfb, total)]
    rows = [("DNS", t[0]), ("TCP", t[1] - t[0]), ("TLS", t[2] - t[1]), ("Server wait", t[3] - t[2]), ("Download", t[4] - t[3])]
    body = "".join(f"<tr><td>{n}</td><td>{v:.1f} ms</td></tr>" for n, v in rows)
    return Response(f"<h3>HTTP {code}, total {t[4]:.0f} ms</h3><table border=1>{body}</table>", mimetype="text/html")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, debug=False)