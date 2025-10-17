import requests
import time

# Replace with your ESP32 IP printed in Serial Monitor
ESP32_IP = "192.168.1.32"  # Example, change to your ESP32 IP

# Function to send a command
def send_cmd(cmd):
    url = f"http://{ESP32_IP}/{cmd}"
    try:
        response = requests.get(url, timeout=2)
        print(f"Sent {cmd}, response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending {cmd}: {e}")

# Move forward
send_cmd("F")
time.sleep(2)

# Stop
send_cmd("S")
