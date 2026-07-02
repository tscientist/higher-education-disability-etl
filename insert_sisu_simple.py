#!/usr/bin/env python3
"""
Script simples e direto para inserir SISU agregado no MongoDB
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 80, flush=True)
print("INSERINDO SISU AGREGADO NO MONGODB", flush=True)
print("=" * 80, flush=True)

try:
    print("\n[STEP 1] Importando módulos...", flush=True)
    from src.clients.bigquery_client import BigQueryClient
    from src.clients.mongodb_client import MongoDBClient
    print("Módulos importados", flush=True)
    
    print("\n[STEP 2] Conectando ao BigQuery...", flush=True)
    bq = BigQueryClient()
    print("BigQuery conectado", flush=True)
    
    print("\n[STEP 3] Lendo SISU agregado (2022)...", flush=True)
    sisu_docs = bq.aggregate_sisu_by_course_optimized(
        "staging",
        "stg_sisu_microdados",
        year_range=(2022, 2022)
    )
    print(f"{len(sisu_docs)} documentos SISU lidos", flush=True)
    
    if not sisu_docs:
        print("Nenhum documento encontrado!", flush=True)
        sys.exit(1)
    
    print(f"\n[STEP 4] Primeiro documento SISU:")
    first = sisu_docs[0]
    for key in list(first.keys())[:3]:
        print(f"  {key}: {first[key]}", flush=True)
    
    print("\n[STEP 5] Conectando ao MongoDB...", flush=True)
    mongo = MongoDBClient()
    print("MongoDB conectado", flush=True)
    
    print(f"\n[STEP 6] Inserindo {len(sisu_docs)} documentos...", flush=True)
    result = mongo.upsert_documents(
        "sisu_aggregated",
        sisu_docs,
        id_field="_id"
    )
    print(f"Inserção concluída:", flush=True)
    print(f"  - Matched:  {result.get('matched', 0)}", flush=True)
    print(f"  - Modified: {result.get('modified', 0)}", flush=True)
    print(f"  - Upserted: {result.get('upserted', 0)}", flush=True)
    
    print("\n[STEP 7] Verificando...", flush=True)
    count = mongo.count_documents("sisu_aggregated")
    print(f"Total em sisu_aggregated: {count}", flush=True)
    
    print("\nSUCESSO!", flush=True)
    
except Exception as e:
    print(f"\nERRO: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
