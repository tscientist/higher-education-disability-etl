from google.cloud import bigquery
from google.oauth2 import service_account
from ..config import GCP_PROJECT_ID, GCP_CREDENTIALS_PATH
from ..utils.logger import logger


class BigQueryClient:
    def __init__(self):
        self.client = bigquery.Client(
            project=GCP_PROJECT_ID,
            credentials=self._load_credentials()
        )
        self.project_id = GCP_PROJECT_ID
    
    def _load_credentials(self):
        """Carrega as credenciais da service account"""
        return service_account.Credentials.from_service_account_file(
            GCP_CREDENTIALS_PATH
        )
    
    def fetch_data(self, query):
        """Executa uma query no BigQuery e retorna os resultados"""
        query_job = self.client.query(query)
        results = query_job.result()
        return [dict(row) for row in results]
    
    def read_table(self, dataset_id, table_id, year_range=None, limit=None):
        """
        Lê uma tabela BigQuery com filtros opcionais de ano e limite.
        
        Args:
            dataset_id: ID do dataset
            table_id: ID da tabela
            year_range: Tuple (start_year, end_year) para filtrar por ano
            limit: Limite de registros para testes
            
        Returns:
            List[dict]: Lista de documentos
        """
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        
        query = f"SELECT * FROM `{table_ref}`"
        
        if year_range:
            start_year, end_year = year_range
            query += f" WHERE ano >= {start_year} AND ano <= {end_year}"
        
        if limit:
            query += f" LIMIT {limit}"
        
        logger.info(f"Lendo tabela {table_id} com query: {query}")
        results = self.fetch_data(query)
        logger.info(f"Tabela {table_id}: {len(results)} registros lidos")
        
        return results
