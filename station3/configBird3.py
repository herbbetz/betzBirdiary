import fcntl, json, os
# from configBird3 import * works in all *.py scripts, because configBird3.py is not only read, but also executed on import !
# 'import msgBird as ms' is an error: circular import as msgBird.py also imports configBird3.py
#
appdir = "/home/pi/station3"
birdpath = {
    'appdir': appdir,
    'ramdisk': f"{appdir}/ramdisk",
    'fifo': f"{appdir}/ramdisk/birdpipe"
}
# Path to config.json
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

def read_config_json():
    """
    Safely reads a JSON configuration file using a shared file lock.

    Returns:
        dict: The loaded configuration data, or an empty dictionary if
              the file is not found or is invalid.
    """
    if not os.path.exists(CONFIG_PATH):
        print(f"Config file not found: {CONFIG_PATH}")
        return {} # Return an empty dict on failure

    with open(CONFIG_PATH, 'r') as jfile:
        try:
            # Acquire a shared lock (LOCK_SH) to allow concurrent reads
            fcntl.flock(jfile, fcntl.LOCK_SH)

            # Read the current data
            data = json.load(jfile)
            return data

        except json.JSONDecodeError:
            print(f"{CONFIG_PATH} contains invalid JSON.")
            return {} # Return an empty dict on failure

        finally:
            # The 'with' statement handles both file closure and lock release.
            pass

def update_config_json(newdata):
    """
    Safely updates a JSON configuration file using an exclusive file lock.

    Args:
        newdata (dict): A dictionary of key-value pairs to update.
    """
    # Use 'r+' mode to open the file for both reading and writing
    if not os.path.exists(CONFIG_PATH):
        print(f"Config file not found: {CONFIG_PATH}")
        return

    with open(CONFIG_PATH, 'r+') as jfile:
        try:
            # Acquire an exclusive lock (LOCK_EX) and wait if needed
            fcntl.flock(jfile, fcntl.LOCK_EX)

            # Read the current data
            jfile.seek(0)
            try:
                data = json.load(jfile)
            except json.JSONDecodeError:
                print(f"{CONFIG_PATH} contains invalid JSON.")
                # It's better to return and not overwrite the file with an empty dict.
                return

            # Update the data from newdata
            for key, value in newdata.items():
                if key in data:
                    data[key] = value
                else:
                    print(f"Warning: Key '{key}' not found in data.")

            # Truncate the file to remove old content before writing
            jfile.seek(0)
            jfile.truncate()

            # Write the updated data
            json.dump(data, jfile, indent=4)

        finally:
            # The 'with' statement handles closing the file, which also
            # releases the lock automatically. You can explicitly unlock
            # with fcntl.flock(jfile, fcntl.LOCK_UN) as well, but it's
            # not strictly necessary when the file is closed.
            pass

####main:
_config = read_config_json()

# Validate and assign required keys
try:
    serverUrl        = _config['serverUrl']
    boxId            = _config['boxId']
    upmaxcnt         = _config['upmaxcnt']
    videodurate      = _config['videodurate']
    hflip_val        = _config['hflip_val']
    vflip_val        = _config['vflip_val']
    vidsize          = tuple(_config['vidsize']) # Convert json array to tuple
    losize           = tuple(_config['losize'])
    luxThreshold     = _config['luxThreshold']
    luxLimit         = _config['luxLimit']
    weightlimit      = _config['weightlimit']
    weightThreshold  = _config['weightThreshold']
    hxScale          = _config['hxScale']
    hxOffset         = _config['hxOffset']
    dhtPin           = _config['dhtPin']
    hxDataPin        = _config['hxDataPin']
    hxClckPin        = _config['hxClckPin']
    mdroid_key       = _config['mdroid_key']
    wapp_key         = _config['wapp_key']
    wapp_phone       = _config['wapp_phone']
    tasmota_ip       = _config['tasmota_ip']
    geoloc           = _config['geoloc']
    sun              = _config['sun']
except KeyError as e:
    # ms.log(f"Missing config key: {e}")
    raise RuntimeError(f"Missing key in config.json: {e}")
