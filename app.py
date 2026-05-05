import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app

app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    # Porta default 8002 — alinhada com CONTENT_SERVICE_URL do Gateway.
    port = int(os.environ.get("PORT", 8002))
    app.run(host="0.0.0.0", port=port)
