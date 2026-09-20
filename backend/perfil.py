import os
from datetime import datetime

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from backend import experiencia, models, utils
from backend.extensions import cache, limiter

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")

TIPOS_SOLICITUD = [
    "Certificado de egresado",
    "Constancia de estudios",
    "Descuento por excelencia",
    "Reingreso académico",
    "Retiro temporal",
    "Otro",
]


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
            return render_template("perfil.html", perfil=vista, active_page="actualizar", mostrar_edicion=True), 400

        avisos = experiencia.guardar_perfil(current_user.id, datos, contactos)
        flash("Perfil actualizado.", "success")
        for categoria, texto in avisos:
            flash(texto, categoria)
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

    if not utils.es_imagen_real(archivo.stream):
        flash("El archivo no es una imagen válida, aunque termine en .jpg o .png.", "error")
        return redirect(url_for("usuarios.perfil"))

    nombre_seguro = utils.nombre_archivo_seguro(current_user.id, archivo.filename)
    """
    OJO: se usa static_folder (la carpeta que Flask SIRVE), no root_path.
    root_path apunta a backend/, asi que guardaba en backend/static/uploads/...
    mientras Flask servia /static/... desde <raiz>/static/... -> foto 404.
    """
    carpeta_absoluta = os.path.join(current_app.static_folder, "uploads", "perfiles")
    os.makedirs(carpeta_absoluta, exist_ok=True)
    archivo.save(os.path.join(carpeta_absoluta, nombre_seguro))

    foto_anterior = current_user.foto
    ruta_publica = f"/static/uploads/perfiles/{nombre_seguro}"
    models.actualizar_foto(current_user.id, ruta_publica)
    utils.borrar_archivo_subido(foto_anterior)
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
    return models.listar_comentarios_visibles(pagina=pagina, por_pagina=20)


@usuarios_bp.route("/promociones")
@login_required
def promociones():
    return render_template(
        "promocion.html",
        promociones=_todas_las_promociones_cacheadas(),
        imagenes_promocion=_anios_con_imagen(),
        active_page="promociones",
    )


@usuarios_bp.route("/promociones/<int:anio>/egresados")
@login_required
def promocion_egresados(anio):
    """Egresados de una promoción, en JSON, para el desplegable del carrusel del
    inicio (no recarga la página). Devuelve solo los campos que cada quien puede
    ver según la privacidad del egresado; la administración ve todo."""
    es_admin = current_user.rol == "administrador"
    salida = []
    for e in _egresados_por_promocion_cacheados(anio):
        publicos = (e.get("campos_publicos") or "").split(",")
        def visible(campo):
            return es_admin or campo in publicos
        salida.append({
            "id": e["id"],
            "nombre": e["nombre"],
            "foto": e["foto"] or "",
            "anio": e["anio_promocion"] or "",
            "tecnico": e["tecnico_nombre"] or "",
            "destacado": "1" if e["destacado"] else "0",
            "profesion": (e["profesion"] or "") if visible("profesion") else "",
            "residencia": (e["lugar_residencia"] or "") if visible("lugar_residencia") else "",
            "estudio": (e["lugar_estudio"] or "") if visible("lugar_estudio") else "",
            "correo": (e["correo"] or "") if visible("correo") else "",
            "frase": (e["frase"] or "") if visible("frase") else "",
        })
    return jsonify(egresados=salida)


@cache.memoize(timeout=300)
def _anios_con_imagen():
    """Años que tienen foto de promoción en static/img/promociones/<anio>.jpg.
    Así la plantilla solo pide la imagen cuando existe y no llena la consola de
    404 para las promociones sin foto."""
    carpeta = os.path.join(current_app.root_path, "static", "img", "promociones")
    try:
        nombres = os.listdir(carpeta)
    except OSError:
        return set()
    anios = set()
    for nombre in nombres:
        base, ext = os.path.splitext(nombre)
        if ext.lower() in (".jpg", ".jpeg", ".png", ".webp") and base.isdigit():
            anios.add(int(base))
    return anios


@cache.memoize(timeout=180)
def _todas_las_promociones_cacheadas():
    return models.listar_todas_promociones()


@cache.memoize(timeout=120)
def _egresados_por_promocion_cacheados(anio):
    return models.listar_egresados_por_promocion(anio, pagina=1, por_pagina=200)


