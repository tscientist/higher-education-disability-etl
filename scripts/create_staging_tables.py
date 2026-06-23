import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account


load_dotenv()


@dataclass
class StagingTableConfig:
    name: str
    source_table: str
    destination_table: str
    create_sql: str
    source_validation_sql: str
    destination_validation_sql: str


def get_bigquery_client() -> bigquery.Client:
    project_id = os.getenv("GCP_PROJECT_ID")
    credentials_path = os.getenv("GCP_CREDENTIALS_PATH")

    if not project_id:
        raise ValueError("GCP_PROJECT_ID is not configured in .env")

    if credentials_path and os.path.exists(credentials_path):
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        return bigquery.Client(project=project_id, credentials=credentials)

    return bigquery.Client(project=project_id)


def run_query(
    client: bigquery.Client,
    sql: str,
    description: str,
) -> bigquery.table.RowIterator:
    print(f"\nRunning: {description}")
    query_job = client.query(sql)
    result = query_job.result()
    print(f"Finished: {description}")
    return result


def get_count(client: bigquery.Client, sql: str) -> int:
    result = run_query(client, sql, "validation count")
    row = next(iter(result))
    return row["total_registros"]


def validate_table_copy(client: bigquery.Client, config: StagingTableConfig) -> None:
    source_count = get_count(client, config.source_validation_sql)
    destination_count = get_count(client, config.destination_validation_sql)

    print(f"\nValidation for {config.destination_table}")
    print(f"Source count:      {source_count}")
    print(f"Destination count: {destination_count}")

    if source_count != destination_count:
        raise ValueError(
            f"Validation failed for {config.destination_table}. "
            f"Source count: {source_count}, destination count: {destination_count}"
        )

    print("Status: Match - copy successful")


def main() -> None:
    project_id = os.getenv("GCP_PROJECT_ID")
    dataset_id = os.getenv("BIGQUERY_DATASET")

    if not project_id:
        raise ValueError("GCP_PROJECT_ID is not configured in .env")

    if not dataset_id:
        raise ValueError("BIGQUERY_DATASET is not configured in .env")

    destination_dataset = f"{project_id}.{dataset_id}"

    configs = [
        StagingTableConfig(
            name="SISU microdados",
            source_table="basedosdados.br_mec_sisu.microdados",
            destination_table=f"{destination_dataset}.stg_sisu_microdados",
            create_sql=f"""
                CREATE OR REPLACE TABLE `{destination_dataset}.stg_sisu_microdados` AS
                SELECT *
                FROM `basedosdados.br_mec_sisu.microdados`
                WHERE ano BETWEEN 2018 AND 2022
            """,
            source_validation_sql="""
                SELECT COUNT(*) AS total_registros
                FROM `basedosdados.br_mec_sisu.microdados`
                WHERE ano BETWEEN 2018 AND 2022
            """,
            destination_validation_sql=f"""
                SELECT COUNT(*) AS total_registros
                FROM `{destination_dataset}.stg_sisu_microdados`
            """,
        ),
        StagingTableConfig(
            name="Censo curso",
            source_table="basedosdados.br_inep_censo_educacao_superior.curso",
            destination_table=f"{destination_dataset}.stg_censo_curso",
            create_sql=f"""
                CREATE OR REPLACE TABLE `{destination_dataset}.stg_censo_curso` AS
                SELECT *
                FROM `basedosdados.br_inep_censo_educacao_superior.curso`
                WHERE ano BETWEEN 2018 AND 2022
            """,
            source_validation_sql="""
                SELECT COUNT(*) AS total_registros
                FROM `basedosdados.br_inep_censo_educacao_superior.curso`
                WHERE ano BETWEEN 2018 AND 2022
            """,
            destination_validation_sql=f"""
                SELECT COUNT(*) AS total_registros
                FROM `{destination_dataset}.stg_censo_curso`
            """,
        ),
        StagingTableConfig(
            name="Censo IES",
            source_table="basedosdados.br_inep_censo_educacao_superior.ies",
            destination_table=f"{destination_dataset}.stg_censo_ies",
            create_sql=f"""
                CREATE OR REPLACE TABLE `{destination_dataset}.stg_censo_ies` AS
                SELECT *
                FROM `basedosdados.br_inep_censo_educacao_superior.ies`
                WHERE ano BETWEEN 2018 AND 2022
            """,
            source_validation_sql="""
                SELECT COUNT(*) AS total_registros
                FROM `basedosdados.br_inep_censo_educacao_superior.ies`
                WHERE ano BETWEEN 2018 AND 2022
            """,
            destination_validation_sql=f"""
                SELECT COUNT(*) AS total_registros
                FROM `{destination_dataset}.stg_censo_ies`
            """,
        ),
        StagingTableConfig(
            name="Censo dicionario",
            source_table="basedosdados.br_inep_censo_educacao_superior.dicionario",
            destination_table=f"{destination_dataset}.stg_censo_dicionario",
            create_sql=f"""
                CREATE OR REPLACE TABLE `{destination_dataset}.stg_censo_dicionario` AS
                SELECT *
                FROM `basedosdados.br_inep_censo_educacao_superior.dicionario`
                WHERE id_tabela IN ('curso', 'ies')
            """,
            source_validation_sql="""
                SELECT COUNT(*) AS total_registros
                FROM `basedosdados.br_inep_censo_educacao_superior.dicionario`
                WHERE id_tabela IN ('curso', 'ies')
            """,
            destination_validation_sql=f"""
                SELECT COUNT(*) AS total_registros
                FROM `{destination_dataset}.stg_censo_dicionario`
            """,
        ),
    ]

    client = get_bigquery_client()

    print("Destination dataset")
    print(f"Project: {project_id}")
    print(f"Dataset: {dataset_id}")

    for config in configs:
        print("\n" + "=" * 80)
        print(f"Creating staging table: {config.destination_table}")
        print(f"Source table: {config.source_table}")

        run_query(
            client=client,
            sql=config.create_sql,
            description=f"create or replace {config.destination_table}",
        )

        validate_table_copy(client, config)

    print("\nAll staging tables were created and validated successfully.")


if __name__ == "__main__":
    main()