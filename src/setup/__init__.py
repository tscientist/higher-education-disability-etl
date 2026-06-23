"""
Setup utilities for test resources.

This module contains scripts to set up test resources for both BigQuery and MongoDB.

Available setup scripts:
- setup_bigquery_test_resources.py - Creates BigQuery test dataset and tables
- setup_mongodb_test_resources.py - Creates MongoDB test database and collection
"""

__all__ = [
    "get_bigquery_client",
    "create_dataset",
    "create_test_table",
    "insert_test_row",
]
