"""
BigQuery intermediate table creation for 2022 ETL
Phases 2-3: Create silver_sisu_aggregated_2022 and gold_course_indicators_source_2022
"""

import os
from ..clients import BigQueryClient
from ..config import BIGQUERY_DATASET, ETL_START_YEAR, ETL_END_YEAR
from ..utils.logger import logger


def load_sql_file(filename, project_id: str = None, dataset: str = None):
    """
    Load SQL file from sql/ directory and substitute project/dataset placeholders.
    Replaces any hardcoded project.dataset references with the configured values.
    """
    sql_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'sql')
    filepath = os.path.join(sql_dir, filename)
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"SQL file not found: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    # Substitute hardcoded project/dataset with env values
    if project_id and dataset:
        import re
        # Replace any `project.dataset.table` pattern inside backticks
        sql = re.sub(
            r'`[^`]+\.([^`.]+\.[^`]+)`',
            lambda m: f'`{project_id}.{dataset}.{m.group(1).split(".")[-1]}`',
            sql
        )
    
    return sql


def create_silver_sisu_aggregated_2022():
    """
    Phase 2: Create silver_sisu_aggregated_2022 table
    Aggregates SISU microdados by (ano, id_ies, id_curso, sigla_uf_ies)
    """
    logger.info("\nPHASE 2: CREATING silver_sisu_aggregated_2022")
    
    bq_client = BigQueryClient()
    
    try:
        sql = load_sql_file(
            '01_create_silver_sisu_aggregated_2022.sql',
            project_id=bq_client.project_id,
            dataset=BIGQUERY_DATASET
        )
        
        logger.info(f"Creating table: {BIGQUERY_DATASET}.silver_sisu_aggregated_2022")
        query_job = bq_client.client.query(sql)
        query_job.result()  # Wait for completion
        
        logger.info("  silver_sisu_aggregated_2022 created successfully")
        
        # Validate
        count_query = f"""
        SELECT COUNT(*) as total
        FROM `{bq_client.project_id}.{BIGQUERY_DATASET}.silver_sisu_aggregated_2022`
        WHERE ano = 2022
        """
        result = bq_client.fetch_data(count_query)
        count = result[0]['total'] if result else 0
        logger.info(f"Total aggregated SISU records for 2022: {count:,}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating silver_sisu_aggregated_2022: {e}", exc_info=True)
        return False


def create_gold_course_indicators_source_2022():
    """
    Phase 3: Create gold_course_indicators_source_2022 table
    Final analytical table joining Censo + IES + SISU aggregated
    """
    logger.info("\nPHASE 3: CREATING gold_course_indicators_source_2022")
    
    bq_client = BigQueryClient()
    
    try:
        sql = load_sql_file(
            '02_create_gold_course_indicators_source_2022.sql',
            project_id=bq_client.project_id,
            dataset=BIGQUERY_DATASET
        )
        
        logger.info(f"Creating table: {BIGQUERY_DATASET}.gold_course_indicators_source_2022")
        query_job = bq_client.client.query(sql)
        query_job.result()  # Wait for completion
        
        logger.info("  gold_course_indicators_source_2022 created successfully")
        
        # Validate
        count_query = f"""
        SELECT COUNT(*) as total, COUNT(DISTINCT sigla_uf) as uf_count
        FROM `{bq_client.project_id}.{BIGQUERY_DATASET}.gold_course_indicators_source_2022`
        WHERE ano = 2022
        """
        result = bq_client.fetch_data(count_query)
        if result:
            count = result[0]['total']
            uf_count = result[0]['uf_count']
            logger.info(f"Total course records for 2022: {count:,}")
            logger.info(f"Number of UFs: {uf_count}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating gold_course_indicators_source_2022: {e}", exc_info=True)
        return False


def setup_intermediate_tables():
    """
    Setup both silver and gold tables for 2022
    """
    logger.info("\nSetting up intermediate BigQuery tables for 2022 ETL...")
    
    if not create_silver_sisu_aggregated_2022():
        logger.error("Failed to create silver_sisu_aggregated_2022")
        return False
    
    if not create_gold_course_indicators_source_2022():
        logger.error("Failed to create gold_course_indicators_source_2022")
        return False
    
    logger.info("\n  All intermediate tables created successfully")
    return True