@usuarios_bp.route("/directorio")
@login_required
def directorio():
    busqueda = request.args.get("q", "").strip() or None
    tecnico_id = request.args.get("tecnico_id", type=int)
    anio_promocion = request.args.get("anio_promocion", type=int)
    pagina, por_pagina = utils.parametros_paginacion(valor_por_defecto=24, maximo=60)

    items, total = models.listar_directorio(
        busqueda=busqueda, tecnico_id=tecnico_id, anio_promocion=anio_promocion,
        pagina=pagina, por_pagina=por_pagina,
    )
    tecnicos = models.listar_tecnicos_activos()

    return render_template(
        "perfiles.html",
        egresados=items,
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        tecnicos=tecnicos,
        filtros={"q": busqueda or "", "tecnico_id": tecnico_id or "", "anio_promocion": anio_promocion or ""},
        active_page="directorio",
    )


@usuarios_bp.route("/directorio/<int:usuario_id>/destacar", methods=["POST"])
@utils.admin_required
@limiter.limit("120 per hour")
def destacar_egresado(usuario_id):
    """Alterna la marca de "destacado" de un egresado. Solo administración.
    Responde JSON porque lo llama el modal del directorio con fetch."""
    nuevo_estado = models.alternar_destacado(usuario_id)
    if nuevo_estado is None:
        return jsonify(ok=False, error="Egresado no encontrado."), 404
    """
    El directorio y las promociones quedan cacheados; hay que refrescarlos
    para que la insignia aparezca al recargar.
    """
    cache.delete_memoized(_egresados_por_promocion_cacheados)
    return jsonify(ok=True, destacado=nuevo_estado)


@usuarios_bp.route("/solicitudes", methods=["GET", "POST"])
@login_required
def solicitudes():
    if request.method == "POST":
        tipo = (request.form.get("tipo") or "").strip()
        descripcion = (request.form.get("descripcion") or "").strip()

        if tipo not in TIPOS_SOLICITUD:
            flash("Selecciona un tipo de solicitud válido.", "error")
        elif not utils.texto_no_vacio(descripcion, 5, 500):
            flash("Describe tu solicitud en al menos 5 caracteres.", "error")
        else:
            models.crear_solicitud(current_user.id, tipo, descripcion)
            flash("Solicitud enviada. Te avisaremos cuando cambie de estado.", "success")
        return redirect(url_for("usuarios.solicitudes"))

    estado = request.args.get("estado") or None
    pagina, por_pagina = utils.parametros_paginacion(valor_por_defecto=20, maximo=50)

    if current_user.rol == "administrador":
        items, total = models.listar_solicitudes_admin(estado=estado, pagina=pagina, por_pagina=por_pagina)
    else:
        items = models.listar_solicitudes_usuario(current_user.id, estado=estado, pagina=pagina, por_pagina=por_pagina)
        total = len(items)

    return render_template(
        "solicitudes.html",
        solicitudes=items,
        total=total,
        estado=estado or "",
        tipos=TIPOS_SOLICITUD,
        active_page="solicitudes",
    )


@usuarios_bp.route("/solicitudes/<int:solicitud_id>/estado", methods=["POST"])
@utils.admin_required
def solicitud_estado(solicitud_id):
    estado = request.form.get("estado")
    respuesta = (request.form.get("respuesta") or "").strip() or None
    if estado not in ("pendiente", "en_proceso", "aprobada", "rechazada", "cancelada"):
        flash("Estado no válido.", "error")
    else:
        models.actualizar_estado_solicitud(solicitud_id, estado, respuesta)
        flash("Solicitud actualizada.", "success")
    return redirect(url_for("usuarios.solicitudes"))


@usuarios_bp.route("/mensajes")
@login_required
def mensajes():
    conversaciones = models.listar_conversaciones(current_user.id)

    conversacion_id = request.args.get("con", type=int)
    conversacion_actual = None
    hilo = []
    if conversacion_id:
        conversacion_actual = models.obtener_conversacion(conversacion_id, current_user.id)
        if conversacion_actual:
            hilo = models.listar_mensajes(conversacion_id)
            models.marcar_mensajes_leidos(conversacion_id, current_user.id)

    return render_template(
        "mensajes.html",
        conversaciones=conversaciones,
        conversacion_id=conversacion_id,
        conversacion_actual=conversacion_actual,
        hilo=hilo,
        active_page="mensajes",
    )


