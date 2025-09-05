import paho.mqtt.client as mqtt
import time
import struct
import json
import os

broker_address = "localhost"
port = 1883

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print("Failed to connect, return code %d\n", rc)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.connect(broker_address, port, 60)
client.loop_start()

# Publish a simple string
client.publish("test/string", "Hello, Mosquitto!")
print("Published string message")

# Publish a decimal as a binary payload
my_float = 3.14
float_binary_data = struct.pack('f', my_float)
client.publish("test/float_binary", float_binary_data)
print("Published float as binary data")

# Publish an image
fname = 'test.jpg'
if os.path.exists(fname):
    with open(fname, 'rb') as f:
        bin_data = f.read()
    client.publish("test/img", bin_data)
    print(f"Published '{fname}'")
else:
    print(f"Error: Image file '{fname}' not found.")

# Publish a JSON string
sensor_data = {
    "device_id": "sensor_01",
    "timestamp": int(time.time()),
    "temperature_c": 24.5,
    "humidity_percent": 60
}
json_payload = json.dumps(sensor_data)
client.publish("sensors/data", json_payload)
print("Published JSON payload")

# A single, short sleep is needed to give the loop thread time to process the queue.
time.sleep(1)

client.loop_stop()
client.disconnect()
print("Disconnected from MQTT broker.")