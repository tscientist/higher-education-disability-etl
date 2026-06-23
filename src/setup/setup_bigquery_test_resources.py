"""
Setup BigQuery test resources for ETL validation.

This script creates a test dataset and table in BigQuery to validate
that the service account has proper access. It is idempotent and can
be run multiple times safely.

Usage:
    python src/setup/setup_bigquery_test_resources.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from google.cloud import bigquery
from google.cloud.exceptions import Conflict

# Load .env from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Set GOOGLE_APPLICATION_CREDENTIALS if not already set
credentials_path = os.getenv("GCP_CREDENTIALS_PATH", "credentials.json")
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    if not Path(credentials_path).is_absolute():
        credentials_path = Path(__file__).parent.parent / credentials_path
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)


def get_bigquery_client():
    """
    Initialize and return a BigQuery client.
    
    Uses credentials from GOOGLE_APPLICATION_CREDENTIALS environment variable.
    
    Returns:
        bigquery.Client: Authenticated BigQuery client
        
    Raises:
        ValueError: If GCP_PROJECT_ID is not set in environment
    """
    project_id = os.getenv("GCP_PROJECT_ID")
    if not project_id:
        raise ValueError("GCP_PROJECT_ID environment variable is not set")
    
    return bigquery.Client(project=project_id)


def create_dataset(client, dataset_id):
    """
    Create a BigQuery dataset if it does not exist.
    
    Args:
        client (bigquery.Client): Authenticated BigQuery client
        dataset_id (str): Dataset ID (e.g., 'ppgti_etl_test')
        
    Returns:
        tuple: (dataset, created) where created is True if dataset was created,
               False if it already existed
    """
    dataset_ref = f"{client.project}.{dataset_id}"
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = "US"
    
    try:
        dataset = client.create_dataset(dataset, exists_ok=False)
        print(f"Dataset '{dataset_id}' created successfully in project '{client.project}'")
        return dataset, True
    except Conflict:
        dataset = client.get_dataset(dataset_id)
        print(f"Dataset '{dataset_id}' already exists in project '{client.project}'")
        return dataset, False


def create_test_table(client, dataset_id, table_id):
    """
    Create a test table in the dataset if it does not exist.
    
    Table schema:
    - id (INTEGER): Unique identifier
    - source (STRING): Source of the test data
    - description (STRING): Description of the test
    - created_at (TIMESTAMP): Timestamp when row was created
    
    Args:
        client (bigquery.Client): Authenticated BigQuery client
        dataset_id (str): Dataset ID
        table_id (str): Table ID (e.g., 'etl_test_table')
        
    Returns:
        tuple: (table, created) where created is True if table was created,
               False if it already existed
    """
    table_ref = f"{client.project}.{dataset_id}.{table_id}"
    
    schema = [
        bigquery.SchemaField("id", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("source", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("description", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    
    table = bigquery.Table(table_ref, schema=schema)
    
    try:
        table = client.create_table(table)
        print(f"Table '{dataset_id}.{table_id}' created successfully")
        return table, True
    except Conflict:
        table = client.get_table(table_ref)
        print(f"Table '{dataset_id}.{table_id}' already exists")
        return table, False


def insert_test_row(client, dataset_id, table_id):
    """
    Insert a test row into the table.
    
    Args:
        client (bigquery.Client): Authenticated BigQuery client
        dataset_id (str): Dataset ID
        table_id (str): Table ID
        
    Returns:
        bool: True if insertion was successful
    """
    table_id_full = f"{client.project}.{dataset_id}.{table_id}"
    
    test_row = {
        "id": 1,
        "source": "etl_setup_script",
        "description": f"Test row inserted at {datetime.utcnow().isoformat()}",
        "created_at": datetime.utcnow().isoformat(),
    }
    
    errors = client.insert_rows_json(table_id_full, [test_row])
    
    if errors:
        print(f"Error inserting test row: {errors}")
        return False
    
    print(f"Test row inserted successfully into '{dataset_id}.{table_id}'")
    return True


def main():
    """Main setup function."""
    try:
        print("=" * 60)
        print("BigQuery Test Resources Setup")
        print("=" * 60)
        print()
        
        # Initialize BigQuery client
        client = get_bigquery_client()
        print(f"Connected to GCP project: {client.project}")
        print()
        
        # Create dataset
        dataset_id = "ppgti_etl_test"
        print(f"Setting up dataset '{dataset_id}'...")
        dataset, dataset_created = create_dataset(client, dataset_id)
        print()
        
        # Create table
        table_id = "etl_test_table"
        print(f"Setting up table '{table_id}'...")
        table, table_created = create_test_table(client, dataset_id, table_id)
        print()
        
        # Insert test row
        print("Inserting test row...")
        insert_test_row(client, dataset_id, table_id)
        print()
        
        # Summary
        print("=" * 60)
        print("Setup Complete")
        print("=" * 60)
        print(f"Dataset '{dataset_id}': {'CREATED' if dataset_created else 'ALREADY EXISTS'}")
        print(f"Table '{table_id}': {'CREATED' if table_created else 'ALREADY EXISTS'}")
        print()
        print("You can now query the test table:")
        print(f"  SELECT * FROM `{client.project}.{dataset_id}.{table_id}`")
        print()
        
        return 0
        
    except ValueError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())