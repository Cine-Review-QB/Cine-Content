import os
from flask import Flask
from flask_cors import CORS
from app.config import config
from app.routes.movies import movies_bp
from app.routes.health import health_bp


def create_app(config_name=None):
    """Factory que cria e configura a aplicação Flask."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    CORS(app)

    app.register_blueprint(health_bp)
    app.register_blueprint(movies_bp)

    return app
