"""
Venom AI Assistant - API Test Script
Tests all API endpoints to ensure everything is working
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.RESET}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.RESET}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.RESET}")

def test_health_check():
    """Test health check endpoint"""
    print_info("Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print_success(f"Health check passed - Status: {data['status']}")
            print(f"   Camera available: {data['camera_available']}")
            print(f"   Security active: {data['security_active']}")
            return True
        else:
            print_error(f"Health check failed - Status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Health check error: {e}")
        return False

def test_memory_save():
    """Test memory save endpoint"""
    print_info("Testing memory save...")
    try:
        response = requests.post(f"{BASE_URL}/memory/save", json={
            "memory_text": "Test memory - My favorite programming language is Python",
            "context": "API test"
        })
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print_success("Memory saved successfully")
                return True
        print_error(f"Memory save failed: {response.json()}")
        return False
    except Exception as e:
        print_error(f"Memory save error: {e}")
        return False

def test_memory_search():
    """Test memory search endpoint"""
    print_info("Testing memory search...")
    try:
        response = requests.post(f"{BASE_URL}/memory/search", json={
            "query": "programming language",
            "max_results": 5
        })
        if response.status_code == 200:
            data = response.json()
            print_success(f"Memory search successful - Found {data['count']} memories")
            if data['memories']:
                print(f"   First result: {data['memories'][0]['memory'][:50]}...")
            return True
        print_error(f"Memory search failed: {response.json()}")
        return False
    except Exception as e:
        print_error(f"Memory search error: {e}")
        return False

def test_memory_tamil():
    """Test memory with Tamil language"""
    print_info("Testing Tamil memory support...")
    try:
        # Save Tamil memory
        response = requests.post(f"{BASE_URL}/memory/save", json={
            "memory_text": "என் பெயர் Kavin - My name is Kavin",
            "context": "Tamil test"
        })
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print_success("Tamil memory saved successfully")
                
                # Search Tamil memory
                response2 = requests.post(f"{BASE_URL}/memory/search", json={
                    "query": "peyar",
                    "max_results": 5
                })
                if response2.status_code == 200:
                    data2 = response2.json()
                    print_success(f"Tamil memory search successful - Found {data2['count']} memories")
                    return True
        print_error("Tamil memory test failed")
        return False
    except Exception as e:
        print_error(f"Tamil memory error: {e}")
        return False

def test_reminder_create():
    """Test reminder creation"""
    print_info("Testing reminder creation...")
    try:
        response = requests.post(f"{BASE_URL}/reminder/create", json={
            "task": "API test reminder",
            "time_description": "5 minutes"
        })
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print_success(f"Reminder created - Will remind at {data['remind_time']}")
                return True
        print_error(f"Reminder creation failed: {response.json()}")
        return False
    except Exception as e:
        print_error(f"Reminder creation error: {e}")
        return False

def test_ai_query_text():
    """Test AI text-only query"""
    print_info("Testing AI text query...")
    try:
        response = requests.post(f"{BASE_URL}/ai/query", json={
            "query": "What is the capital of France?",
            "image_base64": None,
            "include_memory_context": False
        })
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print_success("AI query successful")
                print(f"   Response: {data['response'][:100]}...")
                return True
        print_error(f"AI query failed: {response.json()}")
        return False
    except Exception as e:
        print_error(f"AI query error: {e}")
        return False

def test_conversation_save():
    """Test conversation save"""
    print_info("Testing conversation save...")
    try:
        response = requests.post(f"{BASE_URL}/conversation/save", json={
            "question": "What is AI?",
            "response": "AI stands for Artificial Intelligence"
        })
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print_success("Conversation saved successfully")
                return True
        print_error(f"Conversation save failed: {response.json()}")
        return False
    except Exception as e:
        print_error(f"Conversation save error: {e}")
        return False

def test_conversation_history():
    """Test conversation history retrieval"""
    print_info("Testing conversation history...")
    try:
        response = requests.get(f"{BASE_URL}/conversation/history?limit=5")
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print_success(f"Conversation history retrieved - {data['count']} entries")
                return True
        print_error(f"Conversation history failed: {response.json()}")
        return False
    except Exception as e:
        print_error(f"Conversation history error: {e}")
        return False

def test_process_command():
    """Test natural language command processing"""
    print_info("Testing command processing...")
    try:
        response = requests.post(f"{BASE_URL}/ai/process-command", json={
            "text": "remember my birthday is January 15th",
            "language": "en"
        })
        if response.status_code == 200:
            data = response.json()
            print_success(f"Command processed - Intent: {data['intent']}")
            print(f"   Response: {data.get('response', 'N/A')}")
            return True
        print_error(f"Command processing failed: {response.json()}")
        return False
    except Exception as e:
        print_error(f"Command processing error: {e}")
        return False

def test_tts():
    """Test text-to-speech"""
    print_info("Testing text-to-speech...")
    try:
        response = requests.post(f"{BASE_URL}/tts/speak", json={
            "text": "Testing Venom API text to speech",
            "save_audio": False
        })
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print_success("TTS request queued successfully")
                return True
        print_error(f"TTS failed: {response.json()}")
        return False
    except Exception as e:
        print_error(f"TTS error: {e}")
        return False

def test_all_reminders():
    """Test get all reminders"""
    print_info("Testing get all reminders...")
    try:
        response = requests.get(f"{BASE_URL}/reminder/all")
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print_success(f"Retrieved {data['count']} reminders")
                return True
        print_error(f"Get reminders failed: {response.json()}")
        return False
    except Exception as e:
        print_error(f"Get reminders error: {e}")
        return False

def test_all_memories():
    """Test get all memories"""
    print_info("Testing get all memories...")
    try:
        response = requests.get(f"{BASE_URL}/memory/all")
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print_success(f"Retrieved {data['count']} memories")
                return True
        print_error(f"Get memories failed: {response.json()}")
        return False
    except Exception as e:
        print_error(f"Get memories error: {e}")
        return False

def run_all_tests():
    """Run all tests and generate report"""
    print("\n" + "=" * 60)
    print(f"{Colors.BLUE}🧪 VENOM AI ASSISTANT - API TEST SUITE{Colors.RESET}")
    print("=" * 60 + "\n")
    
    tests = [
        ("Health Check", test_health_check),
        ("Memory Save", test_memory_save),
        ("Memory Search", test_memory_search),
        ("Tamil Memory Support", test_memory_tamil),
        ("Reminder Creation", test_reminder_create),
        ("AI Text Query", test_ai_query_text),
        ("Conversation Save", test_conversation_save),
        ("Conversation History", test_conversation_history),
        ("Command Processing", test_process_command),
        ("Text-to-Speech", test_tts),
        ("Get All Reminders", test_all_reminders),
        ("Get All Memories", test_all_memories),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'─' * 60}")
        print(f"📋 Test: {test_name}")
        print('─' * 60)
        
        try:
            result = test_func()
            results.append((test_name, result))
            time.sleep(0.5)  # Small delay between tests
        except Exception as e:
            print_error(f"Test crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"{Colors.BLUE}📊 TEST SUMMARY{Colors.RESET}")
    print("=" * 60 + "\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Colors.GREEN}✅ PASSED{Colors.RESET}" if result else f"{Colors.RED}❌ FAILED{Colors.RESET}"
        print(f"{test_name:.<50} {status}")
    
    print("\n" + "─" * 60)
    
    success_rate = (passed / total) * 100
    if success_rate == 100:
        print(f"{Colors.GREEN}🎉 ALL TESTS PASSED! ({passed}/{total}){Colors.RESET}")
    elif success_rate >= 80:
        print(f"{Colors.YELLOW}⚠️  MOST TESTS PASSED ({passed}/{total}) - {success_rate:.1f}%{Colors.RESET}")
    else:
        print(f"{Colors.RED}❌ MANY TESTS FAILED ({passed}/{total}) - {success_rate:.1f}%{Colors.RESET}")
    
    print("=" * 60 + "\n")
    
    return success_rate == 100

if __name__ == "__main__":
    print(f"\n{Colors.BLUE}Starting Venom AI Assistant API Tests...{Colors.RESET}")
    print(f"Target: {BASE_URL}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Check if API is running
    try:
        response = requests.get(BASE_URL, timeout=5)
        print_success("API is reachable")
    except Exception as e:
        print_error(f"Cannot connect to API at {BASE_URL}")
        print_warning("Make sure the API is running: python api.py")
        exit(1)
    
    # Run tests
    success = run_all_tests()
    
    if success:
        print(f"{Colors.GREEN}✨ All systems operational!{Colors.RESET}\n")
        exit(0)
    else:
        print(f"{Colors.YELLOW}⚠️  Some tests failed. Check the output above.{Colors.RESET}\n")
        exit(1)