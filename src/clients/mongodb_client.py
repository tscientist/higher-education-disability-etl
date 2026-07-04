from pymongo import MongoClient
from pymongo.errors import PyMongoError
from ..config import MONGO_URI, MONGO_DATABASE, MONGO_COLLECTION
from ..utils.logger import logger


class MongoDBClient:
    def __init__(self):
        # Conectar ao MongoDB com opções SSL/TLS
        # Para MongoDB Atlas, desabilitar verificação de certificado se necessário
        try:
            # Primeiro tenta com verificação de certificado
            self.client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=60000,
                connectTimeoutMS=60000,
                socketTimeoutMS=300000,   # 5 min — bulk writes de docs grandes
                maxPoolSize=10,
                retryWrites=True,
            )
            # Test connection
            self.client.admin.command('ping')
            logger.info("Conexao com MongoDB estabelecida com verificacao SSL")
        except Exception as e:
            logger.warning(f"Erro com SSL: {e}")
            logger.warning("Tentando sem verificacao de certificado SSL...")
            try:
                # Se falhar, tenta sem verificação de certificado
                self.client = MongoClient(
                    MONGO_URI,
                    tlsInsecure=True,
                    serverSelectionTimeoutMS=60000,
                    connectTimeoutMS=60000,
                    socketTimeoutMS=300000,   # 5 min — bulk writes de docs grandes
                    maxPoolSize=10,
                    retryWrites=True,
                )
                # Test connection
                self.client.admin.command('ping')
                logger.info("Conexao com MongoDB estabelecida (SSL insecure)")
            except Exception as e2:
                logger.error(f"Falha ao conectar no MongoDB: {e2}")
                raise
        
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
    
    def ensure_collection_exists(self, collection_name):
        """
        Garante que a coleção existe no banco de dados.
        Se a coleção não existir, cria uma com um documento vazio e o remove.
        
        Args:
            collection_name: Nome da coleção
            
        Returns:
            bool: True se a coleção foi criada ou já existe
        """
        try:
            # Verificar se a coleção já existe
            existing_collections = self.db.list_collection_names()
            
            if collection_name in existing_collections:
                logger.info(f"Colecao '{collection_name}' ja existe")
                return True
            
            # Se nao existe, criar inserindo um documento dummy e removendo
            logger.info(f"Criando colecao '{collection_name}'...")
            collection = self.db[collection_name]
            
            # Inserir um documento dummy para criar a coleção
            dummy_doc = {"_setup": True, "created": True}
            result = collection.insert_one(dummy_doc)
            
            # Remover o documento dummy
            collection.delete_one({"_id": result.inserted_id})
            
            logger.info(f"Colecao '{collection_name}' criada com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao criar colecao '{collection_name}': {e}")
            return False
    
    def ensure_database_exists(self):
        """
        Garante que o banco de dados existe.
        MongoDB cria automaticamente ao inserir dados, mas podemos verificar.
        
        Returns:
            bool: True se o banco foi criado ou já existe
        """
        try:
            existing_databases = self.client.list_database_names()
            
            if MONGO_DATABASE in existing_databases:
                logger.info(f"Banco de dados '{MONGO_DATABASE}' ja existe")
                return True
            
            logger.info(f"Banco de dados '{MONGO_DATABASE}' sera criado na primeira insercao")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao verificar banco de dados: {e}")
            return False
    
    def close(self):
        """Fecha a conexão com o MongoDB"""
        self.client.close()
