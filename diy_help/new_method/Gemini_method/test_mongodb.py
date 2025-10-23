"""
Test script to verify MongoDB connection and schema
"""
from pymongo import MongoClient
import time

# MongoDB connection
mongo_uri = "mongodb+srv://krish:krish@study.po9dv.mongodb.net/"

try:
    client = MongoClient(mongo_uri)
    # Test connection
    client.admin.command('ping')
    print("✅ Connected to MongoDB Atlas")

    db = client['venom']
    collection = db['state']

    # Insert test document with correct schema
    test_state = {
        "is_active": False,
        "is_listening": False,
        "is_speaking": False,
        "last_command": "",
        "timestamp": int(time.time() * 1000)
    }

    result = collection.update_one(
        {},
        {"$set": test_state},
        upsert=True
    )

    print("✅ Test document inserted/updated")
    print(f"Matched: {result.matched_count}, Modified: {result.modified_count}")

    # Read back the document
    state = collection.find_one({}, {"_id": 0})
    print("\n📄 Current state in MongoDB:")
    print(state)

    client.close()
    print("\n✅ Test completed successfully!")

except Exception as e:
    print(f"❌ Error: {e}")
