def test_health_check(client):
    """Verifica se o endpoint de health check retorna status 200 e status 'ok'."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"


def test_list_movies(client):
    """Verifica se a listagem de filmes retorna uma lista paginada com total."""
    response = client.get("/api/movies/")
    assert response.status_code == 200
    data = response.get_json()
    assert "movies" in data
    assert "total" in data
    assert data["total"] == len(data["movies"])


def test_get_movie_by_id(client):
    """Verifica se um filme existente é retornado corretamente pelo seu ID."""
    response = client.get("/api/movies/1")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == 1
    assert "title" in data


def test_get_movie_not_found(client):
    """Verifica se a busca por um ID inexistente retorna 404 com mensagem de erro."""
    response = client.get("/api/movies/9999")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data


def test_add_movie(client):
    """Verifica se um novo filme é criado corretamente com os dados fornecidos."""
    payload = {"title": "Matrix", "year": 1999, "director": "Wachowski"}
    response = client.post("/api/movies/", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["title"] == "Matrix"
    assert data["year"] == 1999


def test_add_movie_missing_fields(client):
    """Verifica se a criação de filme sem campos obrigatórios retorna 400."""
    response = client.post("/api/movies/", json={"title": "Sem Ano"})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_list_reviews(client):
    """Verifica se as avaliações de um filme existente são listadas corretamente."""
    response = client.get("/api/movies/1/reviews")
    assert response.status_code == 200
    data = response.get_json()
    assert "reviews" in data


def test_add_review(client):
    """Verifica se uma avaliação válida é criada e retornada com os dados corretos."""
    payload = {"author": "Teste", "rating": 8, "comment": "Muito bom!"}
    response = client.post("/api/movies/1/reviews", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["author"] == "Teste"
    assert data["rating"] == 8


def test_add_review_invalid_rating(client):
    """Verifica se uma avaliação com nota fora do intervalo 1–10 retorna 400."""
    payload = {"author": "Teste", "rating": 15}
    response = client.post("/api/movies/1/reviews", json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_add_review_movie_not_found(client):
    """Verifica se adicionar avaliação a um filme inexistente retorna 404."""
    payload = {"author": "Teste", "rating": 7}
    response = client.post("/api/movies/9999/reviews", json=payload)
    assert response.status_code == 404
