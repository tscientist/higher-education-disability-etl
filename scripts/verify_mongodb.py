"""
MongoDB verification script

Checks MongoDB connection and collections exist
"""

import os
import sys
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from dotenv import load_dotenv

load_dotenv()


def verify_mongodb():
    """Verifies MongoDB connection and collections"""
    
    mongo_uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI or MONGODB_URI environment variable must be set")
    database_name = os.getenv("MONGO_DATABASE", "higher_education")
    
    print(f"\n{'='*80}")
    print("MONGODB VERIFICATION")
    print(f"{'='*80}\n")
    
    print(f"MongoDB URI:  {mongo_uri}")
    print(f"Database:     {database_name}\n")
    
    try:
        # Connect
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        print("MongoDB connection: OK\n")
        
        # Get database
        db = client[database_name]
        
        # Check collections
        collections = db.list_collection_names()
        
        print(f"Collections in '{database_name}':")
        print("-" * 80)
        
        if not collections:
            print("  (No collections found)")
        else:
            for collection in sorted(collections):
                col = db[collection]
                count = col.count_documents({})
                indexes = len(list(col.list_indexes()))
                
                print(f"  {collection}")
                print(f"    Documents: {count:,}")
                print(f"    Indexes:   {indexes}")
                print()
        
        # Check for analytical collections
        print("\nAnalytical Collections Status:")
        print("-" * 80)
        
        gold_col = db["gold_course_indicators"]
        if "gold_course_indicators" in collections:
            count = gold_col.count_documents({})
            print(f" gold_course_indicators: {count:,} documents")
            
            # Sample document
            sample = gold_col.find_one()
            if sample:
                print(f"    Sample ID: {sample.get('_id')}")
                print(f"    Year: {sample.get('ano')}")
        else:
            print(" gold_course_indicators: NOT FOUND")
        
        sisu_col = db["sisu_aggregated"]
        if "sisu_aggregated" in collections:
            count = sisu_col.count_documents({})
            print(f" sisu_aggregated: {count:,} documents")
        else:
            print(" sisu_aggregated: NOT FOUND (optional)")
        
        print("\n" + "="*80)
        print("MongoDB verification complete!")
        print("="*80 + "\n")
        
        client.close()
        return True
        
    except ServerSelectionTimeoutError:
        print(f"MongoDB connection FAILED")
        print(f"  Cannot reach MongoDB at {mongo_uri}")
        print(f"\n  Make sure MongoDB is running:")
        print(f"  - Local: mongod --dbpath /path/to/data")
        print(f"  - Docker: docker-compose up mongo")
        print(f"  - Cloud: Check connection string and IP whitelist\n")
        return False
    except Exception as e:
        print(f"Error: {e}\n")
        return False


if __name__ == "__main__":
    success = verify_mongodb()
    sys.exit(0 if success else 1)
