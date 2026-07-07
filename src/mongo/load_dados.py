import argparse
import datetime as dt
import decimal
import os
from typing import Any, Dict, Iterable, List, Optional

import certifi
from dotenv import load_dotenv
from google.cloud import bigquery
from google.oauth2 import service_account
from pymongo import MongoClient


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

QUERY_CURSOS = """
SELECT *
FROM `basedosdados.br_inep_censo_educacao_superior.curso`
WHERE ano = 2022
"""

QUERY_CURSOS_STATS = """
SELECT
  COUNT(*) AS total_linhas,
  COUNT(DISTINCT id_curso) AS total_id_curso_distintos,
  COUNT(DISTINCT CONCAT(
    CAST(ano AS STRING), '_',
    CAST(id_ies AS STRING), '_',
    CAST(id_curso AS STRING), '_',
    CAST(id_municipio AS STRING)
  )) AS total_chaves_distintas
FROM `basedosdados.br_inep_censo_educacao_superior.curso`
WHERE ano = 2022
"""

QUERY_IES = """
SELECT *
FROM `basedosdados.br_inep_censo_educacao_superior.ies`
WHERE ano = 2022
"""

QUERY_SISU = """
SELECT *
FROM `basedosdados.br_mec_sisu.microdados`
WHERE ano = 2022
"""

# ---------------------------------------------------------------------------
# Configuracao das tabelas
# ---------------------------------------------------------------------------

TABLE_CONFIGS: Dict[str, Dict] = {
    "cursos": {
        "query": QUERY_CURSOS,
        "collection": "cursos",
        "indexes": [
            ([("ano", 1)], {}),
            ([("id_ies", 1)], {}),
            ([("id_curso", 1)], {}),
            ([("id_municipio", 1)], {}),
            (
                # Não é unique: o BigQuery tem duplicatas reais para
                # id_municipio="0" (cursos sem campus/município definido).
                [("ano", 1), ("id_ies", 1), ("id_curso", 1), ("id_municipio", 1)],
                {},
            ),
        ],
    },
    "ies": {
        "query": QUERY_IES,
        "collection": "ies",
        "indexes": [
            ([("ano", 1)], {}),
            ([("id_ies", 1)], {}),
            ([("sigla_uf", 1)], {}),
            ([("ano", 1), ("id_ies", 1)], {"unique": True}),
        ],
    },
    "sisu": {
        "query": QUERY_SISU,
        "collection": "sisu",
        "indexes": [
            ([("ano", 1)], {}),
            ([("id_ies", 1)], {}),
            ([("id_curso", 1)], {}),
            ([("ano", 1), ("id_ies", 1), ("id_curso", 1)], {}),
        ],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    """Print com timestamp."""
    timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")


def get_bigquery_client() -> bigquery.Client:
    project_id = os.getenv("GCP_PROJECT_ID", "").strip()
    credentials_path = os.getenv("GCP_CREDENTIALS_PATH", "").strip()

    if not project_id:
        raise ValueError("GCP_PROJECT_ID nao esta configurado no .env")

    if credentials_path:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        return bigquery.Client(project=project_id, credentials=credentials)

    return bigquery.Client(project=project_id)


def get_mongodb_client() -> MongoClient:
    mongo_uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")

    if not mongo_uri:
        raise ValueError("MONGO_URI ou MONGODB_URI precisa estar configurado no .env")

    return MongoClient(
        mongo_uri,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=60000,
        connectTimeoutMS=60000,
        socketTimeoutMS=300000,
        maxPoolSize=10,
        retryWrites=True,
    )


def to_bson_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: to_bson_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_bson_value(item) for item in value]
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.date):
        return dt.datetime.combine(value, dt.time.min)
    if isinstance(value, dt.time):
        return value.isoformat()
    return value


def row_to_document(row: bigquery.table.Row) -> Dict[str, Any]:
    document = {key: to_bson_value(value) for key, value in dict(row).items()}

    ano = document.get("ano")
    id_ies = document.get("id_ies")
    id_curso = document.get("id_curso")
    id_municipio = document.get("id_municipio")

    if ano is not None and id_ies is not None and id_curso is not None and id_municipio is not None:
        document["id"] = f"{ano}{id_ies}{id_curso}{id_municipio}"

    return document


def insert_batch(collection, documents: List[Dict[str, Any]], ordered: bool) -> int:
    if not documents:
        return 0
    result = collection.insert_many(documents, ordered=ordered)
    return len(result.inserted_ids)


