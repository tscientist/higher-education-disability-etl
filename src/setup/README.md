# Setup Scripts

This directory contains scripts to set up and validate test resources for the ETL pipeline.

## Available Scripts

### 1. BigQuery Setup
**File:** `setup_bigquery_test_resources.py`

Creates test dataset and tables in BigQuery for validation.

```bash
python src/setup/setup_bigquery_test_resources.py
```

**What it does:**
- Creates dataset `ppgti_etl_test` (if not exists)
- Creates tables: `stg_sisu_microdados`, `stg_censo_curso`, `stg_censo_ies`, `stg_censo_dicionario`
- Inserts test data
- Validates connection to BigQuery

### 2. MongoDB Setup
**File:** `setup_mongodb_test_resources.py`

Creates test database and collection in MongoDB for validation.

```bash
python src/setup/setup_mongodb_test_resources.py
```

**What it does:**
- Creates database `higher_education` (if not exists)
- Creates collection `students` (if not exists)
- Inserts test document
- Validates connection to MongoDB

### 3. Run All Setup Scripts
**File:** `run_all_setup.py`

Runs all setup scripts in sequence.

```bash
python src/setup/run_all_setup.py
```

**What it does:**
- Runs BigQuery setup
- Runs MongoDB setup
- Displays summary of all results

## Requirements

Before running any setup scripts:

1. Ensure `.env` file is configured with:
   - `GCP_PROJECT_ID`
   - `GCP_CREDENTIALS_PATH`
   - `MONGO_URI`
   - `MONGO_DATABASE`
   - `MONGO_COLLECTION`

2. Virtual environment is activated:
   ```bash
   source venv/bin/activate
   ```

3. All dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

## Recommended Setup Order

For complete validation of your ETL infrastructure:

```bash
# 1. Validate BigQuery connection
python src/setup/setup_bigquery_test_resources.py

# 2. Validate MongoDB connection
python src/setup/setup_mongodb_test_resources.py

# Or run all at once:
python src/setup/run_all_setup.py
```

## Troubleshooting

### BigQuery Setup Fails
- Check `GCP_PROJECT_ID` in `.env`
- Verify `credentials.json` exists and is valid
- Ensure service account has BigQuery permissions

### MongoDB Setup Fails
- Check `MONGO_URI` in `.env`
- Verify MongoDB Atlas cluster is running
- Ensure credentials are correct
- Check firewall/network access

## Notes

All scripts are **idempotent** - they can be run multiple times safely without causing errors if resources already exist.
