from flask import Blueprint, jsonify, request

from app.models.movie import (
    create_movie,
    get_movie_by_id,
    list_movies,
    search_movies,
)

movies_bp = Blueprint("movies", __name__, url_prefix="/movies")

MAX_LIMIT = 100
DEFAULT_LIMIT = 20


def _parse_pagination():
    try:
        limit = int(request.args.get("limit", DEFAULT_LIMIT))
        skip = int(request.args.get("skip", 0))
    except ValueError:
        return None, None, "Parâmetros 'limit' e 'skip' devem ser inteiros."
    if limit < 1 or limit > MAX_LIMIT:
        return None, None, f"'limit' deve estar entre 1 e {MAX_LIMIT}."
    if skip < 0:
        return None, None, "'skip' não pode ser negativo."
    return limit, skip, None


@movies_bp.get("")
@movies_bp.get("/")
def list_movies_route():
    """Lista filmes paginados, opcionalmente filtrados por gênero."""
    limit, skip, err = _parse_pagination()
    if err:
        return jsonify({"error": err}), 400

    genre = request.args.get("genre")
    movies, total = list_movies(genre=genre, limit=limit, skip=skip)
    return jsonify({
        "movies": movies,
        "total": total,
        "limit": limit,
        "skip": skip,
    }), 200


@movies_bp.get("/search")
def search_movies_route():
    """Busca full-text por título (rota fixa, antes de /<movie_id>)."""
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"error": "Parâmetro 'q' é obrigatório."}), 400

    limit, skip, err = _parse_pagination()
    if err:
        return jsonify({"error": err}), 400

    movies, total = search_movies(q, limit=limit, skip=skip)
    return jsonify({
        "movies": movies,
        "total": total,
        "query": q,
        "limit": limit,
        "skip": skip,
    }), 200


@movies_bp.get("/genre/<genre>")
def list_by_genre_route(genre):
    """Filtra filmes por gênero (URL path) — alias amigável de ?genre=."""
    limit, skip, err = _parse_pagination()
    if err:
        return jsonify({"error": err}), 400

    movies, total = list_movies(genre=genre, limit=limit, skip=skip)
    return jsonify({
        "movies": movies,
        "total": total,
        "genre": genre,
        "limit": limit,
        "skip": skip,
    }), 200


@movies_bp.get("/<movie_id>")
def get_movie(movie_id):
    """Retorna os detalhes de um filme pelo _id (ObjectId em string)."""
    movie = get_movie_by_id(movie_id)
    if movie is None:
        return jsonify({"error": "Filme não encontrado."}), 404
    return jsonify(movie), 200


@movies_bp.post("")
@movies_bp.post("/")
def add_movie():
    """Adiciona um novo filme à collection."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Corpo da requisição inválido ou ausente."}), 400

    required_fields = ["title", "year"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return (
            jsonify({"error": f"Campos obrigatórios ausentes: {', '.join(missing)}"}),
            400,
        )

    movie = create_movie(data)
    return jsonify(movie), 201
