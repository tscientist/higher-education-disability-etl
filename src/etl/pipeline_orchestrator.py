"""
Complete ETL Pipeline Orchestrator

Executa todas as fases do pipeline de forma orchestrada.
Pode ser executado como um todo ou em fases separadas para testes.
"""

import sys
from datetime import datetime

from src.etl.phase_extract import PhaseExtract
from src.etl.phase_transform_censo import PhaseTransformCenso
from src.etl.phase_transform_sisu import PhaseTransformSISU
from src.etl.phase_join_build_metrics import PhaseJoinBuildMetrics
from src.etl.phase_mongodb_load import PhaseMongoDBLoad
from src.etl.phase_create_indexes import PhaseCreateIndexes
from src.etl.phase_validation import PhaseValidation
from src.config import ETL_START_YEAR, ETL_END_YEAR
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ETLPipelineOrchestrator:
    """Orquestra a execução de todas as fases do pipeline"""
    
    def __init__(self):
        self.results = {}
    
    def run_phase_1_extract(self):
        """Executa Phase 1 - Extract"""
        logger.info("\n" + "="*100)
        logger.info("INICIANDO PHASE 1 - EXTRACT")
        logger.info("="*100 + "\n")
        
        try:
            phase1 = PhaseExtract()
            result = phase1.run()
            self.results["phase_1"] = result["stats"]
            
            return result
        except Exception as e:
            logger.error(f"Erro na Phase 1: {e}", exc_info=True)
            raise
    
    def run_phase_2_transform_censo(self, phase1_result):
        """Executa Phase 2 - Transform Censo"""
        logger.info("\n" + "="*100)
        logger.info("INICIANDO PHASE 2 - TRANSFORM CENSO CURSO + CENSO IES")
        logger.info("="*100 + "\n")
        
        try:
            phase2 = PhaseTransformCenso()
            censo_cursos_enriquecidos = phase2.run(
                phase1_result["censo_curso"],
                phase1_result["censo_ies"]
            )
            
            return censo_cursos_enriquecidos
        except Exception as e:
            logger.error(f"Erro na Phase 2: {e}", exc_info=True)
            raise
    
    def run_phase_3_transform_sisu(self, phase1_result):
        """Executa Phase 3 - Transform SISU"""
        logger.info("\n" + "="*100)
        logger.info("INICIANDO PHASE 3 - TRANSFORM SISU MICRODADOS")
        logger.info("="*100 + "\n")
        
        try:
            phase3 = PhaseTransformSISU()
            sisu_aggregations, sisu_final_docs = phase3.run(
                phase1_result["sisu_microdados"]
            )
            
            self.results["sisu_aggregations"] = sisu_aggregations
            self.results["sisu_final_docs"] = sisu_final_docs
            
            return sisu_aggregations, sisu_final_docs
        except Exception as e:
            logger.error(f"Erro na Phase 3: {e}", exc_info=True)
            raise
    
    def run_phase_456_join_build_metrics(self, censo_cursos_enriquecidos, sisu_final_docs):
        """Executa Phase 4-6 - Join, Build & Metrics"""
        logger.info("\n" + "="*100)
        logger.info("INICIANDO PHASE 4-6 - JOIN, BUILD & CALCULATE METRICS")
        logger.info("="*100 + "\n")
        
        try:
            phase456 = PhaseJoinBuildMetrics()
            final_documents = phase456.run(
                censo_cursos_enriquecidos,
                sisu_final_docs,
                year_range=(ETL_START_YEAR, ETL_END_YEAR)
            )
            
            self.results["final_documents"] = final_documents
            
            return final_documents
        except Exception as e:
            logger.error(f"Erro na Phase 4-6: {e}", exc_info=True)
            raise
    
    def run_phase_7_mongodb_load(self, final_documents, sisu_final_docs):
        """Executa Phase 7 - MongoDB Load"""
        logger.info("\n" + "="*100)
        logger.info("INICIANDO PHASE 7 - MONGODB LOAD")
        logger.info("="*100 + "\n")
        
        try:
            phase7 = PhaseMongoDBLoad()
            load_stats = phase7.run(final_documents, sisu_final_docs)
            
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
            logger.error(f"Erro na Phase 7: {e}", exc_info=True)
            raise
    
    def run_phase_8_create_indexes(self):
        """Executa Phase 8 - Create Indexes"""
        logger.info("\n" + "="*100)
        logger.info("INICIANDO PHASE 8 - CREATE INDEXES")
        logger.info("="*100 + "\n")
        
        try:
            phase8 = PhaseCreateIndexes()
            index_stats = phase8.run()
            
            return index_stats
        except Exception as e:
            logger.error(f"Erro na Phase 8: {e}", exc_info=True)
            raise
    
    def run_phase_11_validation(self):
        """Executa Phase 11 - Validation"""
        logger.info("\n" + "="*100)
        logger.info("INICIANDO PHASE 11 - VALIDATION & TEST OUTPUT")
        logger.info("="*100 + "\n")
        
        try:
            phase11 = PhaseValidation()
            validation_stats = phase11.run(self.results)
            
            return validation_stats
        except Exception as e:
            logger.error(f"Erro na Phase 11: {e}", exc_info=True)
            raise
    
    def run_full_pipeline(self):
        """
        Executa o pipeline completo (todas as fases).
        
        Recomendado para execução em produção.
        """
        try:
            start_time = datetime.now()
            logger.info("")
            logger.info("╔" + "="*98 + "╗")
            logger.info("║" + " "*98 + "║")
            logger.info("║" + "BRASIL - EDUCAÇÃO SUPERIOR COM DEFICIÊNCIA - ETL PIPELINE COMPLETO".center(98) + "║")
            logger.info("║" + " "*98 + "║")
            logger.info("╚" + "="*98 + "╝")
            logger.info("")
            
            # Phase 1: Extract
            phase1_result = self.run_phase_1_extract()
            
            # Phase 2: Transform Censo
            censo_cursos_enriquecidos = self.run_phase_2_transform_censo(phase1_result)
            
            # Phase 3: Transform SISU
            sisu_aggregations, sisu_final_docs = self.run_phase_3_transform_sisu(phase1_result)
            
            # Phase 4-6: Join, Build & Metrics
            final_documents = self.run_phase_456_join_build_metrics(
                censo_cursos_enriquecidos,
                sisu_final_docs
            )
            
            # Phase 7: MongoDB Load
            load_stats = self.run_phase_7_mongodb_load(final_documents, sisu_final_docs)
            
            # Phase 8: Create Indexes
            index_stats = self.run_phase_8_create_indexes()
            
            # Phase 11: Validation
            validation_stats = self.run_phase_11_validation()
            
            # Resumo final
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info("")
            logger.info("╔" + "="*98 + "╗")
            logger.info("║" + " "*98 + "║")
            logger.info("║" + "PIPELINE EXECUTADO COM SUCESSO!".center(98) + "║")
            logger.info("║" + " "*98 + "║")
            logger.info("║" + f"Tempo total: {duration:.2f} segundos".center(98) + "║")
            logger.info("║" + " "*98 + "║")
            logger.info("╚" + "="*98 + "╝")
            logger.info("")
            
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
        Executa apenas Phase 1 (extração).
        Útil para testes iniciais.
        """
        try:
            logger.info("Executando apenas Phase 1 - EXTRACT para testes...")
            phase1_result = self.run_phase_1_extract()
            return phase1_result
        except Exception as e:
            logger.error(f"Erro: {e}", exc_info=True)
            return None
    
    def run_extract_to_build(self):
        """
        Executa Phases 1-6 (Extract, Transform, Build).
        """
        try:
            logger.info("Executando Phases 1-6 (Extract, Transform, Build)...")
            
            # Phase 1
            phase1_result = self.run_phase_1_extract()
            
            # Phase 2
            censo_cursos_enriquecidos = self.run_phase_2_transform_censo(phase1_result)
            
            # Phase 3
            sisu_aggregations, sisu_final_docs = self.run_phase_3_transform_sisu(phase1_result)
            
            # Phase 4-6
            final_documents = self.run_phase_456_join_build_metrics(
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
