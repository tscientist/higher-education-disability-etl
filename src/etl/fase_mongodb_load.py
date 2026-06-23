"""
Fase 7: MongoDB Load

Carrega documentos transformados para MongoDB com upsert.
Cria as coleções analíticas necessárias.
"""

from ..clients import MongoDBClient
from ..config import MONGO_COLLECTION_GOLD_COURSE, MONGO_COLLECTION_SISU_AGGREGATED
from ..utils.logger import logger


class FaseMongoDBLoad:
    """Carrega dados transformados para MongoDB"""
    
    def __init__(self):
        self.mongo_client = MongoDBClient()
    
    def load_gold_course_indicators(self, final_documents):
        """
        Faz upsert de documentos analíticos na coleção gold_course_indicators.
        
        Args:
            final_documents: Lista de documentos finais para carregar
            
        Returns:
            dict: Estatísticas da operação
        """
        logger.info(f"Carregando {len(final_documents)} documentos em {MONGO_COLLECTION_GOLD_COURSE}...")
        
        stats = self.mongo_client.upsert_documents(
            MONGO_COLLECTION_GOLD_COURSE,
            final_documents,
            id_field="_id"
        )
        
        logger.info(f"Upsert concluído: {stats['matched']} matched, "
                   f"{stats['modified']} modified, {stats['upserted']} upserted")
        
        return stats
    
    def load_sisu_aggregated(self, sisu_final_docs):
        """
        Faz upsert de agregações SISU em coleção separada (opcional).
        
        Args:
            sisu_final_docs: Lista de documentos SISU agregados
            
        Returns:
            dict: Estatísticas da operação
        """
        if not sisu_final_docs:
            logger.info("Nenhum documento SISU para carregar")
            return {"matched": 0, "modified": 0, "upserted": 0}
        
        logger.info(f"Carregando {len(sisu_final_docs)} documentos em {MONGO_COLLECTION_SISU_AGGREGATED}...")
        
        stats = self.mongo_client.upsert_documents(
            MONGO_COLLECTION_SISU_AGGREGATED,
            sisu_final_docs,
            id_field="_id"
        )
        
        logger.info(f"Upsert SISU concluído: {stats['matched']} matched, "
                   f"{stats['modified']} modified, {stats['upserted']} upserted")
        
        return stats
    
    def run(self, final_documents, sisu_final_docs=None):
        """
        Executa carregamento de dados em MongoDB.
        
        Args:
            final_documents: Documentos analíticos finais
            sisu_final_docs: Documentos SISU (opcional)
            
        Returns:
            dict: Estatísticas consolidadas
        """
        try:
            logger.info("=" * 80)
            logger.info("PHASE 7: MONGODB LOAD")
            logger.info("=" * 80)
            
            # Carregar documentos de cursos
            stats_gold = self.load_gold_course_indicators(final_documents)
            
            # Carregar documentos SISU (opcional)
            stats_sisu = self.load_sisu_aggregated(sisu_final_docs or [])
            
            logger.info("")
            logger.info("PHASE 7 - MONGODB LOAD SUMMARY")
            logger.info("-" * 80)
            logger.info(f"Gold Course Indicators: {stats_gold['matched']} matched, "
                       f"{stats_gold['modified']} modified, {stats_gold['upserted']} upserted")
            logger.info(f"SISU Aggregated: {stats_sisu['matched']} matched, "
                       f"{stats_sisu['modified']} modified, {stats_sisu['upserted']} upserted")
            logger.info("-" * 80)
            
            return {
                "gold_course_indicators": stats_gold,
                "sisu_aggregated": stats_sisu,
            }
        except Exception as e:
            logger.error(f"Erro na Phase 7 - MongoDB Load: {e}", exc_info=True)
            raise
        finally:
            self.mongo_client.close()
