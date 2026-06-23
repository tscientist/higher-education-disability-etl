"""
Setup MongoDB test resources for ETL validation.

This script creates a test database, collection, and sample document in MongoDB
to validate that the connection and permissions are working correctly.

Usage:
    python src/setup/setup_mongodb_test_resources.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


def main():
    """Main setup function."""
    try:
        print("=" * 60)
        print("MongoDB Test Resources Setup")
        print("=" * 60)
        print()
        
        # Get environment variables
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("MONGO_URI environment variable is not set")
        
        database_name = os.getenv("MONGO_DATABASE", "higher_education")
        collection_name = os.getenv("MONGO_COLLECTION", "students")
        
        print(f"Connecting to MongoDB...")
        print(f"Database: {database_name}")
        print(f"Collection: {collection_name}")
        print()
        
        # Create client with short timeouts and disable SSL verification
        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=2000,
            tlsInsecure=True
        )
        
        # Get database and collection
        db = client[database_name]
        collection = db[collection_name]
        
        # Insert test document
        print("Inserting test document...")
        test_doc = {
            "id": 1,
            "source": "etl_setup_script",
            "description": "Test document for ETL validation",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        result = collection.insert_one(test_doc)
        print(f"Test document inserted with ID: {result.inserted_id}")
        print()
        
        # Summary
        print("=" * 60)
        print("Setup Complete")
        print("=" * 60)
        print(f"Database: {database_name} - READY")
        print(f"Collection: {collection_name} - READY")
        print("=" * 60)
        
        client.close()
        return 0
        
    except ValueError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
