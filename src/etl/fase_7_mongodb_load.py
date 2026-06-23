"""
Fase 7: MongoDB Load

Carrega documentos transformados para MongoDB com upsert.
Cria as coleções analíticas necessárias.
"""

from pymongo import UpdateOne
from ..clients import MongoDBClient
from ..config import MONGO_COLLECTION_GOLD_COURSE, MONGO_COLLECTION_SISU_AGGREGATED
from ..utils.logger import logger


class Fase7MongoDBLoad:
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
    
    def load_batch(self, batch_documents, batch_number):
        """
        Carrega um batch de documentos em MongoDB usando bulk operations.
        
        Args:
            batch_documents: Lista de documentos do batch para inserir
            batch_number: Número do batch (para logging)
            
        Returns:
            dict: Estatísticas da inserção
        """
        try:
            if not batch_documents:
                logger.warning(f"Batch #{batch_number} vazio, pulando...")
                return {
                    "batch_number": batch_number,
                    "inserted_count": 0,
                    "status": "skipped"
                }
            
            # Verificar e criar banco de dados e coleção se necessário (apenas no primeiro batch)
            if batch_number == 1:
                logger.info("Verificando estrutura do MongoDB...")
                self.mongo_client.ensure_database_exists()
                self.mongo_client.ensure_collection_exists(MONGO_COLLECTION_GOLD_COURSE)
                logger.info("Estrutura do MongoDB pronta")
            
            logger.info(f"Fase 7 - Carregando batch #{batch_number} ({len(batch_documents)} documentos)...")
            
            # Get collection from MongoDB client
            collection = self.mongo_client.get_collection(MONGO_COLLECTION_GOLD_COURSE)
            
            # Usar bulk operations para performance
            operations = []
            
            for doc in batch_documents:
                # Usar _id como filtro único (garantido ser único)
                filter_query = {"_id": doc.get("_id")}
                
                # Remover _id do documento para evitar erro ao atualizar campo imutável
                doc_to_update = {k: v for k, v in doc.items() if k != "_id"}
                
                # Adicionar operação de upsert à lista
                operations.append(
                    UpdateOne(filter_query, {"$set": doc_to_update}, upsert=True)
                )
            
            # Executar todas as operações de uma vez
            if operations:
                result = collection.bulk_write(operations)
                
                inserted_count = result.upserted_ids.__len__() if result.upserted_ids else 0
                upserted_count = result.matched_count
                
                logger.info(f"Batch #{batch_number}: {upserted_count} matched, {inserted_count} upserted")
                
                return {
                    "batch_number": batch_number,
                    "inserted_count": inserted_count,
                    "matched_count": upserted_count,
                    "total_documents": len(batch_documents),
                    "status": "success"
                }
            else:
                return {
                    "batch_number": batch_number,
                    "inserted_count": 0,
                    "status": "skipped"
                }
                
        except Exception as e:
            logger.error(f"Erro ao carregar batch #{batch_number}: {e}", exc_info=True)
            raise
    
    def load_sisu_batch(self, sisu_documents, batch_number):
        """
        Carrega um batch de documentos SISU agregados em MongoDB usando bulk operations.
        
        Args:
            sisu_documents: Lista de documentos SISU agregados do batch
            batch_number: Número do batch (para logging)
            
        Returns:
            dict: Estatísticas da inserção
        """
        try:
            if not sisu_documents:
                logger.info(f"Batch #{batch_number} SISU vazio, pulando...")
                return {
                    "batch_number": batch_number,
                    "inserted_count": 0,
                    "status": "skipped"
                }
            
            # Verificar e criar coleção SISU se necessário (apenas no primeiro batch)
            if batch_number == 1:
                self.mongo_client.ensure_collection_exists(MONGO_COLLECTION_SISU_AGGREGATED)
            
            logger.info(f"Carregando batch #{batch_number} SISU ({len(sisu_documents)} documentos)...")
            
            # Get collection from MongoDB client
            collection = self.mongo_client.get_collection(MONGO_COLLECTION_SISU_AGGREGATED)
            
            # Usar bulk operations para performance
            operations = []
            
            for doc in sisu_documents:
                # Usar _id como filtro único (garantido ser único: ano_id_ies_id_curso)
                filter_query = {"_id": doc.get("_id")}
                
                # Remover _id do documento para evitar erro ao atualizar campo imutável
                doc_to_update = {k: v for k, v in doc.items() if k != "_id"}
                
                # Adicionar operação de upsert à lista
                operations.append(
                    UpdateOne(filter_query, {"$set": doc_to_update}, upsert=True)
                )
            
            # Executar todas as operações de uma vez
            if operations:
                result = collection.bulk_write(operations)
                
                inserted_count = result.upserted_ids.__len__() if result.upserted_ids else 0
                matched_count = result.matched_count
                
                logger.info(f"Batch #{batch_number} SISU: {matched_count} matched, {inserted_count} upserted")
                
                return {
                    "batch_number": batch_number,
                    "inserted_count": inserted_count,
                    "matched_count": matched_count,
                    "total_documents": len(sisu_documents),
                    "status": "success"
                }
            else:
                return {
                    "batch_number": batch_number,
                    "inserted_count": 0,
                    "status": "skipped"
                }
                
        except Exception as e:
            logger.error(f"Erro ao carregar batch SISU #{batch_number}: {e}", exc_info=True)
            raise
