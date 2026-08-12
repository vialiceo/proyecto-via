"""
Sitio público: portada (ayuda.html para visitantes / index.html para
quien ya inició sesión), la página de contacto (con el formulario que
alimenta soporte_tickets) y el registro de canal telefónico si alguna
vez se agrega.
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from backend import models, utils
from backend.extensions import cache, limiter

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    if current_user.is_authenticated:
        return render_template("index.html", promociones_recientes=_promociones_recientes_cacheadas())
    return render_template("ayuda.html")


@cache.memoize(timeout=180)
def _promociones_recientes_cacheadas():
    """Las 4 promociones del carrusel de la portada. Se calculan una vez
    cada 3 minutos, no en cada carga de index.html."""
    return models.listar_promociones_recientes(limite=4)


@public_bp.route("/ayuda")
def ayuda():
    return render_template("ayuda.html")


@public_bp.route("/aviso-legal")
def aviso_legal():
    return render_template("aviso_legal.html")


@public_bp.route("/contacto", methods=["GET", "POST"])
@limiter.limit("6 per hour", methods=["POST"])
def contacto():
    if request.method == "POST":
        nombre = (request.form.get("nombre") or "").strip()
        correo = (request.form.get("correo") or "").strip().lower()
        asunto = (request.form.get("asunto") or "").strip()
        mensaje = (request.form.get("mensaje") or "").strip()

        errores = []
        if not utils.texto_no_vacio(nombre, 3, 150):
            errores.append("Escribe tu nombre completo.")
        if not utils.validar_correo(correo):
            errores.append("El correo no es válido.")
        if not utils.texto_no_vacio(asunto, 3, 200):
            errores.append("Escribe un asunto breve.")
        if not utils.texto_no_vacio(mensaje, 10, 2000):
            errores.append("El mensaje debe tener entre 10 y 2000 caracteres.")

        if errores:
            for error in errores:
                flash(error, "error")
            return render_template("contacto.html"), 400

        usuario_id = current_user.id if current_user.is_authenticated else None
        models.crear_ticket_soporte(nombre, correo, asunto, mensaje, usuario_id=usuario_id, canal="formulario")
        utils.enviar_correo_async(
            "soporte@via.liceotame.edu.co",
            f"Nuevo mensaje de soporte: {asunto}",
            f"De: {nombre} <{correo}>\n\n{mensaje}",
        )
        flash("Tu mensaje fue enviado. Te responderemos pronto.", "success")
        return redirect(url_for("public.contacto"))

    return render_template("contacto.html")
