"""Popula a collection cinedb.content com filmes da TMDB API.

Estratégia em duas fases:
1. **discover** — itera /discover/movie ordenado por popularidade desc e coleta os IDs
2. **detail**   — para cada ID, busca /movie/{id}?append_to_response=credits e monta o doc

Idempotente: o upsert é por `tmdb_id`. Rodar várias vezes só atualiza dados existentes.

Uso:
    python scripts/seed_movies_from_tmdb.py                  # default: 100 páginas (~2000 filmes)
    python scripts/seed_movies_from_tmdb.py --pages 5        # smoke test (~100 filmes)
    python scripts/seed_movies_from_tmdb.py --pages 250      # ~5000 filmes
    python scripts/seed_movies_from_tmdb.py --pages 500      # máximo permitido pela TMDB (~10k)
    python scripts/seed_movies_from_tmdb.py --concurrency 50

Pré-requisitos:
    - MONGO_URI no .env
    - TMDB_API_KEY no .env (https://www.themoviedb.org/settings/api)
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient, TEXT, UpdateOne
from pymongo.errors import BulkWriteError
from tqdm.asyncio import tqdm_asyncio

ROOT = Path(__file__).resolve().parent.parent
DB_NAME = "cinedb"
COLL_NAME = "content"

TMDB_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w500"
BACKDROP_BASE = "https://image.tmdb.org/t/p/original"

DEFAULT_PAGES = 500
DEFAULT_CONCURRENCY = 30
DEFAULT_MIN_VOTES = 100
TMDB_MAX_PAGES = 500
DETAIL_CHUNK = 1000


async def _request(
    client: httpx.AsyncClient,
    url: str,
    params: dict,
    *,
    retries: int = 1,
) -> dict | None:
    """GET com retry simples em 429."""
    for attempt in range(retries + 1):
        try:
            r = await client.get(url, params=params, timeout=15.0)
        except (httpx.RequestError, httpx.TimeoutException):
            return None

        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", "5"))
            await asyncio.sleep(wait)
            continue
        if r.status_code != 200:
            return None
        return r.json()
    return None


async def fetch_discover_page(
    client: httpx.AsyncClient,
    api_key: str,
    page: int,
    min_votes: int,
    sem: asyncio.Semaphore,
) -> list[int]:
    async with sem:
        data = await _request(
            client,
            f"{TMDB_BASE}/discover/movie",
            {
                "api_key": api_key,
                "sort_by": "popularity.desc",
                "page": page,
                "include_adult": "false",
                "include_video": "false",
                "language": "en-US",
                "vote_count.gte": min_votes,
            },
            retries=1,
        )
    if not data:
        return []
    return [m["id"] for m in data.get("results", []) if "id" in m]


async def fetch_movie_detail(
    client: httpx.AsyncClient,
    api_key: str,
    tmdb_id: int,
    sem: asyncio.Semaphore,
) -> dict | None:
    async with sem:
        return await _request(
            client,
            f"{TMDB_BASE}/movie/{tmdb_id}",
            {
                "api_key": api_key,
                "append_to_response": "credits",
                "language": "en-US",
            },
            retries=1,
        )


def _parse_year(release_date: str | None) -> int | None:
    if not release_date or len(release_date) < 4:
        return None
    head = release_date[:4]
    return int(head) if head.isdigit() else None


def build_doc(m: dict) -> dict | None:
    """Monta o doc Mongo a partir do payload TMDB. Retorna None se inválido."""
    if not m:
        return None
    title = m.get("title")
    imdb_id = m.get("imdb_id")
    if not title or not imdb_id:
        return None

    genres = [g["name"] for g in m.get("genres", []) if "name" in g]

    credits = m.get("credits") or {}
    cast_list = credits.get("cast", []) or []
    cast_top5 = [c["name"] for c in cast_list[:5] if "name" in c]

    crew = credits.get("crew", []) or []
    director = next(
        (c["name"] for c in crew if c.get("job") == "Director"),
        None,
    )

    poster_path = m.get("poster_path")
    backdrop_path = m.get("backdrop_path")

    return {
        "tmdb_id": m.get("id"),
        "imdb_id": imdb_id,
        "title": title,
        "original_title": m.get("original_title") or title,
        "year": _parse_year(m.get("release_date")),
        "genres": genres,
        "rating": float(m.get("vote_average") or 0.0),
        "runtime": int(m["runtime"]) if m.get("runtime") else None,
        "overview": (m.get("overview") or "").strip() or None,
        "poster_url": f"{POSTER_BASE}{poster_path}" if poster_path else None,
        "backdrop_url": f"{BACKDROP_BASE}{backdrop_path}" if backdrop_path else None,
        "director": director,
        "cast": cast_top5,
        "language": m.get("original_language"),
    }


def _flush(coll, ops: list[UpdateOne]) -> tuple[int, int]:
    if not ops:
        return 0, 0
    try:
        result = coll.bulk_write(ops, ordered=False)
        return result.upserted_count, result.modified_count
    except BulkWriteError as bwe:
        print(f"[warn] bulk_write parcial: {bwe.details.get('writeErrors', [])[:3]}")
        return 0, 0


def create_indexes(coll) -> None:
    print("[mongo] criando índices ...")
    coll.create_index([("tmdb_id", ASCENDING)], unique=True, name="tmdb_id_unique")
    coll.create_index([("imdb_id", ASCENDING)], unique=True, name="imdb_id_unique")
    coll.create_index(
        [("title", TEXT)],
        name="title_text",
        default_language="none",
        language_override="_text_language",
    )
    coll.create_index([("genres", ASCENDING)], name="genres_idx")
    coll.create_index([("rating", ASCENDING)], name="rating_idx")
    coll.create_index([("year", ASCENDING)], name="year_idx")
    print("[mongo] índices OK")


async def run(args: argparse.Namespace) -> None:
    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("TMDB_API_KEY")
    mongo_uri = os.environ.get("MONGO_URI")
    if not api_key:
        sys.exit("[erro] TMDB_API_KEY ausente no .env")
    if not mongo_uri:
        sys.exit("[erro] MONGO_URI ausente no .env")

    pages = min(args.pages, TMDB_MAX_PAGES)
    sem = asyncio.Semaphore(args.concurrency)

    mclient = MongoClient(mongo_uri)
    coll = mclient[DB_NAME][COLL_NAME]

    async with httpx.AsyncClient(http2=False) as hclient:
        # ---- Phase 1: discover IDs ----
        print(
            f"[discover] {pages} páginas (~{pages * 20} filmes) | "
            f"vote_count >= {args.min_votes}"
        )
        discover_tasks = [
            fetch_discover_page(hclient, api_key, p, args.min_votes, sem)
            for p in range(1, pages + 1)
        ]
        page_results = await tqdm_asyncio.gather(
            *discover_tasks, desc="discover", leave=False
        )
        seen: set[int] = set()
        for ids in page_results:
            seen.update(ids)
        all_ids = sorted(seen)
        print(f"[discover] {len(all_ids)} IDs únicos coletados")

        if not all_ids:
            print("[erro] nenhum ID retornado — verifique TMDB_API_KEY")
            mclient.close()
            return

        # ---- Phase 2: detail + credits, em chunks ----
        print(f"[detail] buscando detalhes+elenco (chunks de {DETAIL_CHUNK})")
        upserted = 0
        modified = 0
        invalid = 0
        for i in range(0, len(all_ids), DETAIL_CHUNK):
            batch_ids = all_ids[i : i + DETAIL_CHUNK]
            tasks = [
                fetch_movie_detail(hclient, api_key, mid, sem) for mid in batch_ids
            ]
            details = await tqdm_asyncio.gather(
                *tasks,
                total=len(tasks),
                desc=f"[{i + 1}-{i + len(batch_ids)}/{len(all_ids)}]",
                leave=False,
            )

            ops: list[UpdateOne] = []
            for raw in details:
                doc = build_doc(raw)
                if doc is None:
                    invalid += 1
                    continue
                ops.append(
                    UpdateOne(
                        {"tmdb_id": doc["tmdb_id"]},
                        {"$set": doc},
                        upsert=True,
                    )
                )
            up, mod = _flush(coll, ops)
            upserted += up
            modified += mod

    print(
        f"[done] inseridos: {upserted} | atualizados: {modified} | inválidos: {invalid}"
    )
    create_indexes(coll)
    mclient.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages",
        type=int,
        default=DEFAULT_PAGES,
        help=f"páginas /discover/movie a coletar (default {DEFAULT_PAGES}, max {TMDB_MAX_PAGES})",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"requests TMDB simultâneos (default {DEFAULT_CONCURRENCY})",
    )
    parser.add_argument(
        "--min-votes",
        type=int,
        default=DEFAULT_MIN_VOTES,
        help=(
            f"vote_count mínimo no /discover (default {DEFAULT_MIN_VOTES}). "
            "Evita outliers tipo rating 10.0 com 3 votos."
        ),
    )
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
