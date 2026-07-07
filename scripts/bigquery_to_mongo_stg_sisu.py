#!/usr/bin/env python3
"""
Extrai todos os dados de stg_sisu_microdados (ano=2022) do BigQuery
e carrega na coleção MongoDB 'stg_sisu_microdados'.

Uso:
    python scripts/bigquery_to_mongo_stg_sisu.py
"""

import sys
import os

# Adiciona o diretório raiz ao path para importar src.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.clients import BigQueryClient, MongoDBClient
from src.utils import get_logger

logger = get_logger(__name__)

# ──────────────────────────────────────────────────────────────────
# Configurações
# ──────────────────────────────────────────────────────────────────
BQ_PROJECT    = "higher-education-disability"
BQ_DATASET    = "ppgti_etl_test"
BQ_TABLE      = "stg_sisu_microdados"
ANO_FILTRO    = 2022

MONGO_COLLECTION_NAME = "stg_sisu_microdados"

# Quantos documentos inserir por lote no MongoDB
BATCH_SIZE = 5_000


def extrair_bigquery(bq_client: BigQueryClient) -> list[dict]:
    """Executa a query no BigQuery e retorna lista de dicts."""
    query = f"""
        SELECT *
        FROM `{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}`
        WHERE ano = {ANO_FILTRO}
    """
    logger.info(f"Executando query no BigQuery: {query.strip()}")
    rows = bq_client.fetch_data(query)
    logger.info(f"BigQuery retornou {len(rows):,} registros")
    return rows


def carregar_mongodb(mongo_client: MongoDBClient, documentos: list[dict]) -> None:
    """
    Apaga os dados existentes do ano na coleção e insere os novos documentos
    em lotes para evitar esgotamento de memória.
    """
    collection = mongo_client.db[MONGO_COLLECTION_NAME]

    # Remove registros anteriores do mesmo ano para garantir idempotência
    deleted = collection.delete_many({"ano": ANO_FILTRO})
    logger.info(
        f"Removidos {deleted.deleted_count:,} documentos anteriores "
        f"(ano={ANO_FILTRO}) da coleção '{MONGO_COLLECTION_NAME}'"
    )

    total_inseridos = 0
    for inicio in range(0, len(documentos), BATCH_SIZE):
        lote = documentos[inicio : inicio + BATCH_SIZE]
        collection.insert_many(lote, ordered=False)
        total_inseridos += len(lote)
        logger.info(
            f"  → Inseridos {total_inseridos:,} / {len(documentos):,} documentos..."
        )

    logger.info(
        f"✅ Carga finalizada: {total_inseridos:,} documentos inseridos "
        f"na coleção '{MONGO_COLLECTION_NAME}'"
    )


def criar_indices(mongo_client: MongoDBClient) -> None:
    """Cria índices básicos para acelerar consultas na coleção."""
    collection = mongo_client.db[MONGO_COLLECTION_NAME]

    indices = [
        ([("ano", 1)],                   {"name": "idx_ano"}),
        ([("ano", 1), ("uf", 1)],        {"name": "idx_ano_uf"}),
        ([("ano", 1), ("id_ies", 1)],    {"name": "idx_ano_id_ies"}),
        ([("ano", 1), ("id_curso", 1)],  {"name": "idx_ano_id_curso"}),
    ]

    for keys, options in indices:
        try:
            nome = collection.create_index(keys, **options)
            logger.info(f"Índice '{nome}' criado/confirmado em '{MONGO_COLLECTION_NAME}'")
        except Exception as e:
            logger.warning(f"Índice '{options.get('name')}' não pôde ser criado: {e}")


def main() -> None:
    logger.info("=" * 60)
    logger.info("Iniciando carga: BigQuery → MongoDB (stg_sisu_microdados)")
    logger.info("=" * 60)

    # ── Clientes ──────────────────────────────────────────────────
    logger.info("Conectando ao BigQuery...")
    bq_client = BigQueryClient()

    logger.info("Conectando ao MongoDB...")
    mongo_client = MongoDBClient()

    try:
        # ── 1. Extração ───────────────────────────────────────────
        documentos = extrair_bigquery(bq_client)

        if not documentos:
            logger.warning("Nenhum registro retornado pelo BigQuery. Encerrando.")
            return

        # ── 2. Carga ──────────────────────────────────────────────
        carregar_mongodb(mongo_client, documentos)

        # ── 3. Índices ────────────────────────────────────────────
        criar_indices(mongo_client)

        logger.info("=" * 60)
        logger.info("Pipeline concluído com sucesso ✅")
        logger.info("=" * 60)

    finally:
        mongo_client.close()


if __name__ == "__main__":
    main()
