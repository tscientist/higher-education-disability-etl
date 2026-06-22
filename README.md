# Higher Education Disability ETL

ETL pipeline for analyzing the distribution of students with disabilities in Brazilian higher education, integrating Higher Education Census and SISU data into MongoDB.

## Data Preparation Overview

Before running the ETL pipeline, the raw Higher Education Census microdata files must be prepared and loaded into BigQuery.

The current data preparation flow is:

```text
INEP CSV files → Parquet files → Google Cloud Storage → BigQuery → MongoDB
```

The conversion from CSV to Parquet is performed by a local Python script. The upload to Google Cloud Storage is currently a manual step performed through the Google Cloud CLI.

## Preparing INEP Microdata

The Higher Education Census microdata files are originally provided by INEP in CSV format. Before loading them into BigQuery, the files must be converted to Parquet.

Place the original INEP CSV files inside:

```bash
data/raw/
```

Expected files:

```bash
data/raw/microdados_ed_sup_ies_2024.csv
data/raw/microdados_cadastro_cursos_2024.csv
```

Run the conversion script:

```bash
python scripts/convert_to_parquet.py
```

The generated Parquet files will be saved in:

```bash
data/parquet/
```

Expected output:

```bash
data/parquet/microdados_ed_sup_ies_2024.parquet
data/parquet/microdados_cadastro_cursos_2024.parquet
```

The conversion script requires:

```bash
pandas
pyarrow
```

If needed, install them with:

```bash
python -m pip install pandas pyarrow
```

## Uploading Parquet Files to Google Cloud Storage

After generating the Parquet files, they must be uploaded to Google Cloud Storage.

At this stage of the project, the upload process is manual and performed through the Google Cloud CLI.

### 1. Authenticate with Google Cloud

```bash
gcloud auth login
```

### 2. Select the GCP project

```bash
gcloud config set project YOUR_GCP_PROJECT_ID
```

Confirm the active configuration:

```bash
gcloud config list
```

### 3. Define the bucket and destination path

Replace the bucket name with the bucket used by the project:

```bash
export BUCKET_NAME="your-bucket-name"
export GCS_PATH="microdados/educacao_superior/2024/parquet"
```

The final destination will be:

```bash
gs://your-bucket-name/microdados/educacao_superior/2024/parquet/
```

### 4. Upload the generated Parquet files

```bash
gcloud storage cp data/parquet/*.parquet gs://$BUCKET_NAME/$GCS_PATH/
```

### 5. Validate the uploaded files

```bash
gcloud storage ls gs://$BUCKET_NAME/$GCS_PATH/
```

Expected result:

```bash
gs://your-bucket-name/microdados/educacao_superior/2024/parquet/microdados_ed_sup_ies_2024.parquet
gs://your-bucket-name/microdados/educacao_superior/2024/parquet/microdados_cadastro_cursos_2024.parquet
```

### Notes

* The Cloud Storage bucket location must be compatible with the BigQuery dataset location.
* The upload step is currently manual and must be executed after generating the Parquet files.
* Future versions of this project may automate the upload process directly from the ETL pipeline.

## Loading Parquet Files into BigQuery

After the files are uploaded to Cloud Storage, they can be loaded into BigQuery as raw tables.

Suggested raw tables:

```text
raw_ies_2024
raw_cursos_2024
```

Suggested source files:

```text
gs://your-bucket-name/microdados/educacao_superior/2024/parquet/microdados_ed_sup_ies_2024.parquet
gs://your-bucket-name/microdados/educacao_superior/2024/parquet/microdados_cadastro_cursos_2024.parquet
```

These raw BigQuery tables will later be used by the ETL pipeline to transform and load the data into MongoDB.

## Loading Parquet Files from Cloud Storage into BigQuery

After uploading the generated Parquet files to Google Cloud Storage, the files must be loaded into BigQuery as raw tables.

This step is currently performed manually through the Google Cloud CLI.

The flow is:

```text
Local Parquet files → Google Cloud Storage → BigQuery raw tables → MongoDB
