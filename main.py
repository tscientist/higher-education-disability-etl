"""Main entry point for ETL pipeline"""
import sys

from src.etl import ETLPipeline
from src.utils import get_logger

logger = get_logger(__name__)


def main():
    """Main function"""
    try:
        logger.info("Iniciando ETL pipeline...")
        pipeline = ETLPipeline()
        pipeline.run()
        logger.info("Pipeline finalizado com sucesso")
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
