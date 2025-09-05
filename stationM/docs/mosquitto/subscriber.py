import paho.mqtt.client as mqtt
import struct
import json
import signal
import sys

# Define the MQTT broker's address and port
broker_address = "localhost"
port = 1883

# Flag to indicate if the script should terminate
terminated = False

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Connected to MQTT Broker!")
        # Subscribe to all relevant topics
        client.subscribe("test/string")
        client.subscribe("test/float_binary")
        client.subscribe("test/img")
        client.subscribe("sensors/data")
    else:
        print("Failed to connect, return code %d\n", rc)

def on_message(client, userdata, msg):
    if msg.topic == "test/string":
        # Decode string payload using UTF-8
        received_string = msg.payload.decode('utf-8')
        print(f"Received string '{received_string}' on topic: {msg.topic}")
    
    elif msg.topic == "test/float_binary":
        # Unpack binary payload to a float
        # 'f' is for a standard float, matching the publisher's pack format
        received_float = struct.unpack('f', msg.payload)[0]
        print(f"Received float {received_float} on topic: {msg.topic}")
        # or simply: received_float = float(msg.payload.decode('utf-8'))
    
    elif msg.topic == "test/img":
        # Save the raw binary payload to an image file
        file_name = "received.jpg"
        with open(file_name, 'wb') as f:
            f.write(msg.payload)
        print(f"Received and saved image to '{file_name}' on topic: {msg.topic}")

    elif msg.topic == "sensors/data":
        # json received
        try:
            # 1. Decode the binary payload to a UTF-8 string
            json_string = msg.payload.decode('utf-8')
            
            # 2. Deserialize the JSON string to a Python dictionary
            received_dict = json.loads(json_string)
            
            # 3. Access the dictionary values
            print(f"Received JSON data on topic: {msg.topic}")
            print(f"Device ID: {received_dict['device_id']}")
            print(f"Temperature: {received_dict['temperature_c']} C")
            print(f"Humidity: {received_dict['humidity_percent']}%")
            print("-" * 20)
            
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON payload: {e}")

    else:
        # Fallback for unexpected topics
        print(f"Received message on unknown topic: {msg.topic}")

def signal_handler(sig, frame):
    """
    Handles keyboard interrupts and termination signals.
    """
    print("\nTermination signal received. Exiting gracefully...")
    global terminated
    terminated = True

# Register the signal handler for SIGINT (Ctrl+C) and SIGTERM (kill)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

try:
    # Use VERSION2 when initializing the client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(broker_address, port, 60)

    # Use loop_start() in a loop to handle network traffic
    client.loop_start()

    # Wait until the termination flag is set
    while not terminated:
        pass

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Clean up and disconnect gracefully
    client.loop_stop()
    client.disconnect()
    print("Disconnected from the MQTT broker.")
    sys.exit(0)