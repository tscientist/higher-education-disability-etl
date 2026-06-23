#!/usr/bin/env python
"""Test script to verify MongoDB bulk_write"""

from src.etl.fase_7_mongodb_load import Fase7MongoDBLoad
import logging

logging.basicConfig(level=logging.INFO)

# Test the load_batch method
phase7 = Fase7MongoDBLoad()

# Create sample batch documents with reasonable size
sample_batch = []
for i in range(100):  # Test with 100 docs first
    sample_batch.append({
        "ano": 2023,
        "id_ies": i % 10,
        "id_curso": i,
        "nome_curso": f"Test Course {i}",
        "estudantes_pcd": i % 5,
        "_id": f"test_{i}"  # Include _id to test if it's properly removed
    })

print("Testing load_batch method with bulk_write...")
try:
    result = phase7.load_batch(sample_batch, batch_number=1)
    print(f"Success! Result: {result}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
