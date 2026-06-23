#!/usr/bin/env python3
"""
Integration Test: Complete ETL Pipeline 2022

This script tests the full ETL pipeline in sequence:
1. Verify BigQuery staging tables exist
2. Create BigQuery intermediate tables (Phases 2-3)
3. Run ETL orchestrator (Phases 4-8)
4. Create MongoDB indexes (Phase 9)
5. Run sample queries
6. Validate data quality
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import get_logger
from src.clients import BigQueryClient, MongoDBClient
from src.config import (
    BIGQUERY_DATASET,
    MONGO_COLLECTION_GOLD_COURSE,
    BQ_TABLE_GOLD_COURSE_INDICATORS_2022
)

logger = get_logger(__name__)


class IntegrationTest:
    """Complete ETL integration test"""
    
    def __init__(self):
        self.bq_client = BigQueryClient()
        self.mongo_client = MongoDBClient()
        self.results = {
            "bigquery_setup": False,
            "etl_orchestrator": False,
            "indexes": False,
            "validation": False,
            "sample_queries": False
        }
    
    def test_bigquery_setup(self):
        """Test Phase 2-3: BigQuery setup"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 1: BigQuery Setup (Phases 2-3)")
        logger.info("=" * 80)
        
        try:
            from src.etl.bigquery_intermediate import setup_intermediate_tables
            
            logger.info("Running BigQuery setup...")
            success = setup_intermediate_tables()
            
            if success:
                logger.info("  BigQuery setup successful")
                self.results["bigquery_setup"] = True
                return True
            else:
                logger.error("✗ BigQuery setup failed")
                return False
        except Exception as e:
            logger.error(f"✗ Exception in BigQuery setup: {e}", exc_info=True)
            return False
    
    def test_etl_orchestrator(self):
        """Test Phase 4-8: ETL Orchestrator"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 2: ETL Orchestrator (Phases 4-8)")
        logger.info("=" * 80)
        
        try:
            from src.etl.orchestrator_2022 import ETLOrchestrator2022
            
            logger.info("Running ETL orchestrator for 2022...")
            orchestrator = ETLOrchestrator2022()
            success = orchestrator.run(force=True)
            
            if success:
                logger.info("  ETL orchestrator successful")
                self.results["etl_orchestrator"] = True
                return True
            else:
                logger.error("✗ ETL orchestrator failed")
                return False
        except Exception as e:
            logger.error(f"✗ Exception in ETL orchestrator: {e}", exc_info=True)
            return False
    
    def test_indexes(self):
        """Test Phase 9: Index Creation"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 3: Index Creation (Phase 9)")
        logger.info("=" * 80)
        
        try:
            from scripts.create_indexes import IndexManager
            
            logger.info("Creating MongoDB indexes...")
            manager = IndexManager()
            success = manager.create_all_indexes()
            
            if success:
                logger.info("  Index creation successful")
                self.results["indexes"] = True
                return True
            else:
                logger.error("✗ Index creation failed")
                return False
        except Exception as e:
            logger.error(f"✗ Exception in index creation: {e}", exc_info=True)
            return False
    
    def test_validation(self):
        """Test data quality validation"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 4: Data Quality Validation")
        logger.info("=" * 80)
        
        try:
            collection = self.mongo_client.db[MONGO_COLLECTION_GOLD_COURSE]
            
            # Check collection exists and has data
            doc_count = collection.count_documents({"ano": 2022})
            logger.info(f"Documents in collection: {doc_count:,}")
            
            if doc_count == 0:
                logger.error("✗ No documents in MongoDB collection")
                return False
            
            # Sample document
            sample = collection.find_one({"ano": 2022})
            if not sample:
                logger.error("✗ No sample document found")
                return False
            
            logger.info(f"\n  Sample Document:")
            logger.info(f"  _id: {sample['_id']}")
            logger.info(f"  IES: {sample['ies'].get('sigla')} - {sample['ies'].get('nome')}")
            logger.info(f"  Curso: {sample['curso'].get('nome')}")
            logger.info(f"  UF: {sample['uf']}")
            
            # Validate document structure
            required_fields = ['_id', 'ano', 'uf', 'ies', 'curso', 'indicadoresAluno', 
                              'indicadoresDeficiencia', 'metricasCalculadas']
            
            missing = [f for f in required_fields if f not in sample]
            if missing:
                logger.error(f"✗ Missing required fields: {missing}")
                return False
            
            logger.info(f"  All required fields present")
            
            # Check for null metrics
            metrics = sample.get('metricasCalculadas', {})
            logger.info(f"\n  Calculated Metrics:")
            for metric, value in metrics.items():
                logger.info(f"  {metric}: {value}")
            
            self.results["validation"] = True
            return True
            
        except Exception as e:
            logger.error(f"✗ Exception in validation: {e}", exc_info=True)
            return False
    
    def test_sample_queries(self):
        """Test sample MongoDB queries"""
        logger.info("\n" + "=" * 80)
        logger.info("TEST 5: Sample MongoDB Queries")
        logger.info("=" * 80)
        
        try:
            collection = self.mongo_client.db[MONGO_COLLECTION_GOLD_COURSE]
            
            # Query 1: Courses by state
            logger.info("\n[Query 1] Find courses in São Paulo")
            sp_courses = collection.count_documents({"uf": "SP", "ano": 2022})
            logger.info(f"  Found {sp_courses:,} courses in SP")
            
            # Query 2: Courses with PcD enrollment
            logger.info("\n[Query 2] Courses with PcD enrollment > 10")
            pcd_courses = collection.count_documents({
                "ano": 2022,
                "indicadoresDeficiencia.matriculas": {"$gt": 10}
            })
            logger.info(f"  Found {pcd_courses:,} courses")
            
            # Query 3: Aggregation - PcD by state
            logger.info("\n[Query 3] PcD enrollment by state")
            pipeline = [
                {"$match": {"ano": 2022}},
                {
                    "$group": {
                        "_id": "$uf",
                        "totalPcD": {"$sum": "$indicadoresDeficiencia.matriculas"},
                        "courses": {"$sum": 1}
                    }
                },
                {"$sort": {"totalPcD": -1}},
                {"$limit": 5}
            ]
            
            results = list(collection.aggregate(pipeline))
            logger.info(f"  Top 5 states by PcD enrollment:")
            for result in results:
                logger.info(f"  {result['_id']}: {result['totalPcD']:,} PcD students ({result['courses']} courses)")
            
            # Query 4: Explain with index
            logger.info("\n[Query 4] Query explain (check index usage)")
            explain_result = collection.find({
                "ano": 2022,
                "uf": "SP",
                "metricasCalculadas.percentualMatriculasPcd": {"$gte": 5}
            }).explain()
            
            exec_stage = explain_result.get("executionStats", {}).get("executionStages", {}).get("stage", "UNKNOWN")
            logger.info(f"  Query execution stage: {exec_stage}")
            
            if "IXSCAN" in exec_stage or "idx" in str(explain_result):
                logger.info(f"  → Using index (efficient!)")
            else:
                logger.warning(f"  → Not using index (consider creating indexes)")
            
            self.results["sample_queries"] = True
            return True
            
        except Exception as e:
            logger.error(f"✗ Exception in sample queries: {e}", exc_info=True)
            return False
    
    def run_all_tests(self):
        """Run all integration tests"""
        logger.info("\n" + "=" * 80)
        logger.info("INTEGRATION TEST: COMPLETE ETL PIPELINE 2022")
        logger.info("=" * 80)
        
        try:
            # Test sequence
            if not self.test_bigquery_setup():
                logger.error("Stopping: BigQuery setup failed")
                return False
            
            if not self.test_etl_orchestrator():
                logger.error("Stopping: ETL orchestrator failed")
                return False
            
            if not self.test_indexes():
                logger.error("Warning: Index creation failed (continuing)")
            
            if not self.test_validation():
                logger.error("Stopping: Data validation failed")
                return False
            
            if not self.test_sample_queries():
                logger.error("Warning: Sample queries failed (continuing)")
            
            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("INTEGRATION TEST SUMMARY")
            logger.info("=" * 80)
            
            for test_name, passed in self.results.items():
                status = "  PASS" if passed else "✗ FAIL"
                logger.info(f"{status}: {test_name}")
            
            all_passed = all(self.results.values())
            
            if all_passed:
                logger.info("\n✅ ALL TESTS PASSED!")
                return True
            else:
                logger.info("\n⚠️  SOME TESTS FAILED (see above)")
                return all(self.results[key] for key in ["bigquery_setup", "etl_orchestrator", "validation"])
        
        except Exception as e:
            logger.error(f"✗ Fatal error: {e}", exc_info=True)
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Integration test for ETL pipeline")
    parser.add_argument(
        "--skip-bigquery",
        action="store_true",
        help="Skip BigQuery setup (assume tables exist)"
    )
    
    args = parser.parse_args()
    
    try:
        test = IntegrationTest()
        
        if args.skip_bigquery:
            logger.info("Skipping BigQuery setup...")
            test.results["bigquery_setup"] = True
        
        success = test.run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
