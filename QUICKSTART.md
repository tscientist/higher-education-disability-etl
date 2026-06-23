# Quick Start Guide

## Instalação

### Pré-requisitos

* Python 3.11+
* Google Cloud SDK instalado e configurado
* Acesso ao projeto Google Cloud `higher-education-disability`
* MongoDB 7.0+ rodando localmente, via Docker ou em ambiente cloud
* Ambiente virtual Python recomendado

### Configuração

1. **Acessar a pasta do projeto:**

```bash
cd /path/to/higher-education-disability-etl
```

2. **Criar e ativar o ambiente virtual:**

```bash
python -m venv venv
source venv/bin/activate
```

3. **Instalar as dependências:**

```bash
pip install -r requirements.txt
```

Para instalação em modo de desenvolvimento, use:

```bash
pip install -e ".[dev]"
```

4. **Configurar as variáveis de ambiente:**

Crie ou atualize o arquivo `.env` na raiz do projeto:

```env
# Google Cloud
GCP_PROJECT_ID=higher-education-disability
GCP_CREDENTIALS_PATH=

# MongoDB
# Use aspas simples na MONGO_URI quando a connection string tiver caracteres especiais, como & em retryWrites=true&w=majority. Sem aspas, o terminal pode interpretar o & como comando em background ao executar source .env.
MONGO_URI=mongodb://admin:password@localhost:27017/higher_education?authSource=admin
MONGO_DATABASE=higher_education
MONGO_COLLECTION=students

# BigQuery
BIGQUERY_DATASET=ppgti_etl_test
BIGQUERY_TABLE=etl_test_table

# Storage
GCS_BUCKET_NAME=
GCS_PATH=

# ETL Configuration
ETL_START_YEAR=2022
ETL_END_YEAR=2022
```

A variável `GCP_CREDENTIALS_PATH` pode ser usada de duas formas.

Se for usar um arquivo de chave/service account do Google Cloud, preencha com o caminho do arquivo JSON:

```env
GCP_CREDENTIALS_PATH=src/credentials.json
```

Nesse caso, confirme se o arquivo existe no caminho informado:

```bash
ls -la src/credentials.json
```

Se for usar autenticação local do Google Cloud, deixe a variável vazia:

```env
GCP_CREDENTIALS_PATH=
```

Nesse caso, execute:

```bash
gcloud auth application-default login
gcloud config set project higher-education-disability
```

5. **Exportar as variáveis de ambiente:**

Depois de atualizar o arquivo `.env`, exporte as variáveis para que os scripts e a aplicação consigam reconhecê-las:

```bash
set -a
source .env
set +a
```

Para conferir se as variáveis foram carregadas corretamente:

```bash
echo $GCP_PROJECT_ID
echo $BIGQUERY_DATASET
echo $MONGO_URI
echo $ETL_START_YEAR
echo $ETL_END_YEAR
```

6. **Executar o script de setup geral:**

Depois de configurar e exportar as variáveis de ambiente, execute:

```bash
python src/setup/run_all_setup.py
```

Esse script executa as verificações e preparações necessárias para o projeto, incluindo validação de conexão com BigQuery, MongoDB e demais recursos usados pelo pipeline ETL.

7. **Executar o pipeline ETL:**

Após o setup finalizar com sucesso, execute:

```bash
python main.py --mode with-queries
```
