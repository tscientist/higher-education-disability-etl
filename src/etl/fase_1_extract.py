"""
Fase 1: Extract BigQuery staging data

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
    ETL_BATCH_SIZE,
    ETL_ENABLE_BATCH_MODE,
)
from ..utils.logger import logger


class Fase1Extract:
    """Extrai dados das tabelas de staging do BigQuery"""
    
    def __init__(self):
        self.bq_client = BigQueryClient()
        self.year_range = (ETL_START_YEAR, ETL_END_YEAR)
        self.limit = ETL_LIMIT
        self.dataset = BIGQUERY_DATASET
        self.batch_size = ETL_BATCH_SIZE
        self.enable_batch_mode = ETL_ENABLE_BATCH_MODE
        
        logger.info(f"Fase 1 - Extract configurado para anos {self.year_range[0]}-{self.year_range[1]}")
        logger.info(f"Modo batch: {'ATIVADO' if self.enable_batch_mode else 'DESATIVADO'} (tamanho: {self.batch_size})")
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
    
    def extract_censo_ies_in_batches(self):
        """
        Extrai dados de Censo IES em batches.
        
        Yields:
            Tuple[int, List[dict]]: (batch_number, batch_data)
        """
        logger.info("Extraindo Censo IES em batches...")
        for batch_number, batch_data in self.bq_client.read_table_in_batches(
            self.dataset,
            BQ_TABLE_CENSO_IES,
            year_range=self.year_range,
            limit=self.limit,
            batch_size=self.batch_size
        ):
            yield batch_number, batch_data
    
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
    
    def extract_censo_curso_in_batches(self):
        """
        Extrai dados de Censo Curso em batches.
        
        Yields:
            Tuple[int, List[dict]]: (batch_number, batch_data)
        """
        logger.info("Extraindo Censo Curso em batches...")
        for batch_number, batch_data in self.bq_client.read_table_in_batches(
            self.dataset,
            BQ_TABLE_CENSO_CURSO,
            year_range=self.year_range,
            limit=self.limit,
            batch_size=self.batch_size
        ):
            yield batch_number, batch_data
    
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
    
    def extract_sisu_microdados_in_batches(self):
        """
        Extrai dados de SISU Microdados em batches.
        
        Yields:
            Tuple[int, List[dict]]: (batch_number, batch_data)
        """
        logger.info("Extraindo SISU Microdados em batches...")
        for batch_number, batch_data in self.bq_client.read_table_in_batches(
            self.dataset,
            BQ_TABLE_SISU_MICRODADOS,
            year_range=self.year_range,
            limit=self.limit,
            batch_size=self.batch_size
        ):
            yield batch_number, batch_data
    
    def run(self):
        """
        Executa a extração de todas as tabelas de staging.
        
        Returns:
            dict: Dicionário com os dados extraídos e estatísticas
        """
        try:
            logger.info("=" * 80)
            logger.info("FASE 1: EXTRACT BIGQUERY STAGING DATA")
            logger.info("=" * 80)
            
            if self.enable_batch_mode:
                return self._run_batch_mode()
            else:
                return self._run_normal_mode()
        except Exception as e:
            logger.error(f"Erro na Fase 1 - Extract: {e}", exc_info=True)
            raise
    
    def _run_normal_mode(self):
        """Executa a extração no modo normal (sem batches)"""
        logger.info("Executando em modo NORMAL (sem batches)...\n")
        
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
        logger.info("FASE 1 - EXTRACTION SUMMARY")
        logger.info("-" * 80)
        logger.info(f"Censo IES:           {result['stats']['censo_ies_count']} registros")
        logger.info(f"Censo Curso:         {result['stats']['censo_curso_count']} registros")
        logger.info(f"SISU Microdados:     {result['stats']['sisu_microdados_count']} registros")
        logger.info("-" * 80)
        
        return result
    
    def _run_batch_mode(self):
        """Executa a extração no modo BATCH"""
        logger.info("Executando em modo BATCH (20mil registros por vez)...\n")
        
        result = {
            "censo_ies_batches": [],
            "censo_curso_batches": [],
            "sisu_microdados_batches": [],
            "stats": {
                "censo_ies_count": 0,
                "censo_curso_count": 0,
                "sisu_microdados_count": 0,
                "censo_ies_batches": 0,
                "censo_curso_batches": 0,
                "sisu_microdados_batches": 0,
            }
        }
        
        # Extrair Censo IES em batches
        logger.info("\n--- EXTRAÇÃO CENSO IES ---")
        for batch_num, batch_data in self.extract_censo_ies_in_batches():
            result["censo_ies_batches"].append(batch_data)
            result["stats"]["censo_ies_count"] += len(batch_data)
            result["stats"]["censo_ies_batches"] = batch_num
        
        # Extrair Censo Curso em batches
        logger.info("\n--- EXTRAÇÃO CENSO CURSO ---")
        for batch_num, batch_data in self.extract_censo_curso_in_batches():
            result["censo_curso_batches"].append(batch_data)
            result["stats"]["censo_curso_count"] += len(batch_data)
            result["stats"]["censo_curso_batches"] = batch_num
        
        # Extrair SISU Microdados em batches
        logger.info("\n--- EXTRAÇÃO SISU MICRODADOS ---")
        for batch_num, batch_data in self.extract_sisu_microdados_in_batches():
            result["sisu_microdados_batches"].append(batch_data)
            result["stats"]["sisu_microdados_count"] += len(batch_data)
            result["stats"]["sisu_microdados_batches"] = batch_num
        
        logger.info("")
        logger.info("FASE 1 - BATCH EXTRACTION SUMMARY")
        logger.info("-" * 80)
        logger.info(f"Censo IES:           {result['stats']['censo_ies_count']} registros em {result['stats']['censo_ies_batches']} batches")
        logger.info(f"Censo Curso:         {result['stats']['censo_curso_count']} registros em {result['stats']['censo_curso_batches']} batches")
        logger.info(f"SISU Microdados:     {result['stats']['sisu_microdados_count']} registros em {result['stats']['sisu_microdados_batches']} batches")
        logger.info("-" * 80)
        
        return result
