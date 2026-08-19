import hmac

import mysql.connector
from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from backend import experiencia, models, utils
from backend.extensions import cache, csrf, limiter

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def _error(mensaje, codigo=400):
    return jsonify(error=mensaje), codigo


def _ok(data, codigo=200):
    return jsonify(data=data), codigo


@api_bp.route("/perfil", methods=["GET"])
@login_required
def perfil_get():
    return _ok(experiencia.construir_vista_perfil(current_user.id))


@api_bp.route("/perfil", methods=["PUT"])
@login_required
@limiter.limit("20 per hour")
def perfil_put():
    body = request.get_json(silent=True) or {}

    errores, datos = experiencia.validar_datos_perfil(body)
    contactos_body = body.get("contactos") or []
    tipos = [c.get("tipo") for c in contactos_body]
    valores = [c.get("valor") for c in contactos_body]
    errores_contacto, contactos = experiencia.validar_contactos(tipos, valores)
    errores += errores_contacto

    if errores:
        return _error(" / ".join(errores), 400)

    experiencia.guardar_perfil(current_user.id, datos, contactos)
    return _ok(experiencia.construir_vista_perfil(current_user.id))


@cache.memoize(timeout=30)
def _comentarios_api_cacheados(pagina):
    return models.listar_comentarios_visibles(pagina=pagina, por_pagina=20)


@api_bp.route("/comentarios", methods=["GET"])
@login_required
def comentarios_get():
    pagina, _ = utils.parametros_paginacion(valor_por_defecto=20, maximo=50)
    return _ok(_comentarios_api_cacheados(pagina))


@api_bp.route("/comentarios", methods=["POST"])
@login_required
@limiter.limit("15 per minute")
def comentarios_post():
    body = request.get_json(silent=True) or {}
    contenido = (body.get("contenido") or "").strip()
    if not utils.texto_no_vacio(contenido, 3, 1000):
        return _error("El comentario debe tener entre 3 y 1000 caracteres.")

    comentario_id = models.crear_comentario(current_user.id, contenido)
    cache.delete_memoized(_comentarios_api_cacheados)
    return _ok({"id": comentario_id}, 201)


@api_bp.route("/soporte", methods=["POST"])
@limiter.limit("6 per hour")
def soporte_post():
    body = request.get_json(silent=True) or {}
    nombre = (body.get("nombre") or "").strip()
    correo = (body.get("correo") or "").strip().lower()
    asunto = (body.get("asunto") or "").strip()
    mensaje = (body.get("mensaje") or "").strip()

    if not utils.texto_no_vacio(nombre, 3, 150):
        return _error("Escribe tu nombre completo.")
    if not utils.validar_correo(correo):
        return _error("El correo no es válido.")
    if not utils.texto_no_vacio(asunto, 3, 200):
        return _error("Escribe un asunto breve.")
    if not utils.texto_no_vacio(mensaje, 10, 2000):
        return _error("El mensaje debe tener entre 10 y 2000 caracteres.")

    usuario_id = current_user.id if current_user.is_authenticated else None
    ticket_id = models.crear_ticket_soporte(nombre, correo, asunto, mensaje, usuario_id=usuario_id, canal="formulario")
    return _ok({"id": ticket_id}, 201)


def _api_key_valida():
    """La clave se compara con hmac para no filtrar información por el tiempo de respuesta."""
    esperada = current_app.config.get("SOLICITUDES_API_KEY")
    if not esperada:
        return False
    recibida = request.headers.get("X-API-Key") or ""
    return hmac.compare_digest(str(esperada), recibida)


@api_bp.route("/solicitudes-cuenta", methods=["POST"])
@csrf.exempt
@limiter.limit("60 per hour")
def solicitudes_cuenta_post():
    """Permite que una plataforma externa deje solicitudes en la misma bandeja de aprobación."""
    if not _api_key_valida():
        return _error("Clave de API inválida o ausente.", 401)

    from backend.routes import registrar_solicitud_cuenta, validar_solicitud_cuenta

    body = request.get_json(silent=True) or {}
    limpios, errores = validar_solicitud_cuenta(body)
    if errores:
        return _error(" / ".join(errores), 400)

    solicitud_id, graduado = registrar_solicitud_cuenta(
        limpios, origen="api", ip_origen=utils.ip_cliente()
    )
    return _ok(
        {
            "id": solicitud_id,
            "estado": "pendiente",
            "coincide_con_archivo": graduado is not None,
        },
        201,
    )


@api_bp.route("/admin/usuarios", methods=["GET"])
@utils.admin_required
def admin_usuarios_get():
    pagina, por_pagina = utils.parametros_paginacion(valor_por_defecto=25, maximo=100)
    items, total = models.listar_usuarios_admin(
        busqueda=request.args.get("q") or None,
        rol=request.args.get("rol") or None,
        estado=request.args.get("estado") or None,
        tecnico_id=request.args.get("tecnico_id", type=int),
        pagina=pagina,
        por_pagina=por_pagina,
    )
    return _ok({"items": items, "total": total, "pagina": pagina, "por_pagina": por_pagina})


@api_bp.route("/admin/usuarios/<int:usuario_id>", methods=["GET"])
@utils.admin_required
def admin_usuario_get(usuario_id):
    usuario = models.obtener_usuario_por_id(usuario_id)
    if not usuario:
        return _error("Usuario no encontrado.", 404)
    usuario.pop("password_hash", None)
    return _ok(usuario)


