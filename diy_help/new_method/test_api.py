"""
Test script for API server
"""

from api_server import start_api_server, update_state
import time

if __name__ == "__main__":
    # Start the server
    print("Starting API server...")
    start_api_server(port=5000)
    
    print("\nAPI server is running!")
    print("Visit: http://localhost:5000/api/state")
    print("\nSimulating Venom activation in 3 seconds...")
    time.sleep(3)
    
    # Simulate activation
    print("\n🟢 Activating Venom...")
    update_state(is_active=True, is_listening=True)
    print("Eyes should open now!")
    
    time.sleep(5)
    
    # Deactivate
    print("\n💤 Deactivating Venom...")
    update_state(is_active=False, is_listening=False)
    print("Eyes should close now!")
    
    # Keep running
    print("\nPress Ctrl+C to stop...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
