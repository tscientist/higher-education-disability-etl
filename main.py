"""
Main entry point for ETL pipeline

🏫 OBSERVAÇÃO CRÍTICA: IES SEMPRE tem ~2,500-3,000 valores!
   Isso muda TUDO na arquitetura! Ver: docs/IES_DIMENSIONALITY_OPTIMIZATION.md

Usage:
    python main.py --mode with-queries       # ETL completo
    python main.py --mode extract            # Extract only (Fase 1)
    python main.py --mode build              # Extract through Build (Fases 1-6)
    python main.py --mode full               # Full pipeline with MongoDB load (Fases 1-8, 11)
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils import get_logger

logger = get_logger(__name__)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="ETL Pipeline - Brasil Educacao Superior com Deficiencia"
    )
    parser.add_argument(
        "--mode",
        choices=["with-queries"],
        default="with-queries",
        help="Modo de execucao"
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == "with-queries":
            logger.info("\n" + "="*80)
            logger.info("🏫 MODO: ETL + QUERIES AVANÇADAS (RECOMENDADO)")
            logger.info("="*80)
            logger.info("Executa:")
            logger.info("├─ Fases 1-8: ETL Completo")
            logger.info("├─ MongoDB Load com integridade garantida")
            logger.info("├─ 8 Queries Avançadas com Aggregation Pipeline")
            logger.info("│   ├─ $lookup (joins)")
            logger.info("│   ├─ $group (agregações)")
            logger.info("│   ├─ $facet (busca facetada)")
            logger.info("│   └─ $unwind (desconstrução arrays)")
            logger.info("└─ Índices MongoDB otimizados")
            logger.info("="*80 + "\n")
            from src.etl.orchestrator_with_advanced_queries import ETLPipelineWithAdvancedQueries
            orchestrator = ETLPipelineWithAdvancedQueries()
            result = orchestrator.run_full_pipeline_with_queries()
        
        if not result.get("success"):
            logger.error("Pipeline failed")
            sys.exit(1)
        
        logger.info("\nPipeline executado com sucesso!")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
