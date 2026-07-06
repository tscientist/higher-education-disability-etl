import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BASE_DIR / ".env")

GOLD_COLLECTION = "gold_course_indicators"
SISU_COLLECTION = "sisu_aggregated"


def get_mongo_uri():
    uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError("Defina MONGO_URI ou MONGODB_URI no arquivo .env.")
    return uri


def get_database_name():
    return (
        os.getenv("MONGO_DATABASE")
        or os.getenv("MONGODB_DB")
        or os.getenv("DB_NAME")
        or "higher_education"
    )


@lru_cache(maxsize=1)
def get_client():
    return MongoClient(
        get_mongo_uri(),
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=30000,
    )


def get_db():
    return get_client()[get_database_name()]


def get_gold_collection():
    return get_db()[GOLD_COLLECTION]


def get_sisu_collection():
    return get_db()[SISU_COLLECTION]


def ping():
    get_client().admin.command("ping")
    return True


def collection_counts():
    db = get_db()
    return {
        GOLD_COLLECTION: db[GOLD_COLLECTION].count_documents({}),
        SISU_COLLECTION: db[SISU_COLLECTION].count_documents({}),
    }
