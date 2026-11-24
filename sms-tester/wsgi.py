"""Entry point for gunicorn: `gunicorn wsgi:app`."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Local development only. In production use gunicorn (see Procfile).
    app.run(host="127.0.0.1", port=5000, debug=False)
