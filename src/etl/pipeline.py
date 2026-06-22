from ..clients import BigQueryClient, MongoDBClient
from ..config import BIGQUERY_DATASET, BIGQUERY_TABLE
from ..utils.logger import logger


class ETLPipeline:
    def __init__(self):
        self.bq_client = BigQueryClient()
        self.mongo_client = MongoDBClient()
    
    def extract(self):
        """Extrai dados do BigQuery"""
        query = f"SELECT * FROM `{BIGQUERY_DATASET}.{BIGQUERY_TABLE}`"
        logger.info(f"Executando query: {query}")
        data = self.bq_client.fetch_data(query)
        logger.info(f"Dados extraídos: {len(data)} registros")
        return data
    
    def transform(self, data):
        """Transforma os dados (aqui você pode adicionar lógica de transformação)"""
        logger.info("Transformando dados...")
        return data
    
    def load(self, data):
        """Carrega os dados no MongoDB"""
        inserted_ids = self.mongo_client.insert_documents(data)
        logger.info(f"Dados carregados: {len(inserted_ids)} documentos inseridos")
        return inserted_ids
    
    def run(self):
        """Executa o pipeline completo"""
        try:
            data = self.extract()
            transformed_data = self.transform(data)
            self.load(transformed_data)
            logger.info("ETL concluído com sucesso!")
        except Exception as e:
            logger.error(f"Erro durante o ETL: {e}", exc_info=True)
        finally:
            self.mongo_client.close()
