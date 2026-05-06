"""Acesso à collection `movies` do MongoDB (Content Service)."""

from __future__ import annotations

import math
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

from app.db import get_collection
from app.cache import get_cache

SEARCH_CACHE_TTL = 3600
DETAIL_CACHE_TTL = 86400
POPULAR_CACHE_TTL = 1800


def _safe_cache():
    try:
        return get_cache()
    except Exception:
        return None


def _normalize_query(query: str) -> str:
    return " ".join(query.lower().strip().split())


def _search_cache_key(query: str, limit: int, skip: int) -> str:
    normalized = _normalize_query(query)
    page = max(1, (skip // max(limit, 1)) + 1)
    return f"movies:search:{normalized}:page:{page}"


def _detail_cache_key(movie_id: str) -> str:
    return f"movies:detail:{movie_id}"


def _popular_cache_key(limit: int) -> str:
    return f"movies:popular:{limit}"


def _cache_movie_detail(movie: dict) -> None:
    cache = _safe_cache()
    if cache is None:
        return
    try:
        cache.setex_json(_detail_cache_key(movie["_id"]), DETAIL_CACHE_TTL, movie)
    except Exception:
        return


def _invalidate_movie_detail(movie_id: str) -> None:
    cache = _safe_cache()
    if cache is None:
        return
    try:
        cache.delete(_detail_cache_key(movie_id))
    except Exception:
        return


def _serialize(doc: dict) -> dict:
    """Converte _id (ObjectId) em string para serialização JSON."""
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])
    return doc


def list_movies(genre: str | None = None, limit: int = 20, skip: int = 0) -> tuple[list[dict], int]:
    """Lista filmes paginados. Retorna (docs, total_filtrado)."""
    coll = get_collection()
    query: dict = {}
    if genre:
        query["genres"] = genre

    cursor = coll.find(query).skip(skip).limit(limit)
    docs = [_serialize(d) for d in cursor]
    total = coll.count_documents(query)
    return docs, total


def search_movies(query: str, limit: int = 20, skip: int = 0) -> tuple[list[dict], int]:
    """Busca full-text por título via índice TEXT. Retorna (docs, total)."""
    cache = _safe_cache()
    cache_key = _search_cache_key(query, limit, skip)
    if cache is not None:
        try:
            cached = cache.get_json(cache_key)
            if cached is not None:
                return cached["movies"], cached["total"]
        except Exception:
            pass

    coll = get_collection()
    normalized_query = _normalize_query(query)
    q = {"$text": {"$search": normalized_query}}
    cursor = coll.find(q).skip(skip).limit(limit)
    docs = [_serialize(d) for d in cursor]
    total = coll.count_documents(q)

    if cache is not None:
        try:
            cache.setex_json(cache_key, SEARCH_CACHE_TTL, {"movies": docs, "total": total})
        except Exception:
            pass

    return docs, total


def list_genres() -> list[str]:
    """Retorna a lista distinta de gêneros, ordenada alfabeticamente."""
    return sorted(g for g in get_collection().distinct("genres") if g)


def get_movie_by_id(movie_id: str) -> dict | None:
    """Busca por _id (string ObjectId). Retorna None se id inválido ou inexistente."""
    cache = _safe_cache()
    cache_key = _detail_cache_key(movie_id)
    if cache is not None:
        try:
            cached = cache.get_json(cache_key)
            if cached is not None:
                return cached
        except Exception:
            pass

    try:
        oid = ObjectId(movie_id)
    except (InvalidId, TypeError):
        return None
    doc = get_collection().find_one({"_id": oid})
    movie = _serialize(doc) if doc else None
    if movie is not None:
        _cache_movie_detail(movie)
    return movie


def list_popular_movies(limit: int = 20) -> tuple[list[dict], int]:
    """Lista os filmes mais populares com cache derivado por limite."""
    cache = _safe_cache()
    cache_key = _popular_cache_key(limit)
    if cache is not None:
        try:
            cached = cache.get_json(cache_key)
            if cached is not None:
                return cached["movies"], cached["total"]
        except Exception:
            pass

    coll = get_collection()
    cursor = (
        coll.find({})
        .sort([("rating", -1), ("title", 1)])
        .limit(limit)
    )
    docs = [_serialize(d) for d in cursor]
    total = coll.count_documents({})

    if cache is not None:
        try:
            cache.setex_json(
                cache_key,
                POPULAR_CACHE_TTL,
                {"movies": docs, "total": total},
            )
        except Exception:
            pass

    return docs, total


def create_movie(data: dict) -> dict:
    """Insere um novo filme. Retorna o doc com _id preenchido."""
    doc = {
        "title": data["title"],
        "original_title": data.get("original_title", data["title"]),
        "year": data["year"],
        "genres": data.get("genres", []),
        "director": data.get("director"),
        "overview": data.get("overview"),
        "rating": data.get("rating"),
        "runtime": data.get("runtime"),
        "poster_url": data.get("poster_url"),
        "backdrop_url": data.get("backdrop_url"),
        "cast": data.get("cast", []),
        "language": data.get("language"),
        "imdb_id": data.get("imdb_id"),
        "tmdb_id": data.get("tmdb_id"),
    }
    result = get_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    movie = _serialize(doc)
    _invalidate_movie_detail(movie["_id"])
    return movie


def update_movie(movie_id: str, data: dict) -> dict | None:
    """Atualiza um filme existente e invalida o cache do detalhe."""
    try:
        oid = ObjectId(movie_id)
    except (InvalidId, TypeError):
        return None

    allowed_fields = {
        "title",
        "original_title",
        "year",
        "genres",
        "director",
        "overview",
        "rating",
        "runtime",
        "poster_url",
        "backdrop_url",
        "cast",
        "language",
        "imdb_id",
        "tmdb_id",
    }
    update_fields = {key: value for key, value in data.items() if key in allowed_fields}
    if not update_fields:
        return get_movie_by_id(movie_id)

    updated = get_collection().find_one_and_update(
        {"_id": oid},
        {"$set": update_fields},
        return_document=ReturnDocument.AFTER,
    )
    movie = _serialize(updated) if updated else None
    if movie is not None:
        _invalidate_movie_detail(movie_id)
    return movie
