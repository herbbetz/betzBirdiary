import os
from flask import Flask, request, send_from_directory
# Import the entire module so you can use the module prefix
import rarebirds4server 

# Initialize Flask app
# We explicitly set static_folder=None so it doesn't conflict with our custom root route
app = Flask(__name__)

# Get the absolute path of the directory where server.py lives
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

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

@app.route("/rarebirds")
def rarebirds():
    station_name = request.args.get('station_name')
    station_id = request.args.get('station_id')
    
    # This now works perfectly because the entire module was imported
    rarebirds4server.setStation(station_name, station_id)
    return rarebirds4server.getHTML()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)