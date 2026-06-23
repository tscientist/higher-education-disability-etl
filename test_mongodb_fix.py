#!/usr/bin/env python
"""Test script to verify MongoDB load fix"""

from src.etl.fase_7_mongodb_load import Fase7MongoDBLoad
import logging

logging.basicConfig(level=logging.DEBUG)

# Test the load_batch method
phase7 = Fase7MongoDBLoad()

# Create sample batch documents
sample_batch = [
    {
        "ano": 2023,
        "id_ies": 1,
        "id_curso": 100,
        "nome_curso": "Test Course",
        "estudantes_pcd": 5
    },
    {
        "ano": 2023,
        "id_ies": 1,
        "id_curso": 101,
        "nome_curso": "Test Course 2",
        "estudantes_pcd": 3
    }
]

print("Testing load_batch method...")
try:
    result = phase7.load_batch(sample_batch, batch_number=1)
    print(f"Success! Result: {result}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
