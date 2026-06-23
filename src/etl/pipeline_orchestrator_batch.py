"""
ETL Pipeline Orchestrator - Batch Mode

Orquestra a execução do pipeline em batches de ponta a ponta:
Extract - Transform Censo - Transform SISU - Join, Build & Metrics - Load

Cada batch é processado antes de iniciar o próximo.
"""

import sys
from datetime import datetime

from src.etl.fase_1_extract import Fase1Extract
from src.etl.fase_2_transform_censo import Fase2TransformCenso
from src.etl.fase_3_transform_sisu import Fase3TransformSISU
from src.etl.fase_456_join_build_metrics import Fase456JoinBuildAndMetrics
from src.etl.fase_7_mongodb_load import Fase7MongoDBLoad
from src.etl.fase_8_create_indexes import Fase8CreateIndexes
from src.etl.fase_11_validation import Fase11Validation
from src.config import ETL_START_YEAR, ETL_END_YEAR
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ETLPipelineOrchestratorBatch:
    """Orquestra a execução de todas as fases do pipeline em modo BATCH"""
    
    def __init__(self):
        self.results = {}
        self.batch_number = 0
        self.total_documents_processed = 0
    
    def run_full_pipeline_batch(self):
        """
        Executa o pipeline completo em batches de ponta a ponta.
        
        Fluxo: Extract → Transform → Join → Load (para cada batch)
        """
        logger.info("\n" + "="*80)
        logger.info("BRASIL - EDUCAÇÃO SUPERIOR COM DEFICIÊNCIA - ETL PIPELINE BATCH")
        logger.info("="*80 + "\n")
        
        start_time = datetime.now()
        
        try:
            # Inicializar as fases
            fase1 = Fase1Extract()
            fase2 = Fase2TransformCenso()
            fase3 = Fase3TransformSISU()
            fase456 = Fase456JoinBuildAndMetrics()
            fase7 = Fase7MongoDBLoad()
            
            batch_results = []
            
            # Iterar sobre batches sincronizados
            for batch_data in fase1.extract_all_tables_synchronized():
                batch_number = batch_data["batch_number"]
                self.batch_number = batch_number
                
                logger.info("\n" + "="*80)
                logger.info(f"PROCESSANDO BATCH #{batch_number}")
                logger.info("="*80 + "\n")
                
                try:
                    # FASE 2: Transform CENSO
                    logger.info(f"[Fase 2] Transformando dados CENSO...")
                    censo_transformed = fase2.transform_batch(
                        batch_data["censo_curso"],
                        batch_data["censo_ies"]
                    )
                    
                    # FASE 3: Transform SISU
                    logger.info(f"[Fase 3] Transformando dados SISU...")
                    sisu_aggregations, sisu_final = fase3.transform_batch(
                        batch_data["sisu_microdados"]
                    )
                    
                    # FASES 4-6: Join, Build & Metrics
                    logger.info(f"[Fases 4-6] Juntando dados e construindo documentos finais...")
                    final_documents = fase456.join_and_build_batch(
                        censo_transformed,
                        sisu_final,
                        year_range=(ETL_START_YEAR, ETL_END_YEAR)
                    )
                    
                    # FASE 7: Load MongoDB
                    logger.info(f"[Fase 7] Carregando dados no MongoDB...")
                    load_result = fase7.load_batch(final_documents, batch_number)
                    
                    # Atualizar estatísticas
                    self.total_documents_processed += len(final_documents)
                    
                    batch_result = {
                        "batch_number": batch_number,
                        "status": "success",
                        "timestamp": datetime.now().isoformat(),
                        "extraction_stats": batch_data["stats"],
                        "documents_processed": len(final_documents),
                        "load_result": load_result,
                    }
                    batch_results.append(batch_result)
                    self.results[f"batch_{batch_number}"] = batch_result
                    
                    logger.info(f"\nBATCH #{batch_number} CONCLUÍDO COM SUCESSO!")
                    logger.info(f"   Registros processados: {len(final_documents)}")
                    logger.info(f"   Total acumulado: {self.total_documents_processed}\n")
                    
                except Exception as e:
                    logger.error(f"ERRO NO BATCH #{batch_number}: {e}", exc_info=True)
                    batch_result = {
                        "batch_number": batch_number,
                        "status": "failed",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                    batch_results.append(batch_result)
                    self.results[f"batch_{batch_number}"] = batch_result
                    
                    # Continua processando outros batches em caso de erro
                    continue
            
            # Após processar todos os batches
            logger.info("\n" + "="*80)
            logger.info("CRIANDO ÍNDICES NO MONGODB")
            logger.info("="*80 + "\n")
            try:
                fase8 = Fase8CreateIndexes()
                fase8.run()
                logger.info("Índices criados com sucesso\n")
            except Exception as e:
                logger.error(f"Erro ao criar índices: {e}", exc_info=True)
            
            # Validação (opcional)
            logger.info("\n" + "="*80)
            logger.info(" VALIDANDO DADOS")
            logger.info("="*80 + "\n")
            try:
                fase11 = Fase11Validation()
                fase11.run(self.results)
                logger.info(" Validação concluída\n")
            except Exception as e:
                logger.error(f"Erro na validação: {e}", exc_info=True)
            
            # Resumo final
            return self._print_summary(batch_results, start_time)
            
        except Exception as e:
            logger.error(f"ERRO CRÍTICO NO PIPELINE: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
    
    def _print_summary(self, batch_results, start_time):
        """Imprime resumo final do pipeline"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        successful_batches = [b for b in batch_results if b["status"] == "success"]
        failed_batches = [b for b in batch_results if b["status"] == "failed"]
        
        logger.info("RESUMO FINAL DO PIPELINE")
        logger.info(f"\n  Duração total: {duration:.2f} segundos ({duration/60:.2f} minutos)")
        logger.info(f"\n Batches processados:")
        logger.info(f"    Sucesso: {len(successful_batches)}")
        logger.info(f"    Falha: {len(failed_batches)}")
        logger.info(f"    Total: {len(batch_results)}")
        logger.info(f"\n Documentos processados:")
        logger.info(f"   Total: {self.total_documents_processed}")
        if len(successful_batches) > 0:
            avg_per_batch = self.total_documents_processed / len(successful_batches)
            logger.info(f"   Média por batch: {avg_per_batch:.0f}")
        logger.info("\n" + "="*80 + "\n")
        
        return {
            "success": len(failed_batches) == 0,
            "total_batches": len(batch_results),
            "successful_batches": len(successful_batches),
            "failed_batches": len(failed_batches),
            "total_documents_processed": self.total_documents_processed,
            "duration_seconds": duration,
            "batch_results": batch_results,
            "timestamp": datetime.now().isoformat(),
        }
