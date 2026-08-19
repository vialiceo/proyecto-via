import os
from dotenv import load_dotenv

load_dotenv()


def _bool(valor, default=False):
    if valor is None:
        return default
    return str(valor).strip().lower() in ("1", "true", "yes", "on")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-cambiar-en-produccion")

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
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8

    ADMIN_PAGE_SIZE = 25

    SOLICITUDES_API_KEY = os.getenv("SOLICITUDES_API_KEY") or None


class DevelopmentConfig(Config):
    DEBUG = True

    # El navegador guarda los CSS y JS en caché: sin esto, al editar una hoja
    # de estilos hay que recargar con Ctrl+F5 para ver el cambio.
    SEND_FILE_MAX_AGE_DEFAULT = 0
    TEMPLATES_AUTO_RELOAD = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


def get_config():
    env = os.getenv("FLASK_ENV", "development").lower()
    return ProductionConfig if env == "production" else DevelopmentConfig
