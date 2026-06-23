import os
from dotenv import load_dotenv

load_dotenv()

# BigQuery Configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "higher-education-disability")
GCP_CREDENTIALS_PATH = os.getenv("GCP_CREDENTIALS_PATH", "credentials.json")

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "higher_education")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "students")

# BigQuery Configuration
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "ppgti_etl_test")
BIGQUERY_TABLE = os.getenv("BIGQUERY_TABLE")

# ETL Configuration - Year range
ETL_START_YEAR = int(os.getenv("ETL_START_YEAR", "2018"))
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
