"""
Phase 1: Extract BigQuery staging data

Lê as três tabelas principais de staging do BigQuery:
- stg_censo_ies
- stg_censo_curso
- stg_sisu_microdados
"""

from ..clients import BigQueryClient
from ..config import (
    GCP_PROJECT_ID,
    BIGQUERY_DATASET,
    BQ_TABLE_CENSO_IES,
    BQ_TABLE_CENSO_CURSO,
    BQ_TABLE_SISU_MICRODADOS,
    ETL_START_YEAR,
    ETL_END_YEAR,
    ETL_LIMIT,
)
from ..utils.logger import logger


class PhaseExtract:
    """Extrai dados das tabelas de staging do BigQuery"""
    
    def __init__(self):
        self.bq_client = BigQueryClient()
        self.year_range = (ETL_START_YEAR, ETL_END_YEAR)
        self.limit = ETL_LIMIT
        self.dataset = BIGQUERY_DATASET
        
        logger.info(f"Phase 1 - Extract configurado para anos {self.year_range[0]}-{self.year_range[1]}")
        if self.limit:
            logger.info(f"Limite de registros por tabela: {self.limit}")
    
    def extract_censo_ies(self):
        """
        Extrai dados de Censo IES.
        
        Returns:
            List[dict]: Lista de registros de IES
        """
        logger.info("Extraindo Censo IES...")
        data = self.bq_client.read_table(
            self.dataset,
            BQ_TABLE_CENSO_IES,
            year_range=self.year_range,
            limit=self.limit
        )
        logger.info(f"Censo IES: {len(data)} registros extraídos")
        return data
    
    def extract_censo_curso(self):
        """
        Extrai dados de Censo Curso.
        
        Returns:
            List[dict]: Lista de registros de cursos
        """
        logger.info("Extraindo Censo Curso...")
        data = self.bq_client.read_table(
            self.dataset,
            BQ_TABLE_CENSO_CURSO,
            year_range=self.year_range,
            limit=self.limit
        )
        logger.info(f"Censo Curso: {len(data)} registros extraídos")
        return data
    
    def extract_sisu_microdados(self):
        """
        Extrai dados de SISU Microdados.
        
        Returns:
            List[dict]: Lista de registros de SISU
        """
        logger.info("Extraindo SISU Microdados...")
        data = self.bq_client.read_table(
            self.dataset,
            BQ_TABLE_SISU_MICRODADOS,
            year_range=self.year_range,
            limit=self.limit
        )
        logger.info(f"SISU Microdados: {len(data)} registros extraídos")
        return data
    
    def run(self):
        """
        Executa a extração de todas as tabelas de staging.
        
        Returns:
            dict: Dicionário com os dados extraídos e estatísticas
        """
        try:
            logger.info("=" * 80)
            logger.info("PHASE 1: EXTRACT BIGQUERY STAGING DATA")
            logger.info("=" * 80)
            
            censo_ies = self.extract_censo_ies()
            censo_curso = self.extract_censo_curso()
            sisu_microdados = self.extract_sisu_microdados()
            
            result = {
                "censo_ies": censo_ies,
                "censo_curso": censo_curso,
                "sisu_microdados": sisu_microdados,
                "stats": {
                    "censo_ies_count": len(censo_ies),
                    "censo_curso_count": len(censo_curso),
                    "sisu_microdados_count": len(sisu_microdados),
                }
            }
            
            logger.info("")
            logger.info("PHASE 1 - EXTRACTION SUMMARY")
            logger.info("-" * 80)
            logger.info(f"Censo IES:           {result['stats']['censo_ies_count']} registros")
            logger.info(f"Censo Curso:         {result['stats']['censo_curso_count']} registros")
            logger.info(f"SISU Microdados:     {result['stats']['sisu_microdados_count']} registros")
            logger.info("-" * 80)
            
            return result
        except Exception as e:
            logger.error(f"Erro na Phase 1 - Extract: {e}", exc_info=True)
            raise
