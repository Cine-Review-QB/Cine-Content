from flask import Blueprint, jsonify

from app.models.movie import list_genres

genres_bp = Blueprint("genres", __name__)


@genres_bp.get("/genres")
def list_genres_route():
    """Lista distinta de gêneros presentes na collection."""
    return jsonify({"genres": list_genres()}), 200
