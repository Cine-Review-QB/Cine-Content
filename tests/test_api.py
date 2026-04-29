from bson import ObjectId

from app.db import get_collection


def _seed(docs):
    coll = get_collection()
    return coll.insert_many(docs).inserted_ids


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_list_movies_empty(client):
    response = client.get("/api/movies/")
    assert response.status_code == 200
    data = response.get_json()
    assert data["movies"] == []
    assert data["total"] == 0


def test_list_movies_paginated(client):
    _seed([
        {"title": f"Filme {i}", "year": 2000 + i, "genres": ["Drama"]}
        for i in range(5)
    ])
    response = client.get("/api/movies/?limit=2&skip=1")
    data = response.get_json()
    assert response.status_code == 200
    assert len(data["movies"]) == 2
    assert data["total"] == 5
    assert data["limit"] == 2
    assert data["skip"] == 1


def test_list_movies_filter_by_genre(client):
    _seed([
        {"title": "A", "year": 1999, "genres": ["Drama"]},
        {"title": "B", "year": 2000, "genres": ["Comedy"]},
        {"title": "C", "year": 2001, "genres": ["Drama", "Romance"]},
    ])
    response = client.get("/api/movies/?genre=Drama")
    data = response.get_json()
    assert data["total"] == 2
    assert {m["title"] for m in data["movies"]} == {"A", "C"}


def test_get_movie_by_id(client):
    ids = _seed([{"title": "Matrix", "year": 1999, "genres": ["Sci-Fi"]}])
    response = client.get(f"/api/movies/{ids[0]}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "Matrix"
    assert data["_id"] == str(ids[0])


def test_get_movie_invalid_id(client):
    response = client.get("/api/movies/not-an-objectid")
    assert response.status_code == 404


def test_get_movie_not_found(client):
    fake_id = ObjectId()
    response = client.get(f"/api/movies/{fake_id}")
    assert response.status_code == 404


def test_add_movie(client):
    payload = {"title": "Matrix", "year": 1999, "director": "Wachowski"}
    response = client.post("/api/movies/", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["title"] == "Matrix"
    assert data["year"] == 1999
    assert "_id" in data


def test_add_movie_missing_fields(client):
    response = client.post("/api/movies/", json={"title": "Sem Ano"})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_invalid_pagination(client):
    response = client.get("/api/movies/?limit=999")
    assert response.status_code == 400
