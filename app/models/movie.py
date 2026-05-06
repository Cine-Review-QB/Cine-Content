"""Acesso à collection `movies` do MongoDB (Content Service)."""

from bson import ObjectId
from bson.errors import InvalidId

from app.db import get_collection


def _serialize(doc: dict) -> dict:
    """Converte _id (ObjectId) em string e combina rating/vote_count
    com reviews locais quando existem.

    Local rating é em escala 0.5–5; TMDB é 0–10. Convertemos local
    multiplicando por 2 antes da média ponderada — assim 1 review
    nossa vale o mesmo que 1 voto no TMDB.
    """
    if doc is None:
        return None
    doc["_id"] = str(doc["_id"])

    local_n = int(doc.get("local_review_count") or 0)
    if local_n > 0:
        tmdb_r = float(doc.get("rating") or 0.0)
        tmdb_v = int(doc.get("vote_count") or 0)
        local_avg = float(doc.get("local_avg_rating") or 0.0)
        local_on_10 = local_avg * 2
        denom = tmdb_v + local_n
        if denom > 0:
            combined = (tmdb_r * tmdb_v + local_on_10 * local_n) / denom
            doc["rating"] = round(combined, 2)
            doc["vote_count"] = denom
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
    coll = get_collection()
    q = {"$text": {"$search": query}}
    cursor = coll.find(q).skip(skip).limit(limit)
    docs = [_serialize(d) for d in cursor]
    total = coll.count_documents(q)
    return docs, total


def list_genres() -> list[str]:
    """Retorna a lista distinta de gêneros, ordenada alfabeticamente."""
    return sorted(g for g in get_collection().distinct("genres") if g)


def get_movie_by_id(movie_id: str) -> dict | None:
    """Busca por _id (string ObjectId). Retorna None se id inválido ou inexistente."""
    try:
        oid = ObjectId(movie_id)
    except (InvalidId, TypeError):
        return None
    doc = get_collection().find_one({"_id": oid})
    return _serialize(doc) if doc else None


def update_aggregate(movie_id: str, count: int, avg: float) -> bool:
    """Atualiza local_review_count e local_avg_rating do filme.

    Chamado pelo Cine-Review via PUT /movies/{id}/aggregate quando uma
    review é criada ou deletada. Retorna False se ID inválido ou filme
    não encontrado.
    """
    try:
        oid = ObjectId(movie_id)
    except (InvalidId, TypeError):
        return False
    result = get_collection().update_one(
        {"_id": oid},
        {
            "$set": {
                "local_review_count": int(count),
                "local_avg_rating": float(avg),
            }
        },
    )
    return result.matched_count > 0


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
        "vote_count": data.get("vote_count"),
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
    return _serialize(doc)
