from google.cloud import bigquery
from google.oauth2 import service_account
from ..config import GCP_PROJECT_ID, GCP_CREDENTIALS_PATH


class BigQueryClient:
    def __init__(self):
        self.client = bigquery.Client(
            project=GCP_PROJECT_ID,
            credentials=self._load_credentials()
        )
    
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
