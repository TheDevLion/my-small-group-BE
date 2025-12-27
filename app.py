from flask import Flask
from flask_cors import CORS

from config import CORS_ORIGINS, HYGRAPH_ADMIN_TOKEN, SESSION_SECRET_KEY
from routes.auth import auth_bp
from routes.docs import docs_bp
from routes.event_photos import event_photos_bp
from routes.group import group_bp

def create_app():
    if not HYGRAPH_ADMIN_TOKEN:
        raise RuntimeError("Missing HYGRAPH_ADMIN_TOKEN environment variable.")
    if not SESSION_SECRET_KEY:
        raise RuntimeError("Missing SESSION_SECRET_KEY environment variable.")

    app = Flask(__name__)
    CORS(app, supports_credentials=True, origins=CORS_ORIGINS)
    app.config["CORS_HEADERS"] = "Content-Type"

    app.register_blueprint(auth_bp)
    app.register_blueprint(docs_bp)
    app.register_blueprint(group_bp)
    app.register_blueprint(event_photos_bp)

    return app
