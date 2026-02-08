from flask import Flask
from dotenv import load_dotenv

from app.config import Config
from app.extensions import db, login_manager

def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.cron import cron_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(cron_bp)

    with app.app_context():
        db.create_all()

    return app