@usuarios_bp.route("/mensajes/<int:conversacion_id>/enviar", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def mensajes_enviar(conversacion_id):
    conversacion = models.obtener_conversacion(conversacion_id, current_user.id)
    if not conversacion:
        abort(404)

    contenido = (request.form.get("contenido") or "").strip()
    if utils.texto_no_vacio(contenido, 1, 2000):
        models.enviar_mensaje(conversacion_id, current_user.id, contenido)
    return redirect(url_for("usuarios.mensajes", con=conversacion_id))


@usuarios_bp.route("/mensajes/con/<int:usuario_id>")
@login_required
def mensajes_con(usuario_id):
    """
    Mensajearte a ti mismo no tiene sentido: en vez de un 404 crudo, se
    avisa y se vuelve al directorio.
    """
    if usuario_id == current_user.id:
        flash("No puedes enviarte un mensaje a ti mismo.", "info")
        return redirect(url_for("usuarios.directorio"))
    if not models.obtener_usuario_por_id(usuario_id):
        flash("Esa persona ya no existe.", "error")
        return redirect(url_for("usuarios.directorio"))
    conversacion_id = models.obtener_o_crear_conversacion(current_user.id, usuario_id)
    return redirect(url_for("usuarios.mensajes", con=conversacion_id))


@usuarios_bp.route("/eventos")
@login_required
def eventos():
    momento = "pasados" if request.args.get("momento") == "pasados" else "proximos"
    pagina, por_pagina = utils.parametros_paginacion(valor_por_defecto=20, maximo=50)
    items = models.listar_eventos(
        momento=momento, pagina=pagina, por_pagina=por_pagina, usuario_id=current_user.id
    )
    return render_template("eventos.html", eventos=items, momento=momento, active_page="eventos")


@usuarios_bp.route("/eventos/<int:evento_id>")
@login_required
def evento_detalle(evento_id):
    evento = models.obtener_evento(evento_id, usuario_id=current_user.id)
    if not evento:
        abort(404)
    return render_template("evento_detalle.html", evento=evento, active_page="eventos")


@usuarios_bp.route("/eventos/<int:evento_id>/favorito", methods=["POST"])
@login_required
@limiter.limit("60 per hour")
def evento_favorito(evento_id):
    if not models.obtener_evento(evento_id):
        abort(404)
    marcado = models.alternar_evento_favorito(current_user.id, evento_id)
    if marcado:
        flash("Evento guardado. Te recordaremos por correo el día del evento.", "success")
    else:
        flash("Quitaste el evento de tus favoritos.", "info")
    """Volver a donde estaba (detalle o lista)."""
    destino = utils.redireccion_segura(request.form.get("volver_a"), url_for("usuarios.eventos"))
    return redirect(destino)


@usuarios_bp.route("/eventos/nuevo", methods=["GET", "POST"])
@utils.admin_required
def eventos_nuevo():
    if request.method == "POST":
        errores, datos = _validar_evento(request.form)
        if errores:
            for error in errores:
                flash(error, "error")
            return render_template("eventos.html", eventos=[], momento="proximos", evento_form=datos, active_page="eventos"), 400
        models.crear_evento(**datos, creado_por=current_user.id)
        flash("Evento creado.", "success")
        return redirect(url_for("usuarios.eventos"))
    return redirect(url_for("usuarios.eventos"))


@usuarios_bp.route("/eventos/<int:evento_id>/editar", methods=["POST"])
@utils.admin_required
def eventos_editar(evento_id):
    if not models.obtener_evento(evento_id):
        abort(404)
    errores, datos = _validar_evento(request.form)
    if errores:
        for error in errores:
            flash(error, "error")
    else:
        models.actualizar_evento(evento_id, **datos)
        flash("Evento actualizado.", "success")
    return redirect(url_for("usuarios.eventos"))


@usuarios_bp.route("/eventos/<int:evento_id>/eliminar", methods=["POST"])
@utils.admin_required
def eventos_eliminar(evento_id):
    models.eliminar_evento(evento_id)
    flash("Evento eliminado.", "success")
    return redirect(url_for("usuarios.eventos"))


def _validar_evento(form):
    errores = []
    titulo = (form.get("titulo") or "").strip()
    descripcion = (form.get("descripcion") or "").strip() or None
    categoria = form.get("categoria") or "otro"
    lugar = (form.get("lugar") or "").strip() or None
    fecha_raw = (form.get("fecha_inicio") or "").strip()

    if not utils.texto_no_vacio(titulo, 3, 150):
        errores.append("El título debe tener entre 3 y 150 caracteres.")
    if categoria not in ("academico", "profesional", "egresados", "taller", "cultural", "deportivo", "otro"):
        errores.append("Categoría no válida.")

    fecha_inicio = None
    try:
        fecha_inicio = datetime.fromisoformat(fecha_raw)
    except ValueError:
        errores.append("La fecha y hora del evento no son válidas.")

    return errores, {
        "titulo": titulo,
        "descripcion": descripcion,
        "categoria": categoria,
        "lugar": lugar,
        "fecha_inicio": fecha_inicio,
    }


@usuarios_bp.route("/configuracion")
@login_required
def configuracion():
    vista = experiencia.construir_vista_perfil(current_user.id)
    return render_template("configuracion.html", perfil=vista, active_page="configuracion")
