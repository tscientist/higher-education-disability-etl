"""
Fase 1 Extract - Strategy: Batch by IES (Institution ID)

Estratégia alternativa de extração por instituição (ID_IES).
Isso garante que todos os cursos e dados SISU de uma IES sejam processados juntos.
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
)
from ..utils.logger import logger


class Fase1ExtractByIES:
    """Extrai dados agrupados por ID_IES (estratégia alternativa)"""
    
    def __init__(self):
        self.bq_client = BigQueryClient()
        self.year_range = (ETL_START_YEAR, ETL_END_YEAR)
        self.limit = ETL_LIMIT
        self.dataset = BIGQUERY_DATASET
        self.batch_size = ETL_BATCH_SIZE
        
        logger.info(f"Fase 1 - Extract (por IES) configurado para anos {self.year_range[0]}-{self.year_range[1]}")
        logger.info(f"Tamanho do batch: {self.batch_size} registros por IES")
    
    def extract_all_by_ies(self):
        """
        Extrai dados sincronizados por ID_IES.
        
        Yields:
            dict com dados sincronizados de uma IES
        """
        logger.info("\nINICIANDO EXTRAÇÃO SINCRONIZADA POR IES\n")
        
        try:
            # Query para obter lista de IES únicas
            ies_query = f"""
            SELECT DISTINCT id_ies
            FROM `{self.dataset}.{BQ_TABLE_CENSO_IES}`
            WHERE ano >= {self.year_range[0]} AND ano <= {self.year_range[1]}
            ORDER BY id_ies
            """
            
            ies_list = self.bq_client.client.query(ies_query).result()
            ies_ids = [row.id_ies for row in ies_list]
            
            logger.info(f"Encontradas {len(ies_ids)} instituições para processar")
            
            batch_ies_ids = []
            batch_number = 0
            total_cursos = 0
            total_sisu = 0
            total_ies = 0
            
            for ies_id in ies_ids:
                batch_ies_ids.append(ies_id)
                
                # Quando atingir o tamanho do batch, processar
                if len(batch_ies_ids) >= self.batch_size or ies_id == ies_ids[-1]:
                    batch_number += 1
                    
                    # Extrair dados para este lote de IES
                    ies_list_batch = self._extract_ies_batch(batch_ies_ids)
                    curso_list_batch = self._extract_curso_batch(batch_ies_ids)
                    sisu_list_batch = self._extract_sisu_batch(batch_ies_ids)
                    
                    total_cursos += len(curso_list_batch)
                    total_sisu += len(sisu_list_batch)
                    total_ies += len(ies_list_batch)
                    
                    logger.info(f"\n--- BATCH #{batch_number} EXTRAÍDO ---")
                    logger.info(f"  IES: {len(batch_ies_ids)} instituições ({len(ies_list_batch)} registros)")
                    logger.info(f"  Cursos: {len(curso_list_batch)} registros")
                    logger.info(f"  SISU: {len(sisu_list_batch)} registros")
                    logger.info(f"  Totais: {total_ies} IES, {total_cursos} Cursos, {total_sisu} SISU")
                    
                    yield {
                        "batch_number": batch_number,
                        "ies_ids": batch_ies_ids.copy(),
                        "censo_ies": ies_list_batch,
                        "censo_curso": curso_list_batch,
                        "sisu_microdados": sisu_list_batch,
                        "stats": {
                            "batch_ies_count": len(ies_list_batch),
                            "batch_curso_count": len(curso_list_batch),
                            "batch_sisu_count": len(sisu_list_batch),
                            "total_ies": total_ies,
                            "total_cursos": total_cursos,
                            "total_sisu": total_sisu,
                            "ies_ids_in_batch": len(batch_ies_ids)
                        }
                    }
                    
                    batch_ies_ids = []
            
            logger.info(f"\nExtracao completa! {batch_number} batches processados")
            
        except Exception as e:
            logger.error(f"Erro na extracao por IES: {e}", exc_info=True)
            raise
    
    def _extract_ies_batch(self, ies_ids):
        """Extrai dados de IES para lista de IDs"""
        query = f"""
        SELECT *
        FROM `{self.dataset}.{BQ_TABLE_CENSO_IES}`
        WHERE id_ies IN ({','.join(map(str, ies_ids))})
        AND ano >= {self.year_range[0]} AND ano <= {self.year_range[1]}
        """
        
        result = self.bq_client.client.query(query).result()
        return [dict(row) for row in result]
    
    def _extract_curso_batch(self, ies_ids):
        """Extrai dados de Curso para lista de IDs de IES"""
        query = f"""
        SELECT *
        FROM `{self.dataset}.{BQ_TABLE_CENSO_CURSO}`
        WHERE id_ies IN ({','.join(map(str, ies_ids))})
        AND ano >= {self.year_range[0]} AND ano <= {self.year_range[1]}
        """
        
        if self.limit:
            query += f" LIMIT {self.limit}"
        
        result = self.bq_client.client.query(query).result()
        return [dict(row) for row in result]
    
    def _extract_sisu_batch(self, ies_ids):
        """Extrai dados de SISU para lista de IDs de IES"""
        query = f"""
        SELECT *
        FROM `{self.dataset}.{BQ_TABLE_SISU_MICRODADOS}`
        WHERE id_ies IN ({','.join(map(str, ies_ids))})
        AND ano >= {self.year_range[0]} AND ano <= {self.year_range[1]}
        """
        
        if self.limit:
            query += f" LIMIT {self.limit}"
        
        result = self.bq_client.client.query(query).result()
        return [dict(row) for row in result]
