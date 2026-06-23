"""
Main entry point for ETL pipeline

Usage:
    python main.py --mode etl-2022              # 2022 ETL (Phases 4-8)
    python main.py --mode setup-bigquery        # Setup BigQuery tables (Phases 2-3)
    python main.py --mode create-indexes        # Create MongoDB indexes (Phase 9)
    python main.py --mode explain-performance   # Performance comparison (Phase 15)
    python main.py --mode with-queries          # Full ETL with queries
    python main.py --mode extract               # Extract only (Phase 1)
    python main.py --mode build                 # Extract through Build (Phases 1-6)
    python main.py --mode full                  # Full pipeline with MongoDB load
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
        choices=[
            "etl-2022",
            "setup-bigquery",
            "create-indexes",
            "explain-performance",
            "with-queries",
            "extract",
            "build",
            "full"
        ],
        default="with-queries",
        help="Modo de execucao"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reprocessing (ignore checkpoints)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == "etl-2022":
            logger.info("MODO: ETL 2022 (Phases 4-8)")
            from src.etl.orchestrator_2022 import ETLOrchestrator2022
            orchestrator = ETLOrchestrator2022()
            success = orchestrator.run(force=args.force)
            sys.exit(0 if success else 1)
        
        elif args.mode == "setup-bigquery":
            logger.info("MODO: SETUP BIGQUERY (Phases 2-3)")
            from src.etl.bigquery_intermediate import setup_intermediate_tables
            success = setup_intermediate_tables()
            sys.exit(0 if success else 1)
        
        elif args.mode == "create-indexes":
            logger.info("MODO: CREATE INDEXES (Phase 9)")
            from scripts.create_indexes import IndexManager
            manager = IndexManager()
            success = manager.create_all_indexes()
            sys.exit(0 if success else 1)
        
        elif args.mode == "explain-performance":
            logger.info("MODO: EXPLAIN PERFORMANCE (Phase 15)")
            from scripts.explain_index_performance import ExplainComparison
            comparison = ExplainComparison()
            success = comparison.run(force_drop=args.force)
            sys.exit(0 if success else 1)
        
        elif args.mode == "with-queries":
            logger.info("MODO: ETL + QUERIES AVANÇADAS")
            from src.etl.orchestrator_with_advanced_queries import ETLPipelineWithAdvancedQueries
            orchestrator = ETLPipelineWithAdvancedQueries()
            result = orchestrator.run_full_pipeline_with_queries()
            if not result.get("success"):
                logger.error("Pipeline failed")
                sys.exit(1)
        
        elif args.mode == "extract":
            logger.info("MODO: EXTRACT ONLY")
            # Legacy mode support
            pass
        
        elif args.mode == "build":
            logger.info("MODO: BUILD")
            # Legacy mode support
            pass
        
        elif args.mode == "full":
            logger.info("MODO: FULL PIPELINE")
            # Legacy mode support
            pass
        
        logger.info("\nPipeline executado com sucesso!")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
