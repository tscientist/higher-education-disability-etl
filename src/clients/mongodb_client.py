from pymongo import MongoClient
from pymongo.errors import PyMongoError
from ..config import MONGO_URI, MONGO_DATABASE, MONGO_COLLECTION
from ..utils.logger import logger


class MongoDBClient:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[MONGO_DATABASE]
        self.collection = self.db[MONGO_COLLECTION]
    
    def insert_documents(self, documents):
        """Insere documentos na coleção"""
        if documents:
            result = self.collection.insert_many(documents)
            return result.inserted_ids
        return []
    
    def upsert_documents(self, collection_name, documents, id_field="_id"):
        """
        Realiza upsert de documentos usando replace_one.
        
        Args:
            collection_name: Nome da coleção
            documents: Lista de documentos para upsert
            id_field: Campo a usar como _id (padrão: "_id")
            
        Returns:
            dict: Dicionário com estatísticas (matched, modified, upserted)
        """
        collection = self.db[collection_name]
        stats = {"matched": 0, "modified": 0, "upserted": 0}
        
        for doc in documents:
            try:
                filter_query = {id_field: doc.get(id_field)}
                result = collection.replace_one(filter_query, doc, upsert=True)
                stats["matched"] += result.matched_count
                stats["modified"] += result.modified_count
                stats["upserted"] += result.upserted_id is not None
            except PyMongoError as e:
                logger.error(f"Erro ao fazer upsert do documento: {e}")
                
        return stats
    
    def create_index(self, collection_name, index_spec, **kwargs):
        """
        Cria um índice na coleção.
        
        Args:
            collection_name: Nome da coleção
            index_spec: Especificação do índice (lista de tuplas)
            **kwargs: Argumentos adicionais para create_index
        """
        collection = self.db[collection_name]
        try:
            index_name = collection.create_index(index_spec, **kwargs)
            logger.info(f"Índice '{index_name}' criado em {collection_name}")
            return index_name
        except PyMongoError as e:
            logger.error(f"Erro ao criar índice em {collection_name}: {e}")
    
    def get_collection(self, collection_name):
        """Obtém uma coleção específica"""
        return self.db[collection_name]
    
    def close(self):
        """Fecha a conexão com o MongoDB"""
        self.client.close()
