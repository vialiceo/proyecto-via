import time

from flask import current_app, session, Blueprint, flash, redirect, render_template, request, url_for
from flask_login import (
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)

from backend import models, utils
from backend.extensions import limiter, login_manager

auth_bp = Blueprint("auth", __name__)


class Usuario(UserMixin):
    def __init__(self, fila):
        self.id = fila["id"]
        self.nombre = fila["nombre"]
        self.correo = fila["correo"]
        self.usuario = fila["usuario"]
        self.rol = fila["rol"]
        self.estado = fila["estado"]
        self.foto = fila.get("foto")
        self.forzar_cambio_password = bool(fila["forzar_cambio_password"])

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self.estado == "activo"


@auth_bp.before_app_request
def _enforce_expiracion_sesion():
    """Cierra la sesion cuando paso el tiempo fijo desde el login, aunque la
    persona siga activa. La expiracion se fija una sola vez al iniciar sesion,
    asi que navegar o hacer cambios no la corre."""
    if not current_user.is_authenticated:
        return
    expira = session.get("expira_en")
    if expira is not None and time.time() > expira:
        logout_user()
        session.clear()


@login_manager.user_loader
def cargar_usuario(usuario_id):
    fila = models.obtener_usuario_por_id(usuario_id)
    return Usuario(fila) if fila else None


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    if request.method == "POST":
        identificador = (request.form.get("usuario") or "").strip()
        password = request.form.get("contrasena") or ""

        fila = models.obtener_usuario_por_login(identificador) if identificador else None

        if not fila or not utils.verificar_password(fila["password_hash"], password):
            models.registrar_bitacora(fila["id"] if fila else None, "login_fallido", ip=utils.ip_cliente())
            flash("Usuario o contraseña incorrectos.", "error")
            return render_template("login.html"), 401

        if fila["estado"] != "activo":
            flash("Tu cuenta no está activa. Contacta a la institución.", "error")
            return render_template("login.html"), 403

        usuario = Usuario(fila)
        login_user(usuario)
        """
        La sesion dura un tiempo FIJO desde AHORA (el login) y no se renueva al
        navegar. Se guarda la hora exacta de expiracion: _enforce_expiracion_sesion
        la hace cumplir en el servidor y el contador del navegador la lee.
        """
        session.permanent = True
        session["expira_en"] = (
            time.time() + current_app.permanent_session_lifetime.total_seconds()
        )
        models.registrar_login(usuario.id)
        utils.encolar_tarea(models.registrar_bitacora, usuario.id, "login", ip=utils.ip_cliente())

        if usuario.forzar_cambio_password:
            flash("Por seguridad, debes definir una nueva contraseña.", "info")
            return redirect(url_for("auth.cambiar_password"))

        siguiente = utils.redireccion_segura(request.args.get("next"), url_for("public.index"))
        """
        No se salta directo al destino: primero la pantalla de bienvenida,
        que da un respiro visual y confirma que la sesión quedó lista.
        """
        return redirect(url_for("auth.preparando", next=siguiente))

    return render_template("login.html")


@auth_bp.route("/preparando")
@login_required
def preparando():
    """Pantalla breve tras iniciar sesión. Muestra el loader y, con JS, salta
    sola al destino. El `next` se valida para no permitir redirección abierta."""
    destino = utils.redireccion_segura(request.args.get("next"), url_for("public.index"))
    return render_template("preparando.html", destino=destino)


@auth_bp.route("/ping")
@login_required
def ping():
    """Petición ligera que renueva la sesión mientras haya actividad. La usa el
    contador de sesión del navegador para no cerrar la sesión de alguien que
    está usando la página sin cambiar de página."""
    session.permanent = True
    return "", 204


@auth_bp.route("/logout")
@login_required
def logout():
    utils.encolar_tarea(models.registrar_bitacora, current_user.id, "logout", ip=utils.ip_cliente())
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/recuperar", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def recuperar():
    if request.method == "POST":
        identificador = (request.form.get("identificador") or "").strip()
        fila = models.obtener_usuario_por_login(identificador) if identificador else None

        if fila:
            token_plano, token_hash, expira_en = utils.generar_token(minutos_validez=30)
            models.crear_token_reset(fila["id"], token_hash, expira_en)
            enlace = url_for("auth.restablecer", token=token_plano, _external=True)
            utils.enviar_correo_async(
                fila["correo"],
                "Recuperación de contraseña — V.I.A",
                f"Hola {fila['nombre']},\n\n"
                f"Para restablecer tu contraseña entra a este enlace (vence en 30 minutos):\n{enlace}\n\n"
                "Si no fuiste tú, ignora este correo.",
            )

        flash("Si el correo o usuario existe, te enviamos instrucciones para restablecer tu contraseña.", "info")
        return redirect(url_for("auth.login"))

    return render_template("recuperar.html")


@auth_bp.route("/recuperar/<token>", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def restablecer(token):
    token_hash = utils.hash_token(token)
    registro_token = models.obtener_token_valido(token_hash)

    if not registro_token:
        flash("El enlace de recuperación no es válido o ya venció. Solicita uno nuevo.", "error")
        return redirect(url_for("auth.recuperar"))

    if request.method == "POST":
        nueva_password = request.form.get("password") or ""
        confirmacion = request.form.get("password_confirmacion") or ""

        if len(nueva_password) < 8:
            flash("La contraseña debe tener al menos 8 caracteres.", "error")
            return render_template("restablecer.html", token=token)
        if nueva_password != confirmacion:
            flash("Las contraseñas no coinciden.", "error")
            return render_template("restablecer.html", token=token)

        models.cambiar_password(registro_token["usuario_id"], utils.hash_password(nueva_password))
        models.marcar_token_usado(registro_token["id"])
        utils.encolar_tarea(
            models.registrar_bitacora, registro_token["usuario_id"], "password_restablecida", ip=utils.ip_cliente()
        )
        flash("Contraseña actualizada. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login"))

    return render_template("restablecer.html", token=token)


@auth_bp.route("/cambiar-password", methods=["GET", "POST"])
@login_required
def cambiar_password():
    if request.method == "POST":
        actual = request.form.get("password_actual") or ""
        nueva = request.form.get("password") or ""
        confirmacion = request.form.get("password_confirmacion") or ""

        fila = models.obtener_usuario_por_id(current_user.id)
        if not utils.verificar_password(fila["password_hash"], actual):
            flash("La contraseña actual no es correcta.", "error")
            return render_template("cambiar_password.html")
        if len(nueva) < 8:
            flash("La nueva contraseña debe tener al menos 8 caracteres.", "error")
            return render_template("cambiar_password.html")
        if nueva != confirmacion:
            flash("Las contraseñas no coinciden.", "error")
            return render_template("cambiar_password.html")

        models.cambiar_password(current_user.id, utils.hash_password(nueva), forzar_cambio=False)
        utils.encolar_tarea(models.registrar_bitacora, current_user.id, "password_cambiada", ip=utils.ip_cliente())
        flash("Contraseña actualizada.", "success")
        return redirect(url_for("public.index"))

    return render_template("cambiar_password.html")
