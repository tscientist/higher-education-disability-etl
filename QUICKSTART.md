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

### Credenciais e permissões necessárias no BigQuery

A aplicação pode autenticar no Google Cloud de duas formas:

1. usando um arquivo de chave de uma service account, configurado em `GCP_CREDENTIALS_PATH`;
2. usando autenticação local com `gcloud auth application-default login`.

Independentemente da forma de autenticação, a conta utilizada precisa ter permissões suficientes para executar jobs no BigQuery, criar datasets/tabelas, inserir dados e consultar dados.

Para este projeto, a configuração recomendada é conceder à conta os seguintes papéis IAM no projeto `higher-education-disability`:

| Papel IAM            | Identificador               | Uso no projeto                                                                                                   |
| -------------------- | --------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| BigQuery Job User    | `roles/bigquery.jobUser`    | Permite executar jobs de consulta e carga no BigQuery                                                            |
| BigQuery Data Editor | `roles/bigquery.dataEditor` | Permite criar datasets, criar tabelas, inserir dados, substituir tabelas e consultar dados no dataset do projeto |
| BigQuery Data Viewer | `roles/bigquery.dataViewer` | Permite ler tabelas existentes, quando o acesso for apenas de leitura                                            |

Para executar todo o fluxo do projeto, incluindo criação de tabelas de staging, leitura de dados públicos, inserção de dados e consultas, a conta deve ter pelo menos:

```text
roles/bigquery.jobUser
roles/bigquery.dataEditor
```

Esses papéis são necessários porque o pipeline executa operações como:

```sql
CREATE OR REPLACE TABLE destino AS
SELECT ...
FROM origem;
```

Além disso, o pipeline também executa consultas `SELECT`, valida contagens de registros e lê tabelas de staging durante o ETL.

Caso a conta seja usada apenas para consultar dados já existentes, sem criar ou substituir tabelas, o papel `roles/bigquery.dataViewer` pode ser suficiente para leitura, junto com `roles/bigquery.jobUser` para executar as consultas.

Segundo a documentação oficial do BigQuery, o papel **BigQuery Job User** permite executar jobs de consulta e carga, enquanto o papel **BigQuery Data Editor** permite criar datasets, criar tabelas, carregar dados e consultar tabelas.

#### Exemplo usando service account

No `.env`, informe o caminho do arquivo JSON da chave:

```env
GCP_CREDENTIALS_PATH=src/credentials.json
```

O arquivo precisa existir no caminho informado:

```bash
ls -la src/credentials.json
```

#### Exemplo usando autenticação local

Se não for usar arquivo de chave, deixe a variável vazia:

```env
GCP_CREDENTIALS_PATH=
```

E execute:

```bash
gcloud auth application-default login
gcloud config set project higher-education-disability
```

Nesse caso, as permissões necessárias devem estar associadas ao usuário autenticado no Google Cloud.

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

Após o setup finalizar com sucesso, execute o pipeline completo na seguinte ordem:

### Opção A: Pipeline 2022 (recomendado)

```bash
# Passo 1 — Criar tabelas intermediárias no BigQuery (só precisa rodar 1 vez)
python3 main.py --mode setup-bigquery

# Passo 2 — ETL: lê BigQuery em páginas e escreve em gold_course_indicators (~573k docs)
python3 main.py --mode etl-2022

# Passo 3 — Popula sisu_aggregated (coleção referenciada para demonstrar $lookup)
python3 main.py --mode load-sisu

# Passo 4 — Cria os 12 índices no MongoDB
python3 main.py --mode create-indexes
```

Executa todas as fases em sequência e valida os resultados.

### Opção B: Pipeline legado (com queries avançadas)

```bash
python3 main.py --mode with-queries
```

---

## Reprocessar do zero

Para limpar o banco e reprocessar tudo:

```bash
# 1. Limpar o MongoDB
# 2. Rodar o pipeline com --force (ignora checkpoint)
python3 main.py --mode etl-2022 --force && \
python3 main.py --mode load-sisu --force && \
python3 main.py --mode create-indexes
```
----

## Comparação de performance dos índices

```bash
python3 main.py --mode explain-performance --force
```

Demonstra o impacto dos índices: COLLSCAN -> IXSCAN (50-90x mais rápido).

---

## Troubleshooting

- **BigQuery — credenciais:** Verifique `GCP_CREDENTIALS_PATH` no `.env`
- **MongoDB — connection refused:** Verifique `MONGODB_URI` no `.env`
- **Memória insuficiente:** Reduza `ETL_PAGE_SIZE` no `.env` (padrão: 5000)

Para documentação completa, consulte `docs/mongodb_queries.md` e `docs/mongodb_indexes_and_performance.md`.
