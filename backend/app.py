import logging
import os
from logging.handlers import RotatingFileHandler

import mysql.connector
from flask import Flask, jsonify, render_template, request

from werkzeug.middleware.proxy_fix import ProxyFix

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
    """
    La sesion dura un tiempo FIJO desde el login: no se renueva al navegar.
    Sin esto, Flask repone la caducidad de la cookie en cada respuesta y la
    sesion se volveria "rodante". La caducidad real la fija session["expira_en"]
    al iniciar sesion (backend/auth.py) y la hace cumplir _enforce_expiracion_sesion.
    """
    app.config["SESSION_REFRESH_EACH_REQUEST"] = False

    """
    Detrás del proxy de PythonAnywhere: confía en 1 salto para leer el
    esquema real (https), el host y la IP del cliente (X-Forwarded-*).
    Así funcionan bien las cookies "Secure", HSTS y el rate-limiting por IP.
    """
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    _configurar_logging(app)
    _inicializar_extensiones(app)
    _registrar_blueprints(app)
    _registrar_manejadores_error(app)
    _registrar_cabeceras_seguridad(app)
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

    """
    1 MB por archivo y 3 de respaldo: suficiente para revisar qué pasó ayer
    sin que el disco se llene solo.
    """
    archivo = RotatingFileHandler(
        os.path.join(carpeta, "via.log"), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    archivo.setFormatter(formato)
    logger.addHandler(archivo)

    """
    Los correos van además a su propio archivo. Con MAIL_SERVER vacío este
    archivo ES la bandeja de salida: ahí se leen las contraseñas temporales
    y las respuestas de soporte sin montar un servidor SMTP.
    """
    correos = RotatingFileHandler(
        os.path.join(carpeta, "correos.log"), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    correos.setFormatter(formato)
    correos.addFilter(lambda registro: getattr(registro, "es_correo", False))
    logger.addHandler(correos)


def _registrar_cabeceras_seguridad(app):
    """Cabeceras de seguridad + CORS en cada respuesta.

    - Las cabeceras defienden contra clickjacking, sniffing de tipo MIME y
      fuga del referer. Son baratas y no cambian el comportamiento del sitio.
    - CORS aquí es RESTRICTIVO: solo los orígenes de CORS_ORIGINS pueden hacer
      peticiones cruzadas al API, y solo si el navegador manda ese origen. Sin
      la lista, ninguna web externa recibe encabezados CORS, que es justo lo
      que se quiere en una app de un solo dominio.
    """
    origenes = set(app.config.get("CORS_ORIGINS") or [])

    """Métodos y cabeceras que el API acepta en una petición cruzada."""
    METODOS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    CABECERAS = "Content-Type, X-API-Key, X-Requested-With"

    def _aplicar_cors(respuesta):
        """
        CORS solo aplica al API: las páginas HTML son navegación del mismo
        sitio y nunca deben reflejar un origen externo.
        """
        if not request.path.startswith("/api/"):
            return respuesta
        origen = request.headers.get("Origin")
        """
        Solo se responde CORS si el origen está en la lista blanca. La
        comparación es exacta: nada de comodines ni de "termina en".
        """
        if origen and origen in origenes:
            respuesta.headers["Access-Control-Allow-Origin"] = origen
            """
            Cambia según el Origin: los proxys no deben cachear una
            respuesta de un origen y servírsela a otro.
            """
            respuesta.headers.add("Vary", "Origin")
            respuesta.headers["Access-Control-Allow-Credentials"] = "true"
            respuesta.headers["Access-Control-Allow-Methods"] = METODOS
            respuesta.headers["Access-Control-Allow-Headers"] = CABECERAS
            respuesta.headers["Access-Control-Max-Age"] = "600"
        return respuesta

    @app.after_request
    def _cabeceras(respuesta):
        """
        --- Cabeceras de seguridad -------------------------------------
        El sitio no debe poder incrustarse en un iframe de otra página
        (defensa contra clickjacking).
        """
        respuesta.headers.setdefault("X-Frame-Options", "DENY")
        """El navegador respeta el Content-Type declarado y no "adivina"."""
        respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
        """No filtrar la URL completa a sitios externos."""
        respuesta.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        """Apagar APIs del navegador que el sitio no usa."""
        respuesta.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=(), payment=()"
        )
        """
        CSP: por defecto todo del mismo origen. Se permiten estilos y la
        fuente de Google Fonts, que es lo único externo que carga el sitio.
        """
        respuesta.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self' 'unsafe-inline'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'",
        )
        """HSTS solo bajo HTTPS: obliga al navegador a volver siempre por TLS."""
        if request.is_secure:
            respuesta.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return _aplicar_cors(respuesta)

    @app.before_request
    def _preflight_cors():
        """
        El navegador manda un OPTIONS antes de una petición cruzada "no
        simple". Se responde aquí con 204 y los encabezados que arma
        _aplicar_cors, sin entrar a la lógica de la ruta.
        """
        if request.method == "OPTIONS" and request.headers.get("Origin"):
            from flask import Response

            return _aplicar_cors(Response(status=204))


def _registrar_contexto(app):
    """Deja `escudo_url` disponible en todas las plantillas.

    Si nadie ha subido el escudo todavía, vale None y las plantillas dibujan el
    escudo de CSS. Así no se pide un archivo que no existe en cada carga.
    """
    carpeta = os.path.join(app.static_folder, "img", "escudo")

    def _buscar_escudo():
        """
        Primero los nombres recomendados; si no, cualquier imagen que haya
        en la carpeta (así funciona aunque el archivo tenga otro nombre).
        """
        for nombre in ("escudo-liceo.svg", "escudo-liceo.png", "escudo-liceo.webp"):
            if os.path.isfile(os.path.join(carpeta, nombre)):
                return f"/static/img/escudo/{nombre}"
        if os.path.isdir(carpeta):
            for nombre in sorted(os.listdir(carpeta)):
                if nombre.lower().endswith((".svg", ".png", ".webp", ".jpg", ".jpeg")):
                    return f"/static/img/escudo/{nombre}"
        return None

    encontrado = _buscar_escudo()

    @app.context_processor
    def inyectar_escudo():
        """
        En desarrollo se vuelve a mirar, para no tener que reiniciar
        el servidor después de copiar el archivo.
        """
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
