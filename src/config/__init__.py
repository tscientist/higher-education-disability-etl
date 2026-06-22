"""
Configuration module for ETL pipeline
"""

from src.config.config import (
    GCP_CREDENTIALS_PATH,
    GCP_PROJECT_ID,
    BIGQUERY_DATASET,
    BIGQUERY_TABLE,
    MONGO_COLLECTION,
    MONGO_DATABASE,
    MONGO_URI,
)

__all__ = [
    "GCP_PROJECT_ID",
    "GCP_CREDENTIALS_PATH",
    "MONGO_URI",
    "MONGO_DATABASE",
    "MONGO_COLLECTION",
    "BIGQUERY_DATASET",
    "BIGQUERY_TABLE",
]
