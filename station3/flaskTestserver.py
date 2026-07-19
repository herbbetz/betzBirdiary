import os
from flask import Flask, request, jsonify, send_from_directory
import subprocess
from datetime import datetime
# Import the entire module so you can use the module prefix
import stations.rarebrds4srvpag as rb
from sharedBird import prev_month

# Initialize Flask app
# We explicitly set static_folder=None so it doesn't conflict with our custom root route
app = Flask(__name__)

# Get the absolute path of the directory where server.py lives
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
VK_SCRIPT_RUNNING = False # flag OUTSIDE the function context to keep track of state across multiple browser refreshes.

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

@app.route("/api/report-data")
# selectstations.html submits to layouter '/stations/rb_report.html' with GET parameters station_name and station_id
def api_rarebirds():
    station_name = request.args.get('station_name')
    station_id = request.args.get('station_id')
    # DEBUG PRINT: Watch this terminal output after starting flask from terminal!
    print(f"--- Flask Received: Name={station_name}, ID={station_id} ---")
    # module imported above as rb, so we can call rb.setStation() and rb.getHTML()
    rb.setStation(station_name, station_id)
    report_data = rb.getReport()
    return jsonify(report_data)


# 1. Define a global lock flag OUTSIDE the function context 
# to keep track of state across multiple browser refreshes.
VK_SCRIPT_RUNNING = False

@app.route("/videoking")
def monthlyking():
    global VK_SCRIPT_RUNNING
    
    today = datetime.today()
    CURRENT_MONTH = today.strftime("%Y-%m")
    TARGET_MONTH = prev_month(CURRENT_MONTH)
    OUTPUT_FILE = f"vk{TARGET_MONTH}.html"
    
    # 2. Fix the Relative Path Trap: Force absolute path combining BASE_DIR
    STATIONS_DIR = os.path.join(BASE_DIR, "stations")
    OUT_PATH = os.path.join(STATIONS_DIR, OUTPUT_FILE)
    
    print(f"\n[FLASK DEBUG] Checking for VideoKing report...")
    print(f"[FLASK DEBUG] Expected Path: {OUT_PATH}")
    print(f"[FLASK DEBUG] File Exists Status: {os.path.exists(OUT_PATH)}")
    
    # If file exists, reset the lock and serve it!
    if os.path.exists(OUT_PATH):
        VK_SCRIPT_RUNNING = False  # Reset lock for next month
        print(f"[FLASK DEBUG] Serving file directly.")
        return send_from_directory(STATIONS_DIR, OUTPUT_FILE)
        
    else:
        print(f"[FLASK DEBUG] File not found yet. Lock status: {VK_SCRIPT_RUNNING}")
        
        # 3. True concurrency lock check
        if not VK_SCRIPT_RUNNING:
            VK_SCRIPT_RUNNING = True
            SCRIPT_PATH = os.path.join(STATIONS_DIR, "vk_lastmonth_pag.py")
            
            # Windows-safe command array execution (much safer than shell=True strings)
            cmd = ["python", SCRIPT_PATH]
            
            print(f"[FLASK DEBUG] Launching background process: {cmd}")
            subprocess.Popen(cmd) 

        return f"""
        <!doctype html>
        <html>
            <head>
                <meta http-equiv="refresh" content="15;url=/videoking">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>Wait...</title>
                <link rel="icon" href="/favicon.svg" type="image/svg+xml">
                <link rel="stylesheet" href="/bird.css">
            </head>
            <body>
                <h3>Compiling VideoKing stats for {TARGET_MONTH}...</h3>
                <p>Expected target location:<br><code>{OUT_PATH}</code></p>
                <strong>This page updates automatically every 15 seconds. Please wait...</strong>
            </body>
        </html>
        """
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)