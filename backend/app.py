import logging
import os
from logging.handlers import RotatingFileHandler

import mysql.connector
from flask import Flask, jsonify, render_template, request

from config import get_config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_PASOS_ARRANQUE = [
    "Corre <code>mysql -u root -p &lt; database/crear_usuario_mysql.sql</code> "
    "(antes cambia <code>CAMBIA_ESTA_CLAVE</code> por una contraseña tuya).",
    "Escribe esa misma contraseña en el archivo <code>.env</code>, línea "
    "<code>MYSQL_PASSWORD=</code>",
    "Carga las tablas: <code>mysql -u root -p egresados &lt; database/schema.sql</code>",
    "Carga los datos de prueba: <code>mysql -u root -p egresados &lt; database/datos.sql</code>",
    "Reinicia el servidor (Ctrl+C y <code>python run.py</code>).",
]

_PASOS_MYSQL = {
    1045: _PASOS_ARRANQUE,
    1049: [
        "La base <code>egresados</code> no existe todavía.",
        "Corre <code>mysql -u root -p &lt; database/crear_usuario_mysql.sql</code>",
        "Luego <code>mysql -u root -p egresados &lt; database/schema.sql</code>",
        "Y <code>mysql -u root -p egresados &lt; database/datos.sql</code>",
    ],
    1146: [
        "Existe la base pero le faltan tablas.",
        "Corre <code>mysql -u root -p egresados &lt; database/schema.sql</code>",
        "Si ya tenías datos de antes, corre además "
        "<code>mysql -u root -p egresados &lt; database/migracion_graduados.sql</code>",
    ],
    2003: [
        "El servidor MySQL no está corriendo o no escucha en ese puerto.",
        "En Windows: abre <code>services.msc</code> y arranca el servicio MySQL.",
        "Verifica que <code>MYSQL_HOST</code> y <code>MYSQL_PORT</code> del "
        "<code>.env</code> coincidan con tu instalación.",
    ],
    None: _PASOS_ARRANQUE,
}


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
    )
    app.config.from_object(get_config())

    _configurar_logging(app)
    _inicializar_extensiones(app)
    _registrar_blueprints(app)
    _registrar_manejadores_error(app)
    _registrar_contexto(app)

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


def _configurar_logging(app):
    """Sin esto, `logger.info` no aparece en ninguna parte.

    Un `logging.Logger` recién creado no tiene manejadores y su nivel efectivo
    es WARNING, así que todo lo que la app registraba como INFO — incluidos los
    correos simulados y las contraseñas temporales — se perdía en silencio.
    """
    logger = logging.getLogger("via")
    if logger.handlers:
        return

    logger.setLevel(logging.DEBUG if app.debug else logging.INFO)

    formato = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%d/%m/%Y %H:%M:%S"
    )

    consola = logging.StreamHandler()
    consola.setFormatter(formato)
    logger.addHandler(consola)

    carpeta = os.path.join(BASE_DIR, "logs")
    os.makedirs(carpeta, exist_ok=True)

    # 1 MB por archivo y 3 de respaldo: suficiente para revisar qué pasó ayer
    # sin que el disco se llene solo.
    archivo = RotatingFileHandler(
        os.path.join(carpeta, "via.log"), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    archivo.setFormatter(formato)
    logger.addHandler(archivo)

    # Los correos van además a su propio archivo. Con MAIL_SERVER vacío este
    # archivo ES la bandeja de salida: ahí se leen las contraseñas temporales
    # y las respuestas de soporte sin montar un servidor SMTP.
    correos = RotatingFileHandler(
        os.path.join(carpeta, "correos.log"), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    correos.setFormatter(formato)
    correos.addFilter(lambda registro: getattr(registro, "es_correo", False))
    logger.addHandler(correos)


def _registrar_contexto(app):
    """Deja `escudo_url` disponible en todas las plantillas.

    Si nadie ha subido el escudo todavía, vale None y las plantillas dibujan el
    escudo de CSS. Así no se pide un archivo que no existe en cada carga.
    """
    carpeta = os.path.join(app.static_folder, "img", "escudo")

    def _buscar_escudo():
        for nombre in ("escudo-liceo.svg", "escudo-liceo.png", "escudo-liceo.webp"):
            if os.path.isfile(os.path.join(carpeta, nombre)):
                return f"/static/img/escudo/{nombre}"
        return None

    encontrado = _buscar_escudo()

    @app.context_processor
    def inyectar_escudo():
        # En desarrollo se vuelve a mirar, para no tener que reiniciar
        # el servidor después de copiar el archivo.
        return {"escudo_url": _buscar_escudo() if app.debug else encontrado}


def _registrar_manejadores_error(app):
    """Las rutas /api/ responden JSON; el resto ve la página error.html."""

    def _responder(codigo, titulo, mensaje, detalle=None, pasos=None):
        if request.path.startswith("/api/"):
            return jsonify(error=mensaje), codigo
        return (
            render_template(
                "error.html",
                codigo=codigo,
                titulo=titulo,
                mensaje=mensaje,
                detalle=detalle,
                pasos=pasos,
            ),
            codigo,
        )

    @app.errorhandler(mysql.connector.Error)
    def error_mysql(error):
        """En desarrollo dice exactamente qué falta; en producción no filtra nada."""
        if not app.debug:
            return _responder(
                500,
                "Algo salió mal",
                "Ocurrió un error interno y no pudimos completar lo que pediste.",
                "El problema quedó registrado. Intenta de nuevo en unos minutos.",
            )
        return _responder(
            500,
            "La base de datos no responde",
            f"MySQL devolvió: {error}",
            f"Configuración actual: {app.config['MYSQL_USER']}@{app.config['MYSQL_HOST']}:"
            f"{app.config['MYSQL_PORT']}/{app.config['MYSQL_DB']}",
            pasos=_PASOS_MYSQL.get(getattr(error, "errno", None), _PASOS_MYSQL[None]),
        )

    @app.errorhandler(404)
    def no_encontrado(_error):
        return _responder(
            404,
            "Página no encontrada",
            "La dirección que abriste no existe o cambió de lugar.",
            "Revisa que el enlace esté completo. Si llegaste desde el menú, avísanos por Ayuda.",
        )

    @app.errorhandler(403)
    def prohibido(_error):
        return _responder(
            403,
            "No tienes permiso",
            "Esta sección está reservada para otro tipo de cuenta.",
            "Si crees que deberías tener acceso, escríbenos desde Ayuda.",
        )

    @app.errorhandler(413)
    def archivo_muy_grande(_error):
        limite = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        return _responder(
            413,
            "El archivo pesa demasiado",
            f"La imagen supera el límite de {limite} MB.",
            "Reduce el tamaño de la foto y vuelve a intentarlo. "
            "Con 800×800 píxeles sobra para una foto de perfil.",
        )

    @app.errorhandler(429)
    def demasiadas_peticiones(_error):
        return _responder(
            429,
            "Demasiados intentos",
            "Hiciste muchas peticiones seguidas y el sistema las pausó un momento.",
            "Espera unos minutos y vuelve a intentarlo.",
        )

    @app.errorhandler(500)
    def error_interno(_error):
        return _responder(
            500,
            "Algo salió mal",
            "Ocurrió un error interno y no pudimos completar lo que pediste.",
            "El problema quedó registrado. Intenta de nuevo en unos minutos.",
        )
