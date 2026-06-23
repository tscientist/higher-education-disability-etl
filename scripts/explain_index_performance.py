#!/usr/bin/env python3
"""
Phase 15: MongoDB explain() Performance Comparison Script

This script demonstrates performance improvements from indexing:
1. Run query WITHOUT index (expect COLLSCAN)
2. Create ESR index
3. Run query WITH index (expect IXSCAN)
4. Compare execution statistics

This is a practical demonstration of index impact on complex PcD queries.
"""

import sys
import os
import json
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.clients import MongoDBClient
from src.config import MONGO_COLLECTION_GOLD_COURSE
from src.utils import get_logger

logger = get_logger(__name__)


class ExplainComparison:
    """Compare query performance before/after indexing"""
    
    # Test query that benefits from ESR index
    TEST_QUERY = {
        "ano": 2022,
        "uf": "SP",
        "metricasCalculadas.percentualMatriculasPcd": {
            "$gte": 5,
            "$lte": 20
        }
    }
    
    TEST_SORT = {
        "indicadoresDeficiencia.matriculas": -1
    }
    
    ESR_INDEX_DEF = [
        ("ano", 1),
        ("uf", 1),
        ("indicadoresDeficiencia.matriculas", -1),
        ("metricasCalculadas.percentualMatriculasPcd", 1)
    ]
    
    def __init__(self):
        self.mongo_client = MongoDBClient()
        self.db = self.mongo_client.db
        self.collection = self.db[MONGO_COLLECTION_GOLD_COURSE]
    
    def get_document_count(self) -> int:
        """Get total document count"""
        return self.collection.count_documents({})
    
    def check_index_exists(self, index_name: str) -> bool:
        """Check if index exists"""
        try:
            for idx in self.collection.list_indexes():
                if idx['name'] == index_name:
                    return True
        except Exception as e:
            logger.warning(f"Error checking indexes: {e}")
        return False
    
    def drop_index(self, index_name: str) -> bool:
        """Drop an index"""
        try:
            self.collection.drop_index(index_name)
            logger.info(f" Dropped index: {index_name}")
            return True
        except Exception as e:
            logger.warning(f"Index not found or error: {e}")
            return False
    
    def create_index(self, index_def, index_name: str) -> bool:
        """Create an index"""
        try:
            self.collection.create_index(index_def, name=index_name)
            logger.info(f" Created index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating index: {e}")
            return False
    
    def run_explain(self, stage: str) -> Dict[str, Any]:
        """Run explain on test query and return stats"""
        try:
            explain_result = self.collection.find(
                self.TEST_QUERY
            ).sort(self.TEST_SORT[0], self.TEST_SORT[1]).explain()
            
            return self._parse_explain(explain_result, stage)
        except Exception as e:
            logger.error(f"Error running explain: {e}")
            return None
    
    def _parse_explain(self, explain_result: Dict, stage: str) -> Dict[str, Any]:
        """Parse explain output for key metrics"""
        try:
            exec_stats = explain_result.get("executionStats", {})
            
            return {
                "stage": stage,
                "executionStage": explain_result.get("executionStats", {}).get("executionStages", {}).get("stage", "UNKNOWN"),
                "totalDocsExamined": exec_stats.get("totalDocsExamined", 0),
                "nReturned": exec_stats.get("nReturned", 0),
                "executionTimeMillis": exec_stats.get("executionTimeMillis", 0),
                "executionMemoryUsage": exec_stats.get("executionMemoryUsageBytesEstimate", 0),
                "fullExplain": explain_result
            }
        except Exception as e:
            logger.error(f"Error parsing explain: {e}")
            return None
    
    def print_comparison(self, before: Dict, after: Dict):
        """Print before/after comparison"""
        logger.info("\n" + "=" * 100)
        logger.info("EXPLAIN() COMPARISON: WITH vs WITHOUT INDEX")
        logger.info("=" * 100)
        
        if not before or not after:
            logger.error("Cannot compare - missing explain results")
            return
        
        # Header
        logger.info(f"\n📊 Query Pattern:")
        logger.info(f"  Filters: ano=2022, uf=SP, percentualMatriculasPcd in [5,20]%")
        logger.info(f"  Sort: indicadoresDeficiencia.matriculas DESC")
        
        # Metrics comparison
        logger.info(f"\n┌─ BEFORE (WITHOUT INDEX)")
        logger.info(f"├─ Stage: {before['executionStage']}")
        logger.info(f"├─ Docs Examined: {before['totalDocsExamined']:,}")
        logger.info(f"├─ Results Returned: {before['nReturned']:,}")
        logger.info(f"├─ Execution Time: {before['executionTimeMillis']}ms")
        logger.info(f"├─ Memory Used: {before['executionMemoryUsage']:,} bytes")
        
        efficiency_before = (before['nReturned'] / before['totalDocsExamined'] * 100) if before['totalDocsExamined'] > 0 else 0
        logger.info(f"└─ Efficiency: {efficiency_before:.1f}% ({before['nReturned']:,}/{before['totalDocsExamined']:,})")
        
        logger.info(f"\n┌─ AFTER (WITH ESR INDEX)")
        logger.info(f"├─ Stage: {after['executionStage']}")
        logger.info(f"├─ Docs Examined: {after['totalDocsExamined']:,}")
        logger.info(f"├─ Results Returned: {after['nReturned']:,}")
        logger.info(f"├─ Execution Time: {after['executionTimeMillis']}ms")
        logger.info(f"├─ Memory Used: {after['executionMemoryUsage']:,} bytes")
        
        efficiency_after = (after['nReturned'] / after['totalDocsExamined'] * 100) if after['totalDocsExamined'] > 0 else 0
        logger.info(f"└─ Efficiency: {efficiency_after:.1f}% ({after['nReturned']:,}/{after['totalDocsExamined']:,})")
        
        # Improvements
        logger.info(f"\n📈 IMPROVEMENTS")
        if before['executionTimeMillis'] > 0:
            speedup = before['executionTimeMillis'] / after['executionTimeMillis']
            logger.info(f"├─ Speed: {speedup:.1f}x faster ({before['executionTimeMillis']}ms → {after['executionTimeMillis']}ms)")
        
        if before['totalDocsExamined'] > 0:
            docs_reduction = (1 - after['totalDocsExamined'] / before['totalDocsExamined']) * 100
            logger.info(f"├─ Docs Examined: {docs_reduction:.1f}% reduction")
        
        if before['executionMemoryUsage'] > 0:
            memory_reduction = (1 - after['executionMemoryUsage'] / before['executionMemoryUsage']) * 100
            logger.info(f"├─ Memory: {memory_reduction:.1f}% reduction")
        
        logger.info(f"└─ Index Hit: {before['executionStage']} → {after['executionStage']}")
        
        # Verdict
        logger.info(f"\n✅ VERDICT")
        if after['executionStage'] == 'IXSCAN':
            logger.info(f"   Index is being used! Query uses fast index scan.")
            if speedup > 10:
                logger.info(f"   Significant performance improvement ({speedup:.1f}x faster).")
        else:
            logger.info(f"   ⚠️  Index may not be optimized for this query pattern.")
    
    def run(self, force_drop: bool = False):
        """Run the complete comparison"""
        logger.info("\n" + "=" * 100)
        logger.info("PHASE 15: EXPLAIN() PERFORMANCE COMPARISON")
        logger.info("=" * 100)
        
        try:
            # Check collection has data
            doc_count = self.get_document_count()
            logger.info(f"\n📊 Collection: {MONGO_COLLECTION_GOLD_COURSE}")
            logger.info(f"   Documents: {doc_count:,}")
            
            if doc_count == 0:
                logger.error("Collection is empty. Run ETL first.")
                return False
            
            index_name = "idx_esr_pcd_analysis"
            
            # Step 1: Drop index if exists
            if force_drop or self.check_index_exists(index_name):
                logger.info(f"\n[STEP 1] Dropping index: {index_name}")
                self.drop_index(index_name)
                
                # Run explain WITHOUT index
                logger.info(f"\n[STEP 2] Running explain WITHOUT index...")
                import time
                time.sleep(1)  # Allow MongoDB to update
                before_stats = self.run_explain("WITHOUT_INDEX")
                
                if not before_stats:
                    logger.error("Failed to run explain without index")
                    return False
                
                logger.info(f"   Stage: {before_stats['executionStage']}")
                logger.info(f"   Docs examined: {before_stats['totalDocsExamined']:,}")
                logger.info(f"   Execution time: {before_stats['executionTimeMillis']}ms")
            else:
                logger.warning("Index doesn't exist yet. Skipping 'before' test.")
                before_stats = None
            
            # Step 2: Create ESR index
            logger.info(f"\n[STEP 3] Creating ESR index: {index_name}")
            self.create_index(self.ESR_INDEX_DEF, index_name)
            
            # Step 3: Run explain WITH index
            logger.info(f"\n[STEP 4] Running explain WITH index...")
            import time
            time.sleep(1)  # Allow MongoDB to use index
            after_stats = self.run_explain("WITH_INDEX")
            
            if not after_stats:
                logger.error("Failed to run explain with index")
                return False
            
            logger.info(f"   Stage: {after_stats['executionStage']}")
            logger.info(f"   Docs examined: {after_stats['totalDocsExamined']:,}")
            logger.info(f"   Execution time: {after_stats['executionTimeMillis']}ms")
            
            # Step 4: Compare and print
            if before_stats:
                self.print_comparison(before_stats, after_stats)
            else:
                logger.info(f"\n✅ Index created and ready to use")
                logger.info(f"   Execution time with index: {after_stats['executionTimeMillis']}ms")
                logger.info(f"   Stage: {after_stats['executionStage']}")
            
            logger.info("\n" + "=" * 100)
            logger.info("PHASE 15 COMPLETE")
            logger.info("=" * 100)
            
            return True
            
        except Exception as e:
            logger.error(f"  Comparison failed: {e}", exc_info=True)
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Compare MongoDB query performance with/without index"
    )
    parser.add_argument(
        "--force-drop",
        action="store_true",
        help="Force drop existing index before comparison"
    )
    
    args = parser.parse_args()
    
    try:
        comparison = ExplainComparison()
        success = comparison.run(force_drop=args.force_drop)
        
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
