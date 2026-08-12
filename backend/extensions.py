from flask import jsonify, redirect, request, url_for
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_wtf import CSRFProtect
from flask_mail import Mail

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Inicia sesión para continuar."
login_manager.login_message_category = "info"


@login_manager.unauthorized_handler
def _no_autenticado():
    if request.path.startswith("/api/"):
        return jsonify(error="No autenticado."), 401
    return redirect(url_for("auth.login", next=request.path))


limiter = Limiter(key_func=get_remote_address)

cache = Cache()
csrf = CSRFProtect()
mail = Mail()
