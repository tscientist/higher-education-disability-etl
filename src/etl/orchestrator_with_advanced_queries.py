"""
ETL Pipeline com Queries Avançadas MongoDB

Executa ETL + cria agregações complexas usando MongoDB Aggregation Pipeline.

Features:
- $lookup (joins entre collections)
- $group (agregações multi-nível)
- $facet (buscas facetadas multi-dimensionais)
- $unwind (desconstrução de arrays)
- $elemMatch (busca em arrays)
- Text search
- Ranking com $sort
"""

from datetime import datetime
from src.etl.orchestrator_batch_wrapper import ETLPipelineOrchestratorBatch
from src.queries.mongodb_advanced_queries import MongoDBAdvancedQueries
from src.clients import MongoDBClient
from src.config import MONGO_COLLECTION_GOLD_COURSE, MONGO_COLLECTION_SISU_AGGREGATED
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ETLPipelineWithAdvancedQueries:
    """Executa ETL + Queries avançadas MongoDB"""
    
    def __init__(self):
        self.batch_orchestrator = ETLPipelineOrchestratorBatch()
        self.queries = MongoDBAdvancedQueries()
        self.mongo_client = MongoDBClient()
    
    def run_etl_pipeline(self):
        """Executa o pipeline ETL completo em batches"""
        logger.info("\n" + "="*80)
        logger.info("FASE 1: EXECUTANDO ETL PIPELINE")
        logger.info("="*80 + "\n")
        
        result = self.batch_orchestrator.run_full_pipeline_batch()
        return result
    
    def execute_aggregation_queries(self):
        """Executa queries avançadas após ETL completo"""
        logger.info("\n" + "="*80)
        logger.info("FASE 2: EXECUTANDO QUERIES AVANÇADAS COM AGGREGATION PIPELINE")
        logger.info("="*80 + "\n")
        
        results = {}
        
        try:
            # ====================================================================
            # 1. QUERIES COM FILTROS E PROJEÇÕES
            # ====================================================================
            logger.info("\n[1/8] Buscando cursos com dados de deficiência...")
            results["cursos_com_deficiencia"] = self.queries.find_courses_with_disability_data(
                MONGO_COLLECTION_GOLD_COURSE,
                min_disabled_count=1
            )
            logger.info(f"✓ Encontrados {len(results['cursos_com_deficiencia'])} cursos")
            
            # ====================================================================
            # 2. QUERIES COM $ELEMATCH (BUSCA EM ARRAYS)
            # ====================================================================
            logger.info("\n[2/8] Buscando cursos com deficiência VISUAL...")
            results["cursos_deficiencia_visual"] = self.queries.find_courses_by_disability_type(
                MONGO_COLLECTION_GOLD_COURSE,
                "visual"
            )
            logger.info(f"✓ Encontrados {len(results['cursos_deficiencia_visual'])} cursos com deficiência visual")
            
            # ====================================================================
            # 3. AGGREGATION PIPELINE: $GROUP + $SUM + $AVG
            # ====================================================================
            logger.info("\n[3/8] Agregando estatísticas de deficiência por IES...")
            results["stats_por_ies"] = self.queries.aggregate_disability_stats_by_ies(
                MONGO_COLLECTION_GOLD_COURSE
            )
            logger.info(f"✓ Agregadas {len(results['stats_por_ies'])} instituições")
            
            if results["stats_por_ies"]:
                top_ies = results["stats_por_ies"][0]
                logger.info(f"  Top IES: {top_ies.get('sigla_ies', 'N/A')} "
                          f"({top_ies.get('total_alunos_deficiencia', 0)} alunos)")
            
            # ====================================================================
            # 4. AGGREGATION PIPELINE: $UNWIND + $GROUP (DESCONSTRUÇÃO DE ARRAYS)
            # ====================================================================
            logger.info("\n[4/8] Agregando estatísticas por tipo de deficiência...")
            results["stats_por_tipo_deficiencia"] = self.queries.aggregate_disability_by_type(
                MONGO_COLLECTION_GOLD_COURSE
            )
            logger.info(f"✓ Encontrados {len(results['stats_por_tipo_deficiencia'])} tipos de deficiência")
            
            for def_type in results["stats_por_tipo_deficiencia"][:3]:
                logger.info(f"  - {def_type.get('_id', 'N/A')}: {def_type.get('total_alunos', 0)} alunos")
            
            # ====================================================================
            # 5. AGGREGATION COM $LOOKUP (JOIN ENTRE COLLECTIONS)
            # ====================================================================
            logger.info("\n[5/8] Fazendo LEFT JOIN com SISU agregado usando $lookup...")
            results["cursos_com_sisu"] = self.queries.join_courses_with_sisu_aggregates(
                MONGO_COLLECTION_GOLD_COURSE,
                MONGO_COLLECTION_SISU_AGGREGATED
            )
            logger.info(f"✓ JOIN concluído: {len(results['cursos_com_sisu'])} registros")
            
            matched = sum(1 for r in results["cursos_com_sisu"] if r.get("match_sisu", False))
            logger.info(f"  Matches com SISU: {matched}")
            
            # ====================================================================
            # 6. ADVANCED ANALYSIS: MÚLTIPLOS ESTÁGIOS DO PIPELINE
            # ====================================================================
            logger.info("\n[6/8] Executando análise avançada (IES com 5+ cursos)...")
            results["analise_avancada"] = self.queries.advanced_disability_analysis(
                MONGO_COLLECTION_GOLD_COURSE,
                min_courses=5
            )
            logger.info(f"✓ Análise concluída: {len(results['analise_avancada'])} instituições qualificadas")
            
            # ====================================================================
            # 7. FACETED SEARCH: MÚLTIPLOS PIPELINES COM $FACET
            # ====================================================================
            logger.info("\n[7/8] Executando busca facetada (multi-dimensional)...")
            facet_result = self.queries.faceted_search_disability(
                MONGO_COLLECTION_GOLD_COURSE
            )
            results["faceted_search"] = facet_result
            
            logger.info(f"✓ Busca facetada concluída:")
            logger.info(f"  Regiões: {len(facet_result.get('por_regiao', []))}")
            logger.info(f"  Tipos de deficiência: {len(facet_result.get('por_deficiencia', []))}")
            logger.info(f"  Top 10 cursos: {len(facet_result.get('top_cursos', []))}")
            
            # ====================================================================
            # 8. RANKING: ORDENAÇÃO E RANKING COM $SORT
            # ====================================================================
            logger.info("\n[8/8] Gerando ranking de IES por percentual de deficiência...")
            results["ranking_ies"] = self.queries.rank_ies_by_disability_percentage(
                MONGO_COLLECTION_GOLD_COURSE
            )
            logger.info(f"✓ Ranking concluído: {len(results['ranking_ies'])} instituições")
            
            if results["ranking_ies"]:
                for i, ies in enumerate(results["ranking_ies"][:3], 1):
                    logger.info(f"  {i}. {ies.get('sigla_ies', 'N/A')}: "
                              f"{ies.get('percentual_deficiencia', 0):.2f}%")
            
            logger.info("\n✓ Todas as queries avançadas executadas com sucesso!")
            
            return results
            
        except Exception as e:
            logger.error(f"Erro ao executar queries avançadas: {e}", exc_info=True)
            raise
    
    def generate_summary_report(self, etl_result, query_results):
        """Gera relatório final com resultados"""
        logger.info("\n" + "="*80)
        logger.info("RELATÓRIO FINAL - ETL + QUERIES AVANÇADAS")
        logger.info("="*80 + "\n")
        
        # Resumo ETL
        logger.info("📊 RESUMO DO ETL:")
        logger.info(f"  Batches processados: {etl_result.get('total_batches', 0)}")
        logger.info(f"  Documentos processados: {etl_result.get('total_docs', 0):,}")
        logger.info(f"  Duração: {etl_result.get('duration_seconds', 0):.2f}s")
        logger.info(f"  Status: {'✓ SUCESSO' if etl_result.get('success') else '✗ FALHA'}")
        
        # Resumo Queries
        logger.info("\n📈 RESULTADOS DAS QUERIES AVANÇADAS:")
        
        if "cursos_com_deficiencia" in query_results:
            logger.info(f"  Cursos com deficiência: {len(query_results['cursos_com_deficiencia'])}")
        
        if "stats_por_ies" in query_results:
            logger.info(f"  IES agregadas: {len(query_results['stats_por_ies'])}")
        
        if "stats_por_tipo_deficiencia" in query_results:
            logger.info(f"  Tipos de deficiência: {len(query_results['stats_por_tipo_deficiencia'])}")
        
        if "ranking_ies" in query_results:
            logger.info(f"  IES no ranking: {len(query_results['ranking_ies'])}")
        
        # Exemplos de dados
        logger.info("\n📋 EXEMPLOS DE DADOS AGREGADOS:")
        
        if query_results.get("stats_por_ies"):
            top_ies = query_results["stats_por_ies"][0]
            logger.info(f"\n  Top IES por alunos com deficiência:")
            logger.info(f"    - Sigla: {top_ies.get('sigla_ies')}")
            logger.info(f"    - Total alunos com deficiência: {top_ies.get('total_alunos_deficiencia')}")
            logger.info(f"    - Percentual: {top_ies.get('percentual_deficiencia', 0):.2f}%")
            logger.info(f"    - Total de cursos: {top_ies.get('total_cursos')}")
        
        if query_results.get("ranking_ies"):
            logger.info(f"\n  Top 3 IES por percentual de deficiência:")
            for i, ies in enumerate(query_results["ranking_ies"][:3], 1):
                logger.info(f"    {i}. {ies.get('sigla_ies')} - {ies.get('percentual_deficiencia'):.2f}%")
        
        logger.info("\n" + "="*80 + "\n")
    
    def run_full_pipeline_with_queries(self):
        """Executa ETL completo + Queries avançadas"""
        start_time = datetime.now()
        
        logger.info("\n" + "="*80)
        logger.info("ETL PIPELINE COM QUERIES AVANÇADAS MONGODB")
        logger.info("="*80 + "\n")
        
        try:
            # Executar ETL
            etl_result = self.run_etl_pipeline()
            
            if not etl_result.get("success"):
                logger.error("ETL falhou, pulando queries avançadas")
                return {
                    "success": False,
                    "etl_result": etl_result,
                    "error": "ETL pipeline failed"
                }
            
            # Executar Queries Avançadas
            query_results = self.execute_aggregation_queries()
            
            # Gerar Relatório
            self.generate_summary_report(etl_result, query_results)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "etl_result": etl_result,
                "query_results": query_results,
                "duration_seconds": duration,
                "total_queries_executed": len(query_results)
            }
            
        except Exception as e:
            logger.error(f"Erro no pipeline com queries: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