@api_bp.route("/admin/usuarios/<int:usuario_id>", methods=["PUT"])
@utils.admin_required
@limiter.limit("30 per hour")
def admin_usuario_put(usuario_id):
    body = request.get_json(silent=True) or {}
    campos = {}
    for llave in ("nombre", "correo", "usuario", "rol", "anio_promocion", "tecnico_id"):
        if llave in body:
            campos[llave] = body[llave]

    if "correo" in campos and not utils.validar_correo(campos["correo"]):
        return _error("El correo no es válido.")
    if "rol" in campos and campos["rol"] not in ("egresado", "administrador", "institucion"):
        return _error("Rol no válido.")

    try:
        rowcount = models.actualizar_usuario_admin(usuario_id, campos)
    except mysql.connector.IntegrityError:
        return _error("Ya existe una cuenta con ese correo o usuario.", 409)

    if rowcount == 0:
        return _error("Usuario no encontrado.", 404)

    utils.encolar_tarea(
        models.registrar_bitacora, current_user.id, "usuario_editado",
        detalle=f"Editó la cuenta #{usuario_id}", ip=utils.ip_cliente(),
    )
    return _ok(models.obtener_usuario_por_id(usuario_id))


@api_bp.route("/admin/usuarios/<int:usuario_id>/estado", methods=["PATCH"])
@utils.admin_required
@limiter.limit("30 per hour")
def admin_usuario_estado(usuario_id):
    body = request.get_json(silent=True) or {}
    estado = body.get("estado")
    if estado not in ("activo", "inactivo", "pendiente"):
        return _error("Estado no válido.")

    if usuario_id == current_user.id and estado != "activo":
        return _error("No puedes desactivar tu propia cuenta.", 400)

    if models.cambiar_estado(usuario_id, estado) == 0:
        return _error("Usuario no encontrado.", 404)

    utils.encolar_tarea(
        models.registrar_bitacora, current_user.id, "usuario_estado_cambiado",
        detalle=f"Cuenta #{usuario_id} -> {estado}", ip=utils.ip_cliente(),
    )
    from backend.routes import invalidar_stats_dashboard
    invalidar_stats_dashboard()
    return _ok({"id": usuario_id, "estado": estado})


@api_bp.route("/admin/usuarios/<int:usuario_id>/reset-password", methods=["POST"])
@utils.admin_required
@limiter.limit("20 per hour")
def admin_usuario_reset_password(usuario_id):
    usuario = models.obtener_usuario_por_id(usuario_id)
    if not usuario:
        return _error("Usuario no encontrado.", 404)

    password_temporal = utils.generar_password_temporal()
    models.cambiar_password(usuario_id, utils.hash_password(password_temporal), forzar_cambio=True)
    utils.encolar_tarea(
        models.registrar_bitacora, current_user.id, "password_reseteada_por_admin",
        detalle=f"Cuenta #{usuario_id}", ip=utils.ip_cliente(),
    )
    utils.enviar_correo_async(
        usuario["correo"],
        "Tu contraseña V.I.A fue restablecida",
        f"Hola {usuario['nombre']},\n\nUn administrador restableció tu contraseña.\n"
        f"Contraseña temporal: {password_temporal}\n\nTe pedirá cambiarla en tu próximo ingreso.",
    )
    return _ok({"password_temporal": password_temporal})


@api_bp.route("/admin/usuarios/<int:usuario_id>/bitacora", methods=["GET"])
@utils.admin_required
def admin_usuario_bitacora(usuario_id):
    pagina, por_pagina = utils.parametros_paginacion(valor_por_defecto=25, maximo=100)
    return _ok(models.listar_bitacora_usuario(usuario_id, pagina=pagina, por_pagina=por_pagina))


@api_bp.route("/admin/comentarios", methods=["GET"])
@utils.admin_required
def admin_comentarios_get():
    pagina, por_pagina = utils.parametros_paginacion(valor_por_defecto=25, maximo=100)
    return _ok(models.listar_comentarios_admin(estado=request.args.get("estado"), pagina=pagina, por_pagina=por_pagina))


@api_bp.route("/admin/comentarios/<int:comentario_id>", methods=["PATCH"])
@utils.admin_required
def admin_comentario_patch(comentario_id):
    body = request.get_json(silent=True) or {}
    estado = body.get("estado")
    if estado not in ("visible", "oculto", "pendiente"):
        return _error("Estado no válido.")

    if models.moderar_comentario(comentario_id, estado) == 0:
        return _error("Comentario no encontrado.", 404)

    cache.delete_memoized(_comentarios_api_cacheados)
    from backend.perfil import _comentarios_visibles_cacheados
    cache.delete_memoized(_comentarios_visibles_cacheados)
    return _ok({"id": comentario_id, "estado": estado})


@api_bp.route("/admin/soporte", methods=["GET"])
@utils.admin_required
def admin_soporte_get():
    pagina, por_pagina = utils.parametros_paginacion(valor_por_defecto=25, maximo=100)
    items, total = models.listar_tickets_admin(estado=request.args.get("estado"), pagina=pagina, por_pagina=por_pagina)
    return _ok({"items": items, "total": total, "pagina": pagina})


@api_bp.route("/admin/soporte/<int:ticket_id>", methods=["PATCH"])
@utils.admin_required
def admin_soporte_patch(ticket_id):
    body = request.get_json(silent=True) or {}
    estado = body.get("estado")
    if estado not in ("abierto", "en_proceso", "cerrado"):
        return _error("Estado no válido.")

    if models.actualizar_estado_ticket(ticket_id, estado) == 0:
        return _error("Ticket no encontrado.", 404)
    return _ok({"id": ticket_id, "estado": estado})
