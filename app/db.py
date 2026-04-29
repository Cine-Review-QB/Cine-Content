"""Cliente MongoDB compartilhado pelo Content Service."""

from pymongo import MongoClient
from pymongo.collection import Collection

DB_NAME = "cinedb"
MOVIES_COLL = "content"

_collection: Collection | None = None


def init_from_uri(uri: str) -> None:
    """Inicializa a collection a partir do MONGO_URI. Chamado pela app factory."""
    global _collection
    _collection = MongoClient(uri)[DB_NAME][MOVIES_COLL]


def set_collection(collection) -> None:
    """Injeta uma collection (real ou mongomock). Usado por testes."""
    global _collection
    _collection = collection


def get_collection() -> Collection:
    if _collection is None:
        raise RuntimeError(
            "MongoDB não inicializado — chame init_from_uri() ou set_collection()."
        )
    return _collection
