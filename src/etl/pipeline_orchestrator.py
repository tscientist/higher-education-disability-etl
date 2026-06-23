"""
Complete ETL Pipeline Orchestrator

Executa todas as fases do pipeline de forma orchestrada.
Pode ser executado como um todo ou em fases separadas para testes.
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


class ETLPipelineOrchestrator:
    """Orquestra a execução de todas as fases do pipeline"""
    
    def __init__(self):
        self.results = {}
    
    def run_fase_1_extract(self):
        """Executa fase 1 - Extract"""
        logger.info("\n INICIANDO FASE 1 - EXTRACT\n")
        
        try:
            fase1 = Fase1Extract()
            result = fase1.run()
            self.results["fase_1"] = result["stats"]
            
            return result
        except Exception as e:
            logger.error(f"Erro na fase 1: {e}", exc_info=True)
            raise
    
    def run_fase_2_transform_censo(self, fase1_result):
        """Executa fase 2 - Transform Censo"""
        logger.info("INICIANDO FASE 2 - TRANSFORM CENSO CURSO + CENSO IES\n")
        
        try:
            fase2 = Fase2TransformCenso()
            censo_cursos_enriquecidos = fase2.run(
                fase1_result["censo_curso"],
                fase1_result["censo_ies"]
            )
            
            return censo_cursos_enriquecidos
        except Exception as e:
            logger.error(f"Erro na fase 2: {e}", exc_info=True)
            raise
    
    def run_fase_3_transform_sisu(self, fase1_result):
        """Executa fase 3 - Transform SISU"""
        logger.info("\nINICIANDO FASE 3 - TRANSFORM SISU MICRODADOS\n")

        try:
            fase3 = Fase3TransformSISU()
            sisu_aggregations, sisu_final_docs = fase3.run(
                fase1_result["sisu_microdados"]
            )
            
            self.results["sisu_aggregations"] = sisu_aggregations
            self.results["sisu_final_docs"] = sisu_final_docs
            
            return sisu_aggregations, sisu_final_docs
        except Exception as e:
            logger.error(f"Erro na fase 3: {e}", exc_info=True)
            raise
    
    def run_fase_456_join_build_metrics(self, censo_cursos_enriquecidos, sisu_final_docs):
        """Executa fase 4-6 - Join, Build & Metrics"""
        logger.info("INICIANDO FASE 4-6 - JOIN, BUILD & CALCULATE METRICS\n")

        try:
            fase456 = Fase456JoinBuildAndMetrics()
            final_documents = fase456.run(
                censo_cursos_enriquecidos,
                sisu_final_docs,
                year_range=(ETL_START_YEAR, ETL_END_YEAR)
            )
            
            self.results["final_documents"] = final_documents
            
            return final_documents
        except Exception as e:
            logger.error(f"Erro na fase 4-6: {e}", exc_info=True)
            raise
    
    def run_fase_7_mongodb_load(self, final_documents, sisu_final_docs):
        """Executa fase 7 - MongoDB Load"""
        logger.info("\nINICIANDO FASE 7 - MONGODB LOAD\n")
        
        try:
            fase7 = Fase7MongoDBLoad()
            load_stats = fase7.run(final_documents, sisu_final_docs)
            
            self.results["mongodb_stats"] = {
                "gold_matched": load_stats.get("gold_course_indicators", {}).get("matched", 0),
                "gold_modified": load_stats.get("gold_course_indicators", {}).get("modified", 0),
                "gold_upserted": load_stats.get("gold_course_indicators", {}).get("upserted", 0),
                "sisu_matched": load_stats.get("sisu_aggregated", {}).get("matched", 0),
                "sisu_modified": load_stats.get("sisu_aggregated", {}).get("modified", 0),
                "sisu_upserted": load_stats.get("sisu_aggregated", {}).get("upserted", 0),
            }
            
            return load_stats
        except Exception as e:
            logger.error(f"Erro na fase 7: {e}", exc_info=True)
            raise
    
    def run_fase_8_create_indexes(self):
        """Executa fase 8 - Create Indexes"""
        logger.info("\nINICIANDO FASE 8 - CREATE INDEXES\n")

        try:
            fase8 = Fase8CreateIndexes()
            index_stats = fase8.run()
            
            return index_stats
        except Exception as e:
            logger.error(f"Erro na fase 8: {e}", exc_info=True)
            raise
    
    def run_fase_11_validation(self):
        """Executa fase 11 - Validation"""
        logger.info("\nINICIANDO FASE 11 - VALIDATION & TEST OUTPUT\n")

        try:
            fase11 = Fase11Validation()
            validation_stats = fase11.run(self.results)
            
            return validation_stats
        except Exception as e:
            logger.error(f"Erro na fase 11: {e}", exc_info=True)
            raise
    
    def run_full_pipeline(self):
        """
        Executa o pipeline completo (todas as fases).
        
        Recomendado para execução em produção.
        """
        try:
            start_time = datetime.now()
            logger.info("\nBRASIL - EDUCAÇÃO SUPERIOR COM DEFICIÊNCIA - ETL PIPELINE COMPLETO\n")
            
            # Fase 1: Extract
            fase1_result = self.run_fase_1_extract()

            # Fase 2: Transform Censo
            censo_cursos_enriquecidos = self.run_fase_2_transform_censo(fase1_result)

            # Fase 3: Transform SISU
            sisu_aggregations, sisu_final_docs = self.run_fase_3_transform_sisu(fase1_result)

            # Fase 4-6: Join, Build & Metrics
            final_documents = self.run_fase_456_join_build_metrics(
                censo_cursos_enriquecidos,
                sisu_final_docs
            )

            # Fase 7: MongoDB Load
            load_stats = self.run_fase_7_mongodb_load(final_documents, sisu_final_docs)

            # Fase 8: Create Indexes
            index_stats = self.run_fase_8_create_indexes()

            # Fase 11: Validation
            validation_stats = self.run_fase_11_validation()
            
            # Resumo final
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info("\nPIPELINE EXECUTADO COM SUCESSO\n")
            logger.info("\nTempo total: {duration:.2f} segundos\n")
            
            return {
                "success": True,
                "duration_seconds": duration,
                "results": self.results,
            }
        except Exception as e:
            logger.error(f"Erro durante execução do pipeline: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }
    
    def run_extraction_only(self):
        """
        Executa apenas fase 1 (extração).
        Útil para testes iniciais.
        """
        try:
            logger.info("Executando apenas fase 1 - EXTRACT para testes...")
            fase1_result = self.run_fase_1_extract()
            return fase1_result
        except Exception as e:
            logger.error(f"Erro: {e}", exc_info=True)
            return None
    
    def run_extract_to_build(self):
        """
        Executa Fases 1-6 (Extract, Transform, Build).
        """
        try:
            logger.info("Executando fases 1-6 (Extract, Transform, Build)...")

            # Fase 1
            fase1_result = self.run_fase_1_extract()

            # Fase 2
            censo_cursos_enriquecidos = self.run_fase_2_transform_censo(fase1_result)

            # Fase 3
            sisu_aggregations, sisu_final_docs = self.run_fase_3_transform_sisu(fase1_result)

            # Fase 4-6
            final_documents = self.run_fase_456_join_build_metrics(
                censo_cursos_enriquecidos,
                sisu_final_docs
            )
            
            logger.info(f"Construção completa: {len(final_documents)} documentos finais preparados")
            
            return {
                "final_documents": final_documents,
                "sisu_final_docs": sisu_final_docs,
            }
        except Exception as e:
            logger.error(f"Erro: {e}", exc_info=True)
            return None


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="ETL Pipeline - Brasil Educação Superior com Deficiência"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "extract", "build"],
        default="full",
        help="Modo de execução: full (completo), extract (só extração), build (até construção)"
    )
    
    args = parser.parse_args()
    
    orchestrator = ETLPipelineOrchestrator()
    
    if args.mode == "extract":
        orchestrator.run_extraction_only()
    elif args.mode == "build":
        orchestrator.run_extract_to_build()
    else:
        result = orchestrator.run_full_pipeline()
        
        if not result.get("success"):
            sys.exit(1)


if __name__ == "__main__":
    main()
