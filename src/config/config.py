import os
from dotenv import load_dotenv

load_dotenv()

# BigQuery Configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_CREDENTIALS_PATH = os.getenv("GCP_CREDENTIALS_PATH", "credentials.json")

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "higher_education")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "students")

# BigQuery Configuration
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET")
BIGQUERY_TABLE = os.getenv("BIGQUERY_TABLE")
