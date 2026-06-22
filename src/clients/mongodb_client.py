from pymongo import MongoClient
from ..config import MONGO_URI, MONGO_DATABASE, MONGO_COLLECTION


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
    
    def close(self):
        """Fecha a conexão com o MongoDB"""
        self.client.close()
