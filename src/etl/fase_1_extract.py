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
    
    def extract_all_tables_synchronized(self):
        """
        Extrai dados de todas as três tabelas de forma sincronizada em batches.
        
        PROBLEMA ANTERIOR: Quando tabela menor terminava, parava tudo.
        SOLUÇÃO: Ler Censo IES UMA VEZ, depois fazer batches de CURSO + SISU sincronizados.
        
        Yields:
            dict: {
                "batch_number": int,
                "censo_ies": List[dict],
                "censo_curso": List[dict],
                "sisu_microdados": List[dict],
                "stats": dict com contadores
            }
        """
        logger.info("\nINICIANDO EXTRAÇÃO SINCRONIZADA DE BATCHES")
        logger.info(f"Tamanho do batch: {self.batch_size} registros por tabela\n")
        
        try:
            # Ler Censo IES UMA VEZ (é pequeno: 2595 registros)
            logger.info("Lendo Censo IES (tabela pequena)...")
            ies_data = self.extract_censo_ies()
            logger.info(f"✓ Censo IES lido: {len(ies_data)} registros\n")
            
            # Criar geradores para Curso e SISU (são grandes)
            curso_generator = self.extract_censo_curso_in_batches()
            sisu_generator = self.extract_sisu_microdados_in_batches()
            
            batch_number = 0
            total_ies = len(ies_data)
            total_curso = 0
            total_sisu = 0
            
            # Itera sincronizadamente sobre CURSO + SISU em batches
            while True:
                try:
                    _, curso_batch = next(curso_generator)
                    _, sisu_batch = next(sisu_generator)
                    
                    batch_number += 1
                    total_curso += len(curso_batch)
                    total_sisu += len(sisu_batch)
                    
                    logger.info(f"\n{'='*80}")
                    logger.info(f"BATCH #{batch_number} EXTRAÍDO")
                    logger.info(f"{'='*80}")
                    logger.info(f"  Censo IES:       {len(ies_data)} registros (lido uma vez)")
                    logger.info(f"  Censo Curso:     {len(curso_batch)} registros (total: {total_curso})")
                    logger.info(f"  SISU Microdados: {len(sisu_batch)} registros (total: {total_sisu})")
                    logger.info(f"{'='*80}\n")
                    
                    yield {
                        "batch_number": batch_number,
                        "censo_ies": ies_data,  # Sempre os mesmos dados IES
                        "censo_curso": curso_batch,
                        "sisu_microdados": sisu_batch,
                        "stats": {
                            "batch_ies_count": len(ies_data),
                            "batch_curso_count": len(curso_batch),
                            "batch_sisu_count": len(sisu_batch),
                            "total_ies": total_ies,
                            "total_curso": total_curso,
                            "total_sisu": total_sisu,
                        }
                    }
                    
                except StopIteration:
                    logger.info(f"\n✓ Extração completa! {batch_number} batches processados")
                    logger.info(f"  Total final - Censo IES: {total_ies} | Censo Curso: {total_curso} | SISU: {total_sisu}\n")
                    break
                    
        except Exception as e:
            logger.error(f"Erro na extração sincronizada: {e}", exc_info=True)
            raise
    
    def extract_all_by_ies(self):
        """Extrai dados processando um IES por vez"""
        logger.info("\nINICIANDO EXTRACAO POR IES")
        logger.info("Processando um IES por vez\n")
        
        try:
            logger.info("Lendo lista de IES...")
            all_ies = self.extract_censo_ies()
            logger.info(f"Total de IES encontradas: {len(all_ies)}\n")
            
            logger.info("Lendo todos os cursos...")
            all_cursos = self.extract_censo_curso()
            logger.info(f"Total de cursos: {len(all_cursos)}")
            
            logger.info("Lendo todos os registros SISU...")
            all_sisu = self.extract_sisu_microdados()
            logger.info(f"Total de SISU: {len(all_sisu)}\n")
            
            # Criar índices para busca rápida
            cursos_by_ies = {}
            for curso in all_cursos:
                id_ies = curso.get("id_ies")
                if id_ies not in cursos_by_ies:
                    cursos_by_ies[id_ies] = []
                cursos_by_ies[id_ies].append(curso)
            
            sisu_by_ies = {}
            for sisu in all_sisu:
                id_ies = sisu.get("id_ies")
                if id_ies not in sisu_by_ies:
                    sisu_by_ies[id_ies] = []
                sisu_by_ies[id_ies].append(sisu)
            
            # Processar cada IES
            total_ies = len(all_ies)
            for ies_num, ies_record in enumerate(all_ies, 1):
                id_ies = ies_record.get("id_ies")
                nome_ies = ies_record.get("nome", "Desconhecida")
                
                ies_cursos = cursos_by_ies.get(id_ies, [])
                ies_sisu = sisu_by_ies.get(id_ies, [])
                
                logger.info(f"\n[IES {ies_num}/{total_ies}] ID: {id_ies} - {nome_ies}")
                logger.info(f"  Cursos: {len(ies_cursos)} | SISU: {len(ies_sisu)}")
                
                yield {
                    "ies_number": ies_num,
                    "total_ies": total_ies,
                    "ies_data": ies_record,
                    "curso_data": ies_cursos,
                    "sisu_data": ies_sisu,
                    "stats": {
                        "id_ies": id_ies,
                        "nome_ies": nome_ies,
                        "cursos_count": len(ies_cursos),
                        "sisu_count": len(ies_sisu),
                    }
                }
            
            logger.info(f"\nExtracao por IES completa!")
            
        except Exception as e:
            logger.error(f"Erro na extracao por IES: {e}", exc_info=True)
            raise
    
    def extract_single_ies_complete(self, id_ies):
        """
        Extrai dados completos para uma unica IES do BigQuery.
        Filtra cursos e SISU por id_ies, retorna IES, cursos e SISU.
        
        Args:
            id_ies: ID da instituicao para extrair
            
        Returns:
            dict com ies_data, curso_data e sisu_data filtrados
        """
        logger.info(f"\nExtraindo dados para IES {id_ies}")
        
        try:
            # Extrair o registro IES
            ies_table = self.bq_client.read_table(
                self.dataset,
                BQ_TABLE_CENSO_IES,
                year_range=self.year_range,
                limit=None
            )
            ies_data = next((r for r in ies_table if r.get("id_ies") == id_ies), None)
            
            # Extrair cursos para este IES (do BigQuery, nao em memoria)
            curso_data = self.bq_client.read_table_filtered_by_ies(
                self.dataset,
                BQ_TABLE_CENSO_CURSO,
                id_ies,
                year_range=self.year_range
            )
            
            # Extrair SISU para este IES (do BigQuery, nao em memoria)
            sisu_data = self.bq_client.read_table_filtered_by_ies(
                self.dataset,
                BQ_TABLE_SISU_MICRODADOS,
                id_ies,
                year_range=self.year_range
            )
            
            logger.info(f"IES {id_ies}: {len(curso_data)} cursos, {len(sisu_data)} SISU")
            
            return {
                "ies_data": ies_data,
                "curso_data": curso_data,
                "sisu_data": sisu_data
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair IES {id_ies}: {e}", exc_info=True)
            return {
                "ies_data": None,
                "curso_data": [],
                "sisu_data": []
            }
