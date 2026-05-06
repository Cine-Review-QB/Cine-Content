import os
import time
import redis
import pytest

from app.db import get_collection
from app.cache import init_redis, close_redis, get_redis_client


REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/1")


@pytest.fixture(autouse=True)
def redis_setup():
    # Init redis for the Content service to use DB 1
    init_redis({"REDIS_URL": REDIS_URL})
    client = redis.from_url(REDIS_URL, decode_responses=True)
    # flush DB to isolate tests
    client.flushdb()
    yield client
    client.flushdb()
    close_redis()


@pytest.fixture(autouse=True)
def patch_mongomock_text_search(client):
    """Patch mongomock to emulate $text searches by translating to case-insensitive title regex."""
    from app.db import get_collection

    coll = get_collection()
    orig_find = coll.find
    orig_count = coll.count_documents

    def find_with_text(filter=None, *args, **kwargs):
        if isinstance(filter, dict) and "$text" in filter:
            search = filter["$text"]["$search"]
            # simple case-insensitive substring match on title
            regex_filter = {"title": {"$regex": search, "$options": "i"}}
            return orig_find(regex_filter, *args, **kwargs)
        return orig_find(filter, *args, **kwargs)

    def count_with_text(filter=None, *args, **kwargs):
        if isinstance(filter, dict) and "$text" in filter:
            search = filter["$text"]["$search"]
            regex_filter = {"title": {"$regex": search, "$options": "i"}}
            return orig_count(regex_filter, *args, **kwargs)
        return orig_count(filter, *args, **kwargs)

    coll.find = find_with_text
    coll.count_documents = count_with_text
    yield
    coll.find = orig_find
    coll.count_documents = orig_count


def normalized_key(q: str, page: int) -> str:
    nq = " ".join(q.lower().strip().split())
    return f"movies:search:{nq}:page:{page}"


def test_search_cache_hit_and_ttl(client, redis_setup):
    # seed one movie
    coll = get_collection()
    coll.insert_one({"title": "Matrix", "year": 1999, "genres": ["Sci-Fi"]})

    r = redis_setup
    # first call populates cache
    resp = client.get("/movies/search?q=Matrix")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["movies"]

    key = normalized_key("Matrix", 1)
    assert r.exists(key)
    ttl = r.ttl(key)
    assert ttl > 0 and ttl <= 3600

    # remove data from DB to ensure subsequent call served from cache
    coll.delete_many({})
    resp2 = client.get("/movies/search?q=  Matrix  ")
    assert resp2.status_code == 200
    data2 = resp2.get_json()
    assert data2["movies"]  # still returned from cache


def test_detail_cache_hit_and_ttl(client, redis_setup):
    coll = get_collection()
    inserted = coll.insert_one({"title": "Dune", "year": 2021})
    movie_id = str(inserted.inserted_id)

    r = redis_setup
    resp = client.get(f"/movies/{movie_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["_id"] == movie_id

    key = f"movies:detail:{movie_id}"
    assert r.exists(key)
    ttl = r.ttl(key)
    assert ttl > 0 and ttl <= 86400

    # delete from DB and ensure cache still returns
    coll.delete_many({})
    resp2 = client.get(f"/movies/{movie_id}")
    assert resp2.status_code == 200


def test_popular_cache_and_normalization(client, redis_setup):
    coll = get_collection()
    # seed several movies with rating
    coll.insert_many([
        {"title": "A", "rating": 9.0},
        {"title": "B", "rating": 8.0},
        {"title": "C", "rating": 7.0},
    ])

    r = redis_setup
    resp = client.get("/movies/popular?limit=2")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["movies"]) == 2

    key = f"movies:popular:2"
    assert r.exists(key)
    ttl = r.ttl(key)
    assert ttl > 0 and ttl <= 1800

    # normalization test for search keys
    client.get("/movies/search?q=Hello%20World")
    client.get("/movies/search?q=  hello   world  ")
    nk1 = normalized_key("Hello World", 1)
    nk2 = normalized_key("  hello   world  ", 1)
    assert nk1 == nk2
