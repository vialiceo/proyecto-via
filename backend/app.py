import os

from flask import Flask, jsonify, render_template, request

from config import get_config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
    )
    app.config.from_object(get_config())

    _inicializar_extensiones(app)
    _registrar_blueprints(app)
    _registrar_manejadores_error(app)

    os.makedirs(os.path.join(app.static_folder, "uploads", "perfiles"), exist_ok=True)

    return app


def _inicializar_extensiones(app):
    from backend import db
    from backend.extensions import cache, csrf, limiter, login_manager, mail

    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)


def _registrar_blueprints(app):
    from backend.admin import admin_bp
    from backend.api import api_bp
    from backend.auth import auth_bp
    from backend.perfil import usuarios_bp
    from backend.routes import public_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)


def _registrar_manejadores_error(app):
    @app.errorhandler(404)
    def no_encontrado(_error):
        if request.path.startswith("/api/"):
            return jsonify(error="Recurso no encontrado."), 404
        return render_template("ayuda.html"), 404

    @app.errorhandler(403)
    def prohibido(_error):
        if request.path.startswith("/api/"):
            return jsonify(error="No tienes permiso para esto."), 403
        return render_template("ayuda.html"), 403

    @app.errorhandler(429)
    def demasiadas_peticiones(_error):
        mensaje = "Demasiadas solicitudes. Intenta de nuevo en un momento."
        if request.path.startswith("/api/"):
            return jsonify(error=mensaje), 429
        return mensaje, 429

    @app.errorhandler(500)
    def error_interno(_error):
        if request.path.startswith("/api/"):
            return jsonify(error="Error interno del servidor."), 500
        return "Ocurrió un error interno. Intenta de nuevo más tarde.", 500
