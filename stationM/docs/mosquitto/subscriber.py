import paho.mqtt.client as mqtt
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
        # Subscribe to a topic
        client.subscribe("test/topic")
    else:
        print("Failed to connect, return code %d\n", rc)

def on_message(client, userdata, msg):
    print(f"Received message: {msg.payload.decode()} on topic: {msg.topic}")

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
        pass  # Do nothing, just wait

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Clean up and disconnect gracefully
    client.loop_stop()
    client.disconnect()
    print("Disconnected from the MQTT broker.")
    sys.exit(0)