import os
from dotenv import load_dotenv

load_dotenv()

# BigQuery Configuration
# Strip whitespace/newlines to avoid errors from CR/LF in .env values
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "higher-education-disability").strip()
GCP_CREDENTIALS_PATH = os.getenv("GCP_CREDENTIALS_PATH", "credentials.json").strip()

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI or MONGODB_URI environment variable must be set")
MONGO_DATABASE = os.getenv("MONGODB_DB", "higher_education")
MONGO_COLLECTION = os.getenv("MONGODB_COLLECTION", "students")

# BigQuery Configuration
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "ppgti_etl_test")
BIGQUERY_TABLE = os.getenv("BIGQUERY_TABLE")

# ETL Configuration - Year range
ETL_START_YEAR = int(os.getenv("ETL_START_YEAR", "2022"))
ETL_END_YEAR = int(os.getenv("ETL_END_YEAR", "2022"))

# ETL Configuration - Optional limit for test runs
ETL_LIMIT = os.getenv("ETL_LIMIT")
if ETL_LIMIT:
    ETL_LIMIT = int(ETL_LIMIT)

# BigQuery staging tables
BQ_TABLE_CENSO_IES = "stg_censo_ies"
BQ_TABLE_CENSO_CURSO = "stg_censo_curso"
BQ_TABLE_SISU_MICRODADOS = "stg_sisu_microdados"
BQ_TABLE_CENSO_DICIONARIO = "stg_censo_dicionario"

# MongoDB collections for analytical data
MONGO_COLLECTION_GOLD_COURSE = "gold_course_indicators"
MONGO_COLLECTION_SISU_AGGREGATED = "sisu_aggregated"

# ETL Batch Configuration
ETL_BATCH_SIZE = int(os.getenv("ETL_BATCH_SIZE", "20000"))
ETL_PAGE_SIZE = int(os.getenv("ETL_PAGE_SIZE", "5000"))
ETL_ENABLE_BATCH_MODE = os.getenv("ETL_ENABLE_BATCH_MODE", "true").lower() == "true"

# BigQuery intermediate/final tables for 2022
BQ_TABLE_SILVER_SISU_AGGREGATED_2022 = "silver_sisu_aggregated_2022"
BQ_TABLE_GOLD_COURSE_INDICATORS_2022 = "gold_course_indicators_source_2022"

# MongoDB checkpoint collection
MONGO_COLLECTION_CHECKPOINTS = "etl_checkpoints"