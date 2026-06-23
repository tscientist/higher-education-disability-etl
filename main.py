"""
Main entry point for ETL pipeline

Usage:
    python main.py                      # Run full pipeline
    python main.py --mode extract       # Extract only (Fase 1)
    python main.py --mode build         # Extract through Build (Fases 1-6)
    python main.py --mode full          # Full pipeline with MongoDB load (Fases 1-8, 11)
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.etl.pipeline_orchestrator import ETLPipelineOrchestrator
from src.utils import get_logger

logger = get_logger(__name__)


def main():
    """Main function"""
    try:
        orchestrator = ETLPipelineOrchestrator()
        result = orchestrator.run_full_pipeline()
        
        if not result.get("success"):
            logger.error("Pipeline failed")
            sys.exit(1)
        
        logger.info("Pipeline executado com sucesso")
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
