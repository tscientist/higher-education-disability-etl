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
from src.etl.fase_1_extract import Fase1Extract
from src.etl.fase_2_transform_censo import Fase2TransformCenso
from src.etl.fase_3_transform_sisu import Fase3TransformSISU
from src.etl.fase_456_join_build_metrics import Fase456JoinBuildAndMetrics
from src.etl.fase_7_mongodb_load import Fase7MongoDBLoad
from src.etl.fase_8_create_indexes import Fase8CreateIndexes
from src.queries.mongodb_advanced_queries import MongoDBAdvancedQueries
from src.clients import MongoDBClient, BigQueryClient
from src.config import (
    MONGO_COLLECTION_GOLD_COURSE, 
    MONGO_COLLECTION_SISU_AGGREGATED, 
    ETL_START_YEAR, 
    ETL_END_YEAR,
    BIGQUERY_DATASET,
    BQ_TABLE_SISU_MICRODADOS,
    BQ_TABLE_CENSO_IES,
    BQ_TABLE_CENSO_CURSO,
    ETL_BATCH_SIZE
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ETLPipelineWithAdvancedQueries:
    """Executa ETL + Queries avançadas MongoDB"""
    
    def __init__(self):
        self.queries = MongoDBAdvancedQueries()
        self.mongo_client = MongoDBClient()
        self.total_docs_processed = 0
    
    def run_etl_pipeline(self):
        """Executa o pipeline ETL completo em batches"""
        logger.info("\n" + "="*80)
        logger.info("FASE 1: EXECUTANDO ETL PIPELINE")
        logger.info("="*80 + "\n")
        
        try:
            from src.clients import BigQueryClient
            
            fase1 = Fase1Extract()
            fase2 = Fase2TransformCenso()
            fase3 = Fase3TransformSISU()
            fase456 = Fase456JoinBuildAndMetrics()
            fase7 = Fase7MongoDBLoad()
            fase8 = Fase8CreateIndexes()
            bq_client = BigQueryClient()
            
            # ========================================================================
            # PASSO 1: Ler SISU COMPLETO e criar índice
            # ========================================================================
            logger.info("\n[PASSO 1] Lendo SISU COMPLETO do BigQuery (operação única)...")
            sisu_agg_all = bq_client.aggregate_sisu_by_course_optimized(
                BIGQUERY_DATASET,
                BQ_TABLE_SISU_MICRODADOS,
                year_range=(ETL_START_YEAR, ETL_END_YEAR)
            )
            logger.info(f"SISU Agregado lido: {len(sisu_agg_all)} documentos agregados")
            
            # Criar índice para join rápido
            sisu_index = {}
            for sisu_doc in sisu_agg_all:
                key = (sisu_doc.get("ano"), str(sisu_doc.get("id_ies")), str(sisu_doc.get("id_curso")))
                sisu_index[key] = sisu_doc
            logger.info(f"Indice SISU criado para {len(sisu_index)} combinações\n")
            
            # ========================================================================
            # PASSO 2: Ler CENSO IES 
            # ========================================================================
            logger.info("[PASSO 2] Lendo Censo IES...")
            censo_ies_all = bq_client.read_table(
                BIGQUERY_DATASET,
                BQ_TABLE_CENSO_IES,
                year_range=(ETL_START_YEAR, ETL_END_YEAR)
            )
            logger.info(f"Censo IES lido: {len(censo_ies_all)} registros\n")
            
            # ========================================================================
            # PASSO 3: Processar CENSO CURSO em BATCHES (com SISU índexado)
            # ========================================================================
            logger.info("[PASSO 3] Processando Censo Curso em batches com SISU índexado...")
            
            batch_count = 0
            for batch_num, batch_censo_cursos in bq_client.read_table_in_batches(
                BIGQUERY_DATASET,
                BQ_TABLE_CENSO_CURSO,
                year_range=(ETL_START_YEAR, ETL_END_YEAR),
                batch_size=ETL_BATCH_SIZE
            ):
                batch_count = batch_num
                logger.info(f"\n[Batch #{batch_num}] Processando {len(batch_censo_cursos)} cursos...")
                
                try:
                    # FASE 2: Transform CENSO
                    logger.info(f"  [Fase 2] Transformando CENSO...")
                    censo_t = fase2.transform_batch(
                        batch_censo_cursos,
                        censo_ies_all
                    )
                    
                    # FASE 3: Preparar SISU (já está em memória, apenas referência)
                    logger.info(f"  [Fase 3] SISU já em memória (índexado)...")
                    sisu_t = [sisu_index.get((c.get("ano"), str(c.get("id_ies")), str(c.get("id_curso")))) 
                             for c in batch_censo_cursos]
                    sisu_t = [s for s in sisu_t if s is not None]  # Remover None
                    
                    # FASES 4-6: Join, Build & Metrics
                    logger.info(f"  [Fases 4-6] Join e Build (O(1) lookup com índice)...")
                    docs_final = fase456.join_and_build_batch(
                        censo_t,
                        sisu_t,
                        year_range=(ETL_START_YEAR, ETL_END_YEAR)
                    )
                    
                    # FASE 7: Load MongoDB
                    logger.info(f"  [Fase 7] Carregando MongoDB ({len(docs_final)} docs)...")
                    load_result = fase7.load_batch(docs_final, batch_num)
                    
                    self.total_docs_processed += len(docs_final)
                    logger.info(f"Batch #{batch_num} concluído: {len(docs_final)} docs\n")
                    
                except Exception as e:
                    logger.error(f"Erro no batch #{batch_num}: {e}", exc_info=True)
                    continue
            
            # ========================================================================
            # PASSO 4: Carregar SISU agregado no MongoDB
            # ========================================================================
            logger.info("\n[PASSO 4] Carregando SISU agregado no MongoDB...")
            if sisu_agg_all:
                sisu_load_result = fase7.load_sisu_aggregated(sisu_agg_all)
                logger.info(f"SISU agregado carregado: {sisu_load_result['upserted']} inserted, "
                          f"{sisu_load_result['modified']} updated\n")
            else:
                logger.warning("⚠ Nenhum documento SISU agregado para carregar\n")
            
            # ========================================================================
            # PASSO 5: Criar índices
            # ========================================================================
            logger.info("[PASSO 5] Criando índices...")
            fase8.run()
            
            return {
                "success": True,
                "batches_processed": batch_count,
                "total_documents": self.total_docs_processed,
                "sisu_aggregated": len(sisu_agg_all)
            }
            
        except Exception as e:
            logger.error(f"Erro no ETL: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
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
            logger.info(f"Encontrados {len(results['cursos_com_deficiencia'])} cursos")
            
            # ====================================================================
            # 2. QUERIES COM $ELEMATCH (BUSCA EM ARRAYS)
            # ====================================================================
            logger.info("\n[2/8] Buscando cursos com deficiência VISUAL...")
            results["cursos_deficiencia_visual"] = self.queries.find_courses_by_disability_type(
                MONGO_COLLECTION_GOLD_COURSE,
                "visual"
            )
            logger.info(f"Encontrados {len(results['cursos_deficiencia_visual'])} cursos com deficiência visual")
            
            # ====================================================================
            # 3. AGGREGATION PIPELINE: $GROUP + $SUM + $AVG
            # ====================================================================
            logger.info("\n[3/8] Agregando estatísticas de deficiência por IES...")
            results["stats_por_ies"] = self.queries.aggregate_disability_stats_by_ies(
                MONGO_COLLECTION_GOLD_COURSE
            )
            logger.info(f"Agregadas {len(results['stats_por_ies'])} instituições")
            
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
            logger.info(f"Encontrados {len(results['stats_por_tipo_deficiencia'])} tipos de deficiência")
            
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
            logger.info(f"JOIN concluído: {len(results['cursos_com_sisu'])} registros")
            
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
            logger.info(f"Análise concluída: {len(results['analise_avancada'])} instituições qualificadas")
            
            # ====================================================================
            # 7. FACETED SEARCH: MÚLTIPLOS PIPELINES COM $FACET
            # ====================================================================
            logger.info("\n[7/8] Executando busca facetada (multi-dimensional)...")
            facet_result = self.queries.faceted_search_disability(
                MONGO_COLLECTION_GOLD_COURSE
            )
            results["faceted_search"] = facet_result
            
            logger.info(f"Busca facetada concluída:")
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
            logger.info(f"Ranking concluído: {len(results['ranking_ies'])} instituições")
            
            if results["ranking_ies"]:
                for i, ies in enumerate(results["ranking_ies"][:3], 1):
                    logger.info(f"  {i}. {ies.get('sigla_ies', 'N/A')}: "
                              f"{ies.get('percentual_deficiencia', 0):.2f}%")
            
            logger.info("\nTodas as queries avançadas executadas com sucesso!")
            
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
        logger.info(f"  Status: {'SUCESSO' if etl_result.get('success') else 'FALHA'}")
        
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
