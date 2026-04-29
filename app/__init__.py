import os
from flask import Flask
from flask_cors import CORS
from app.config import config
from app.db import init_from_uri
from app.routes.movies import movies_bp
from app.routes.health import health_bp


def create_app(config_name=None):
    """Factory que cria e configura a aplicação Flask."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Em testing, a collection é injetada via fixture (mongomock).
    if config_name != "testing":
        mongo_uri = app.config.get("MONGO_URI")
        if not mongo_uri:
            raise RuntimeError("MONGO_URI ausente nas configurações.")
        init_from_uri(mongo_uri)

    CORS(app)

    app.register_blueprint(health_bp)
    app.register_blueprint(movies_bp)

    return app
