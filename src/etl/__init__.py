"""
ETL pipeline module for data extraction, transformation and loading
"""

from src.etl.pipeline import ETLPipeline
from src.etl.phase_extract import PhaseExtract
from src.etl.phase_transform_censo import PhaseTransformCenso
from src.etl.phase_transform_sisu import PhaseTransformSISU
from src.etl.phase_join_build_metrics import PhaseJoinBuildMetrics
from src.etl.phase_mongodb_load import PhaseMongoDBLoad
from src.etl.phase_create_indexes import PhaseCreateIndexes
from src.etl.phase_validation import PhaseValidation
from src.etl.pipeline_orchestrator import ETLPipelineOrchestrator

__all__ = [
    "ETLPipeline",
    "PhaseExtract",
    "PhaseTransformCenso",
    "PhaseTransformSISU",
    "PhaseJoinBuildMetrics",
    "PhaseMongoDBLoad",
    "PhaseCreateIndexes",
    "PhaseValidation",
    "ETLPipelineOrchestrator",
]
