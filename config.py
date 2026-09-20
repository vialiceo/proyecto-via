import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def _bool(valor, default=False):
    if valor is None:
        return default
    return str(valor).strip().lower() in ("1", "true", "yes", "on")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-cambiar-en-produccion")
    """Clave para cifrar la cédula por columna (AES-SIV). Ver backend/utils.py."""
    CEDULA_ENC_KEY = os.getenv("CEDULA_ENC_KEY")

    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB = os.getenv("MYSQL_DB", "egresados")
    MYSQL_POOL_SIZE = int(os.getenv("MYSQL_POOL_SIZE", "10"))

    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200 per minute")

    CACHE_TYPE = os.getenv("CACHE_TYPE", "SimpleCache")
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", "60"))
    CACHE_REDIS_URL = os.getenv("CACHE_REDIS_URL")

    MAIL_SERVER = os.getenv("MAIL_SERVER") or None
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = _bool(os.getenv("MAIL_USE_TLS"), True)
    MAIL_USERNAME = os.getenv("MAIL_USERNAME") or None
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD") or None
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "no-responder@liceotame.edu.co")

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH_MB", "3")) * 1024 * 1024
    UPLOAD_FOLDER = os.path.join("static", "uploads", "perfiles")
    EXTENSIONES_FOTO_PERMITIDAS = {"png", "jpg", "jpeg", "webp"}

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool(os.getenv("SESSION_COOKIE_SECURE"), False)
    '''cierre de sesion automatico despues de 1 hora segun el estado de la cookie.'''
    PERMANENT_SESSION_LIFETIME = timedelta(
        minutes=int(os.getenv("SESSION_MINUTOS", "60"))
    )

    ADMIN_PAGE_SIZE = 25

    SOLICITUDES_API_KEY = os.getenv("SOLICITUDES_API_KEY") or None

'''  --- CORS (CORS (por sus siglas en inglés, Cross-Origin Resource Sharing, o Intercambio de Recursos de Origen Cruzado) es un mecanismo de seguridad implementado por los navegadores web que permite a una página web solicitar y cargar recursos desde un dominio diferente al que sirvió la página original)
    Lista blanca de orígenes que pueden hacer peticiones cruzadas al API.
    VACÍA a propósito: la aplicación es de una sola página servida por el
    mismo Flask, así que no necesita CORS para funcionar. Solo se llena si
    una plataforma externa (otro dominio) va a consumir /api/v1.
    
    NUNCA poner "*": con cookies de sesión, un comodín deja que cualquier
    web lea los datos del usuario. La lista se compara exacta.'''
CORS_ORIGINS="https://plataforma.example.com,https://otra.example.com"
CORS_ORIGINS = [
    o.strip()
    for o in (os.getenv("CORS_ORIGINS") or "").split(",")
    if o.strip()
]


class DevelopmentConfig(Config):
    DEBUG = True
    """En desarrollo no se cachean CSS/JS, para ver los cambios sin Ctrl+F5."""
    SEND_FILE_MAX_AGE_DEFAULT = 0
    TEMPLATES_AUTO_RELOAD = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    """En produccion los estaticos se cachean 1 dia: menos peticiones al servidor."""
    SEND_FILE_MAX_AGE_DEFAULT = 86400


def get_config():
    env = os.getenv("FLASK_ENV", "development").lower()
    return ProductionConfig if env == "production" else DevelopmentConfig
