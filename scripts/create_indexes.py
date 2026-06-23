#!/usr/bin/env python3
"""
Phase 9: MongoDB Indexes Creation

Creates all required indexes on gold_course_indicators and sisu_aggregated collections
for optimal query performance.

Indexes created:
- Basic indexes: ano, uf+ano, ies.idIes+ano, curso.idCurso+ano, etc.
- ESR (Equality, Sort, Range) compound index for complex queries
- Indexes support filtering, sorting, and range queries
"""

import sys
import os
from typing import List, Dict

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.clients import MongoDBClient
from src.config import MONGO_COLLECTION_GOLD_COURSE, MONGO_COLLECTION_SISU_AGGREGATED
from src.utils import get_logger

logger = get_logger(__name__)


class IndexManager:
    """Manages MongoDB index creation and documentation"""
    
    # Index definitions for gold_course_indicators collection
    GOLD_INDEXES = [
        {
            "name": "idx_ano",
            "keys": [("ano", 1)],
            "sparse": False,
            "unique": False,
            "description": "Partitioning index for year-based queries"
        },
        {
            "name": "idx_uf_ano",
            "keys": [("uf", 1), ("ano", 1)],
            "sparse": False,
            "unique": False,
            "description": "UF + ano for regional analysis"
        },
        {
            "name": "idx_ies_ano",
            "keys": [("ies.idIes", 1), ("ano", 1)],
            "sparse": False,
            "unique": False,
            "description": "IES + ano for institutional drill-down"
        },
        {
            "name": "idx_curso_ano",
            "keys": [("curso.idCurso", 1), ("ano", 1)],
            "sparse": False,
            "unique": False,
            "description": "Curso + ano for course-level analysis"
        },
        {
            "name": "idx_modalidade_ano",
            "keys": [("curso.tipoModalidadeEnsino", 1), ("ano", 1)],
            "sparse": False,
            "unique": False,
            "description": "Teaching modality + ano (on-site vs distance)"
        },
        {
            "name": "idx_categoria_admin_ano",
            "keys": [("ies.tipoCategoriaAdministrativa", 1), ("ano", 1)],
            "sparse": False,
            "unique": False,
            "description": "Administrative category + ano for sector analysis"
        },
        {
            "name": "idx_area_geral_ano",
            "keys": [("curso.areaGeral.id", 1), ("ano", 1)],
            "sparse": False,
            "unique": False,
            "description": "General area + ano for subject analysis"
        },
        {
            "name": "idx_sisu_sexo_ano",
            "keys": [("sisu.demografia.porSexo.sexo", 1), ("ano", 1)],
            "sparse": False,
            "unique": False,
            "description": "SISU demographics by sex + ano"
        },
        {
            "name": "idx_sisu_faixa_etaria_ano",
            "keys": [("sisu.demografia.porFaixaEtaria.faixaEtaria", 1), ("ano", 1)],
            "sparse": False,
            "unique": False,
            "description": "SISU demographics by age group + ano"
        },
        {
            "name": "idx_esr_pcd_analysis",
            "keys": [
                ("ano", 1),                              # Equality: filter by year
                ("uf", 1),                               # Equality: filter by state
                ("indicadoresDeficiencia.matriculas", -1),  # Sort: descending by PcD enrollments
                ("metricasCalculadas.percentualMatriculasPcd", 1)  # Range: percentage range
            ],
            "sparse": False,
            "unique": False,
            "description": "ESR index for PcD enrollment analysis: filter year+UF, sort by PcD count, range by percentage"
        },
    ]
    
    # Index definitions for sisu_aggregated collection
    SISU_INDEXES = [
        {
            "name": "idx_ano",
            "keys": [("ano", 1)],
            "sparse": False,
            "unique": False,
            "description": "Year partitioning"
        },
        {
            "name": "idx_ano_ies_curso",
            "keys": [("ano", 1), ("id_ies", 1), ("id_curso", 1)],
            "sparse": False,
            "unique": False,
            "description": "Compound key for $lookup joins with gold_course_indicators"
        },
        {
            "name": "idx_uf_ano",
            "keys": [("sigla_uf_ies", 1), ("ano", 1)],
            "sparse": False,
            "unique": False,
            "description": "UF + ano for SISU-level regional queries"
        },
    ]
    
    def __init__(self):
        self.mongo_client = MongoDBClient()
        self.db = self.mongo_client.db
    
    def create_indexes(self, collection_name: str, indexes: List[Dict], drop_existing: bool = False):
        """
        Create indexes on a MongoDB collection
        
        Args:
            collection_name: Name of the collection
            indexes: List of index definitions
            drop_existing: If True, drop collection before creating indexes (for clean rebuild)
        """
        collection = self.db[collection_name]
        
        logger.info(f"\nCreating indexes on collection: {collection_name}")
        logger.info("=" * 80)
        
        # Get existing indexes before creation
        existing_indexes = set()
        try:
            for idx_info in collection.list_indexes():
                existing_indexes.add(idx_info['name'])
        except Exception as e:
            logger.warning(f"Could not list existing indexes: {e}")
        
        created_count = 0
        skipped_count = 0
        
        for idx_def in indexes:
            idx_name = idx_def['name']
            idx_keys = idx_def['keys']
            description = idx_def.get('description', '')
            
            try:
                if idx_name in existing_indexes:
                    logger.info(f"  ⊘ {idx_name}: Already exists (skipped)")
                    skipped_count += 1
                    continue
                
                # Create index
                collection.create_index(
                    idx_keys,
                    name=idx_name,
                    sparse=idx_def.get('sparse', False),
                    unique=idx_def.get('unique', False),
                )
                
                logger.info(f"  {idx_name}: Created")
                if description:
                    logger.info(f"      - {description}")
                created_count += 1
                
            except Exception as e:
                logger.error(f"   {idx_name}: Failed - {e}")
        
        logger.info(f"\n  Summary: {created_count} created, {skipped_count} skipped")
        return created_count, skipped_count
    
    def create_all_indexes(self):
        """Create all indexes on both collections"""
        logger.info("\nPHASE 9: CREATING MONGODB INDEXES")
        
        try:
            # Create gold_course_indicators indexes
            gold_created, gold_skipped = self.create_indexes(
                MONGO_COLLECTION_GOLD_COURSE,
                self.GOLD_INDEXES
            )
            
            # Create sisu_aggregated indexes
            sisu_created, sisu_skipped = self.create_indexes(
                MONGO_COLLECTION_SISU_AGGREGATED,
                self.SISU_INDEXES
            )
            
            logger.info("\nPHASE 9 COMPLETE")
            logger.info(f"\n Index Creation Summary:")
            logger.info(f"  gold_course_indicators: {gold_created} created, {gold_skipped} skipped")
            logger.info(f"  sisu_aggregated: {sisu_created} created, {sisu_skipped} skipped")
            logger.info(f"  Total: {gold_created + sisu_created} created")
            
            return True
            
        except Exception as e:
            logger.error(f" Index creation failed: {e}", exc_info=True)
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create MongoDB indexes for ETL data")
    parser.add_argument("--drop", action="store_true", help="Drop existing indexes before creation")
    
    args = parser.parse_args()
    
    try:
        manager = IndexManager()
        success = manager.create_all_indexes()
        
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
