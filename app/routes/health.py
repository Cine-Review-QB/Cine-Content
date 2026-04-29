from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    """Verifica se a API está no ar."""
    return jsonify({"status": "ok", "message": "Cine-Content API está funcionando!"}), 200
