from flask import Blueprint, jsonify, request
from app.models.movie import (
    get_all_movies,
    get_movie_by_id,
    create_movie,
    get_reviews_for_movie,
    create_review,
)

movies_bp = Blueprint("movies", __name__, url_prefix="/api/movies")


@movies_bp.get("/")
def list_movies():
    """Lista todos os filmes disponíveis."""
    genre = request.args.get("genre")
    movies = get_all_movies()
    if genre:
        movies = [m for m in movies if genre in m.get("genre", [])]
    return jsonify({"movies": movies, "total": len(movies)}), 200


@movies_bp.get("/<int:movie_id>")
def get_movie(movie_id):
    """Retorna os detalhes de um filme pelo ID."""
    movie = get_movie_by_id(movie_id)
    if movie is None:
        return jsonify({"error": "Filme não encontrado."}), 404
    return jsonify(movie), 200


@movies_bp.post("/")
def add_movie():
    """Adiciona um novo filme."""
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


@movies_bp.get("/<int:movie_id>/reviews")
def list_reviews(movie_id):
    """Lista as avaliações de um filme."""
    movie = get_movie_by_id(movie_id)
    if movie is None:
        return jsonify({"error": "Filme não encontrado."}), 404

    reviews = get_reviews_for_movie(movie_id)
    return jsonify({"reviews": reviews, "total": len(reviews)}), 200


@movies_bp.post("/<int:movie_id>/reviews")
def add_review(movie_id):
    """Adiciona uma avaliação a um filme."""
    movie = get_movie_by_id(movie_id)
    if movie is None:
        return jsonify({"error": "Filme não encontrado."}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Corpo da requisição inválido ou ausente."}), 400

    required_fields = ["author", "rating"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return (
            jsonify({"error": f"Campos obrigatórios ausentes: {', '.join(missing)}"}),
            400,
        )

    rating = data["rating"]
    if not isinstance(rating, (int, float)) or not (1 <= rating <= 10):
        return jsonify({"error": "A nota deve ser um número entre 1 e 10."}), 400

    review = create_review(movie_id, data)
    return jsonify(review), 201