def iter_batches(rows: Iterable[bigquery.table.Row], batch_size: int):
    batch = []
    for row in rows:
        batch.append(row_to_document(row))
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def print_cursos_stats(client: bigquery.Client) -> None:
    log("Consultando estatisticas da fonte (cursos)...")
    stats = list(client.query(QUERY_CURSOS_STATS).result())[0]
    log(f"  Linhas totais:              {stats['total_linhas']:,}")
    log(f"  id_curso distintos:         {stats['total_id_curso_distintos']:,}")
    log(f"  Chaves compostas distintas: {stats['total_chaves_distintas']:,}")


# ---------------------------------------------------------------------------
# Loader generico
# ---------------------------------------------------------------------------

def load_table(
    table_key: str,
    batch_size: int,
    database_name: str,
    drop_existing: bool,
    limit: Optional[int],
) -> int:
    config = TABLE_CONFIGS[table_key]
    collection_name = config["collection"]
    query = config["query"].strip()

    if limit is not None:
        query = f"{query}\nLIMIT {int(limit)}"

    bq_client = get_bigquery_client()
    mongo_client = get_mongodb_client()

    try:
        db = mongo_client[database_name]
        collection = db[collection_name]

        if drop_existing:
            log(f"Removendo collection existente: {database_name}.{collection_name}")
            collection.drop()

        if table_key == "cursos":
            print_cursos_stats(bq_client)

        preview = query[:120] + ("..." if len(query) > 120 else "")
        log(f"Executando query BigQuery ({table_key}): {preview}")

        inicio_query = dt.datetime.now()
        query_job = bq_client.query(query)
        rows = query_job.result(page_size=batch_size)
        log(f"Query concluida em {(dt.datetime.now() - inicio_query).seconds}s. Iniciando carga...")

        total_inserted = 0
        batch_number = 0
        inicio_carga = dt.datetime.now()

        for batch in iter_batches(rows, batch_size):
            batch_number += 1
            inserted = insert_batch(collection, batch, ordered=False)
            total_inserted += inserted
            elapsed = (dt.datetime.now() - inicio_carga).seconds
            log(
                f"Batch {batch_number}: {inserted:,} docs inseridos"
                f" | acumulado: {total_inserted:,}"
                f" | tempo decorrido: {elapsed}s"
            )

        log(f"Criando indices em '{collection_name}'...")
        for keys, opts in config["indexes"]:
            try:
                idx_name = collection.create_index(keys, **opts)
                log(f"  ok: {idx_name}")
            except Exception as e:
                log(f"  aviso: indice ignorado ({e})")

        elapsed_total = (dt.datetime.now() - inicio_carga).seconds
        log(f"'{collection_name}' finalizado: {total_inserted:,} docs em {elapsed_total}s")
        return total_inserted

    finally:
        mongo_client.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Carrega dados do BigQuery para MongoDB (cursos / ies / sisu)"
    )
    parser.add_argument(
        "--table",
        choices=["cursos", "ies", "sisu", "all"],
        default="cursos",
        help="Qual tabela carregar. Use 'all' para carregar todas (default: cursos)",
    )
    parser.add_argument(
        "--collection",
        default=None,
        help="Sobrescreve o nome da collection destino (so funciona com uma tabela)",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("MONGO_DATABASE") or os.getenv("MONGODB_DB") or "higher_education",
        help="Nome do database destino no MongoDB",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=int(os.getenv("ETL_BATCH_SIZE", "20000")),
        help="Quantidade de documentos inseridos por lote",
    )
    parser.add_argument(
        "--drop-existing",
        action="store_true",
        help="Remove a collection antes de carregar",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limite opcional de registros para testes",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    tables = list(TABLE_CONFIGS.keys()) if args.table == "all" else [args.table]

    if args.collection and len(tables) == 1:
        TABLE_CONFIGS[tables[0]]["collection"] = args.collection

    log("=" * 60)
    log(f"Iniciando pipeline: {', '.join(tables)}")
    log("=" * 60)

    for table_key in tables:
        log(f"Carregando: {table_key}")
        total = load_table(
            table_key=table_key,
            batch_size=args.batch_size,
            database_name=args.database,
            drop_existing=args.drop_existing,
            limit=args.limit,
        )
        log(f"Total inserido em '{TABLE_CONFIGS[table_key]['collection']}': {total:,}")
        log("-" * 60)

    log("Pipeline concluido")


if __name__ == "__main__":
    main()
