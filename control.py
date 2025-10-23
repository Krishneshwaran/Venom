import requests
import keyboard
import time
import sys

# ==== CONFIGURATION ====
# Replace with your ESP32's IP address (shown in Serial Monitor when ESP32 connects)
ESP32_IP = "192.168.97.10"  # CHANGE THIS TO YOUR ESP32 IP
BASE_URL = f"http://{ESP32_IP}"

# ==== CONTROL FUNCTIONS ====
def send_command(cmd):
    """Send a command to the ESP32"""
    try:
        response = requests.get(f"{BASE_URL}/{cmd}", timeout=1)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"Error sending command: {e}")
        return False

def set_speed(speed):
    """Set motor speed (0-100)"""
    try:
        response = requests.get(f"{BASE_URL}/speed?value={speed}", timeout=1)
        if response.status_code == 200:
            print(f"Speed set to: {speed}%")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"Error setting speed: {e}")
        return False

def forward():
    send_command('R')  # Original 'R' moves forward
    print("Moving Forward ↑")

def backward():
    send_command('L')  # Original 'L' moves backward
    print("Moving Backward ↓")

def left():
    send_command('F')  # Original 'F' turns left
    print("Turning Left ←")

def right():
    send_command('B')  # Original 'B' turns right
    print("Turning Right →")

def stop():
    send_command('S')
    print("Stopped ⏹")

# ==== KEYBOARD CONTROL MODE ====
def keyboard_control():
    """Control the car using keyboard arrow keys"""
    print("\n" + "="*50)
    print("🎮 ESP32 CAR KEYBOARD CONTROL")
    print("="*50)
    print("\nControls:")
    print("  ↑ : Forward")
    print("  ↓ : Backward")
    print("  ← : Turn Left")
    print("  → : Turn Right")
    print("  SPACE : Stop")
    print("  + : Increase Speed")
    print("  - : Decrease Speed")
    print("  Q : Quit")
    print("\nPress any key to start...")
    print("="*50 + "\n")
    
    current_speed = 80
    set_speed(current_speed)
    
    # Track which keys are currently pressed
    keys_pressed = {
        'up': False,
        'down': False,
        'left': False,
        'right': False
    }
    
    try:
        while True:
            # Check arrow keys and send stop when released
            if keyboard.is_pressed('up'):
                if not keys_pressed['up']:
                    forward()
                    keys_pressed['up'] = True
            else:
                if keys_pressed['up']:
                    stop()
                    keys_pressed['up'] = False
            
            if keyboard.is_pressed('down'):
                if not keys_pressed['down']:
                    backward()
                    keys_pressed['down'] = True
            else:
                if keys_pressed['down']:
                    stop()
                    keys_pressed['down'] = False
            
            if keyboard.is_pressed('left'):
                if not keys_pressed['left']:
                    left()
                    keys_pressed['left'] = True
            else:
                if keys_pressed['left']:
                    stop()
                    keys_pressed['left'] = False
            
            if keyboard.is_pressed('right'):
                if not keys_pressed['right']:
                    right()
                    keys_pressed['right'] = True
            else:
                if keys_pressed['right']:
                    stop()
                    keys_pressed['right'] = False
            
            # Space bar for manual stop
            if keyboard.is_pressed('space'):
                stop()
                time.sleep(0.2)
            
            # Speed controls
            if keyboard.is_pressed('+') or keyboard.is_pressed('='):
                current_speed = min(100, current_speed + 10)
                set_speed(current_speed)
                time.sleep(0.3)
            elif keyboard.is_pressed('-'):
                current_speed = max(0, current_speed - 10)
                set_speed(current_speed)
                time.sleep(0.3)
            
            # Quit
            if keyboard.is_pressed('q'):
                print("\nExiting...")
                stop()
                break
            
            time.sleep(0.05)  # Small delay to prevent CPU overload
            
    except KeyboardInterrupt:
        print("\nStopping car...")
        stop()
        print("Goodbye!")

# ==== PROGRAMMATIC CONTROL MODE ====
def programmatic_control():
    """Example of programmatic control - create your own patterns!"""
    print("\n🤖 Running Programmatic Control Demo...")
    print("The car will execute a preset movement pattern.\n")
    
    # Set speed
    set_speed(70)
    time.sleep(0.5)
    
    # Move forward
    print("1. Moving forward for 2 seconds...")
    forward()
    time.sleep(2)
    
    # Turn right
    print("2. Turning right for 1 second...")
    right()
    time.sleep(1)
    
    # Move forward
    print("3. Moving forward for 2 seconds...")
    forward()
    time.sleep(2)
    
    # Turn right
    print("4. Turning right for 1 second...")
    right()
    time.sleep(1)
    
    # Move forward
    print("5. Moving forward for 2 seconds...")
    forward()
    time.sleep(2)
    
    # Stop
    print("6. Stopping...")
    stop()
    
    print("\n✅ Demo complete!")

# ==== TEST CONNECTION ====
def test_connection():
    """Test if ESP32 is reachable"""
    print(f"Testing connection to ESP32 at {BASE_URL}...")
    try:
        response = requests.get(BASE_URL, timeout=2)
        if response.status_code == 200:
            print("✅ Connection successful!")
            return True
        else:
            print(f"❌ Connection failed. Status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to ESP32: {e}")
        print(f"\nMake sure:")
        print(f"  1. ESP32 is powered on")
        print(f"  2. ESP32 is connected to WiFi")
        print(f"  3. Your computer is on the same network")
        print(f"  4. ESP32_IP is set correctly (currently: {ESP32_IP})")
        return False

# ==== MAIN MENU ====
def main():
    print("\n" + "="*50)
    print("ESP32 ROBOT CAR CONTROLLER")
    print("="*50)
    
    # Test connection first
    if not test_connection():
        sys.exit(1)
    
    print("\nSelect Control Mode:")
    print("  1. Keyboard Control (Interactive)")
    print("  2. Programmatic Control (Demo Pattern)")
    print("  3. Exit")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == '1':
        keyboard_control()
    elif choice == '2':
        programmatic_control()
    elif choice == '3':
        print("Goodbye!")
        sys.exit(0)
    else:
        print("Invalid choice!")
        sys.exit(1)

if __name__ == "__main__":
    main()