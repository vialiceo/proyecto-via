"""
Área autenticada de "usuarios": actualizar el propio perfil y el feed
de comentarios. Todo bajo /usuarios y protegido con @login_required.
"""
import os

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from backend import experiencia, models, utils
from backend.extensions import cache, limiter

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


@usuarios_bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    if request.method == "POST":
        errores, datos = experiencia.validar_datos_perfil(request.form)

        tipos = request.form.getlist("contacto_tipo")
        valores = request.form.getlist("contacto_valor")
        errores_contacto, contactos = experiencia.validar_contactos(tipos, valores)
        errores += errores_contacto

        if errores:
            for error in errores:
                flash(error, "error")
            vista = experiencia.construir_vista_perfil(current_user.id)
            return render_template("perfil.html", perfil=vista, active_page="actualizar"), 400

        experiencia.guardar_perfil(current_user.id, datos, contactos)
        flash("Perfil actualizado.", "success")
        return redirect(url_for("usuarios.perfil"))

    vista = experiencia.construir_vista_perfil(current_user.id)
    return render_template("perfil.html", perfil=vista, active_page="actualizar")


@usuarios_bp.route("/perfil/foto", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def actualizar_foto():
    archivo = request.files.get("foto")
    if not archivo or archivo.filename == "":
        flash("No se seleccionó ninguna imagen.", "error")
        return redirect(url_for("usuarios.perfil"))

    if not utils.extension_permitida(archivo.filename):
        flash("Formato no permitido. Usa PNG, JPG o WEBP.", "error")
        return redirect(url_for("usuarios.perfil"))

    nombre_seguro = utils.nombre_archivo_seguro(current_user.id, archivo.filename)
    carpeta_absoluta = os.path.join(current_app.root_path, current_app.config["UPLOAD_FOLDER"])
    os.makedirs(carpeta_absoluta, exist_ok=True)
    archivo.save(os.path.join(carpeta_absoluta, nombre_seguro))

    ruta_publica = f"/static/uploads/perfiles/{nombre_seguro}"
    models.actualizar_foto(current_user.id, ruta_publica)
    utils.encolar_tarea(models.registrar_bitacora, current_user.id, "foto_actualizada", ip=utils.ip_cliente())

    flash("Foto de perfil actualizada.", "success")
    return redirect(url_for("usuarios.perfil"))


@usuarios_bp.route("/comentarios", methods=["GET", "POST"])
@login_required
@limiter.limit("30 per minute")
def comentarios():
    if request.method == "POST":
        contenido = (request.form.get("contenido") or "").strip()
        if not utils.texto_no_vacio(contenido, longitud_min=3, longitud_max=1000):
            flash("Escribe un comentario entre 3 y 1000 caracteres.", "error")
        else:
            models.crear_comentario(current_user.id, contenido)
            cache.delete_memoized(_comentarios_visibles_cacheados)
            flash("Comentario publicado.", "success")
        return redirect(url_for("usuarios.comentarios"))

    pagina, _ = utils.parametros_paginacion(valor_por_defecto=20, maximo=50)
    items = _comentarios_visibles_cacheados(pagina)
    return render_template("comentarios.html", comentarios=items, pagina=pagina, active_page="comentarios")


@cache.memoize(timeout=30)
def _comentarios_visibles_cacheados(pagina):
    """Se calcula una sola vez por página cada 30s: el feed de comentarios
    no necesita ser exacto al segundo y así no se golpea MySQL en cada
    request de cada uno de los 5000 usuarios viendo la misma página."""
    return models.listar_comentarios_visibles(pagina=pagina, por_pagina=20)


@usuarios_bp.route("/promocion/<int:anio>")
@login_required
def promocion(anio):
    egresados = _egresados_por_promocion_cacheados(anio)
    return render_template("promocion.html", anio=anio, egresados=egresados, active_page="principal")


@cache.memoize(timeout=120)
def _egresados_por_promocion_cacheados(anio):
    """Una sola query trae nombre + foto + profesión + frase de todos los
    egresados de la promoción: la tarjeta y el pop-up salen del mismo dato,
    ya calculado, sin pedir nada extra por cada clic."""
    return models.listar_egresados_por_promocion(anio, pagina=1, por_pagina=200)
