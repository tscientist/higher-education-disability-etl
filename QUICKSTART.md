# Quick Start

## Pré-requisitos

- Python 3.11+
- MongoDB 7.0+ (local, Docker ou Atlas)
- Acesso ao BigQuery no projeto `higher-education-disability-etl`

---

## 1. Ambiente Python

> **Nota:** dependendo da instalação, use `python` ou `python3`. 

```zsh
cd higher-education-disability-etl
python3 -m venv .venv   # use python se python3 não estiver disponível
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 2. Variáveis de ambiente

Crie o arquivo `.env` na raiz do projeto:

```env
# Google Cloud
GCP_PROJECT_ID=higher-education-disability
GCP_CREDENTIALS_PATH=src/credentials.json   

# MongoDB
MONGO_URI=mongodb+srv://usuario:senha@cluster.mongodb.net/
MONGO_DATABASE=higher_education
```

**Autenticação BigQuery — opção A (service account):**

```zsh
# Coloque o arquivo JSON da chave em src/credentials.json
ls src/credentials.json
```

**Autenticação BigQuery — opção B (gcloud local):**

```zsh
gcloud auth application-default login
gcloud config set project higher-education-disability
# Deixe GCP_CREDENTIALS_PATH vazio no .env
```

---

## 3. MongoDB via Docker (opcional)

Se não tiver MongoDB instalado:

```zsh
docker compose up -d
```

URI local para o `.env`:

```env
MONGO_URI=mongodb://admin:password@localhost:27017/?authSource=admin
```

---

## 4. Carregar os dados

**Etapa 1 — Coleções brutas do BigQuery:**

```zsh
python src/mongo/load_dados.py --table all --drop-existing
```

Cria as coleções `cursos`, `ies` e `sisu` no MongoDB com dados de 2022.

> **Atenção:** a tabela `sisu` tem ~3,5 milhões de registros e pode levar 30–60 minutos dependendo da conexão. Para uma primeira execução ou teste, use `--limit` para carregar apenas uma fração:

```zsh
# Teste rápido (recomendado antes da carga completa)
python src/mongo/load_dados.py --table all --drop-existing --limit 100000

# Carregar só o SISU com limite (cursos e ies são menores e carregam rápido)
python src/mongo/load_dados.py --table cursos --drop-existing
python src/mongo/load_dados.py --table ies    --drop-existing
python src/mongo/load_dados.py --table sisu   --drop-existing --limit 500000
```

**Etapa 2 — Coleção analítica:**

```zsh
python src/mongo/build_gold_cursos_sisu.py --drop-existing
```

Cria a coleção `gold_cursos_sisu` com embedding de IES + SISU + métricas calculadas.

---

## 5. Executar as consultas

```zsh
# Todas as 8 consultas
python src/mongo/consultas.py

# Uma consulta específica
python src/mongo/consultas.py --query 3

# Demonstração de COLLSCAN vs IXSCAN
python src/mongo/consultas.py --query 7
```

---

## 6. Dashboard e API

```zsh
cd dashboard
pip install -r requirements.txt

# Terminal 1 — API REST
python -m uvicorn api:app --host 127.0.0.1 --port 8000

# Terminal 2 — Dashboard Streamlit
python -m streamlit run app.py --server.port 8501
```

| URL | O que é |
|-----|---------|
| http://127.0.0.1:8000/health | Healthcheck da API |
| http://127.0.0.1:8000/docs | Swagger — testar endpoints |
| http://127.0.0.1:8501 | Dashboard Streamlit |

---

## Coleções esperadas no MongoDB

| Coleção | Origem | Volume (2022) |
|---------|--------|--------------|
| `cursos` | Censo — tabela curso | ~573 mil docs |
| `ies` | Censo — tabela IES | ~2,5 mil docs |
| `sisu` | SISU microdados | ~3,5 milhões docs |
| `gold_cursos_sisu` | Construída pelo ETL | ~573 mil docs |

---

## Problemas comuns

| Erro | Solução |
|------|---------|
| `CERTIFICATE_VERIFY_FAILED` | `pip install certifi` e rode `source .venv/bin/activate` |
| `MONGO_URI não configurado` | Verifique o `.env` na raiz do projeto |
| `GCP_PROJECT_ID não configurado` | Verifique o `.env` ou execute `gcloud config set project ...` |
| Dashboard: "Nenhum dado encontrado" | Execute as etapas 4.1 e 4.2 antes de abrir o dashboard |
| `E11000 duplicate key` em cursos | Normal — o Censo tem duplicatas em `id_municipio=0`; o índice não é único |
