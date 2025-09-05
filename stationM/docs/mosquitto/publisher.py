import paho.mqtt.client as mqtt
import time

# Define the MQTT broker's address and port
broker_address = "localhost"
port = 1883

# Note the extra `properties` argument in the on_connect function
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print("Failed to connect, return code %d\n", rc)

# Use VERSION2 when initializing the client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.connect(broker_address, port, 60)

# The blocking call that processes network traffic, dispatches callbacks, and handles reconnecting.
client.loop_start()

# Publish a message
topic = "test/topic"
message = "Hello, Mosquitto!"
client.publish(topic, message)
print(f"Published message '{message}' to topic '{topic}'")

# Give the client some time to send the message
time.sleep(1)

# Stop the loop and disconnect
client.loop_stop()
client.disconnect()