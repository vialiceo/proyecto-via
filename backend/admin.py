import mysql.connector

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from backend import models, utils
from backend.extensions import cache, limiter

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@utils.admin_required
def dashboard():
    stats = _stats_dashboard_cacheadas()
    tickets_abiertos, _ = models.listar_tickets_admin(estado="abierto", pagina=1, por_pagina=5)
    comentarios_pendientes = models.listar_comentarios_admin(estado="pendiente", pagina=1, por_pagina=5)
    return render_template(
        "admin.html",
        stats=stats,
        tickets_abiertos=tickets_abiertos,
        comentarios_pendientes=comentarios_pendientes,
        active_page="admin",
    )


@cache.memoize(timeout=120)
def _stats_dashboard_cacheadas():
    return models.contar_usuarios_por_estado()


def _invalidar_stats():
    cache.delete_memoized(_stats_dashboard_cacheadas)


@admin_bp.route("/usuarios")
@utils.admin_required
def usuarios():
    busqueda = request.args.get("q", "").strip() or None
    rol = request.args.get("rol") or None
    estado = request.args.get("estado") or None
    tecnico_id = request.args.get("tecnico_id", type=int)
    pagina, por_pagina = utils.parametros_paginacion(valor_por_defecto=25, maximo=100)

    items, total = models.listar_usuarios_admin(
        busqueda=busqueda, rol=rol, estado=estado, tecnico_id=tecnico_id, pagina=pagina, por_pagina=por_pagina
    )
    tecnicos = models.listar_tecnicos_activos()

    return render_template(
        "perfiles.html",
        usuarios=items,
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
        tecnicos=tecnicos,
        filtros={"q": busqueda or "", "rol": rol or "", "estado": estado or "", "tecnico_id": tecnico_id or ""},
        active_page="admin",
    )


@admin_bp.route("/usuarios/nuevo", methods=["GET", "POST"])
@utils.admin_required
@limiter.limit("20 per hour")
def usuarios_nuevo():
    tecnicos = models.listar_tecnicos_activos()

    if request.method == "POST":
        nombre = (request.form.get("nombre") or "").strip()
        correo = (request.form.get("correo") or "").strip().lower()
        usuario_login = (request.form.get("usuario") or "").strip().lower()
        rol = request.form.get("rol") or "egresado"
        anio_promocion = request.form.get("anio_promocion", type=int)
        tecnico_id = request.form.get("tecnico_id", type=int) or None

        errores = []
        if not utils.texto_no_vacio(nombre, 3, 150):
            errores.append("El nombre debe tener entre 3 y 150 caracteres.")
        if not utils.validar_correo(correo):
            errores.append("El correo no es válido.")
        if not utils.texto_no_vacio(usuario_login, 3, 60):
            errores.append("El usuario debe tener entre 3 y 60 caracteres.")
        if rol not in ("egresado", "administrador", "institucion"):
            errores.append("Rol no válido.")

        if errores:
            for error in errores:
                flash(error, "error")
            return render_template("registro.html", tecnicos=tecnicos, form=request.form, active_page="admin"), 400

        password_temporal = utils.generar_password_temporal()
        try:
            nuevo_id = models.crear_usuario(
                nombre, correo, usuario_login, utils.hash_password(password_temporal), rol, anio_promocion, tecnico_id
            )
        except mysql.connector.IntegrityError:
            flash("Ya existe una cuenta con ese correo o usuario.", "error")
            return render_template("registro.html", tecnicos=tecnicos, form=request.form, active_page="admin"), 409

        utils.encolar_tarea(
            models.registrar_bitacora,
            current_user.id,
            "usuario_creado",
            detalle=f"Creó la cuenta #{nuevo_id} ({usuario_login})",
            ip=utils.ip_cliente(),
        )
        utils.enviar_correo_async(
            correo,
            "Tu cuenta V.I.A ya está lista",
            f"Hola {nombre},\n\nTu cuenta fue creada.\nUsuario: {usuario_login}\nContraseña temporal: {password_temporal}\n\n"
            "Te pedirá cambiarla en tu primer ingreso.",
        )
        _invalidar_stats()

        flash(
            f"Cuenta creada. Usuario: {usuario_login} — contraseña temporal: {password_temporal} "
            "(anótala: solo se muestra esta vez si el correo no está configurado).",
            "success",
        )
        return redirect(url_for("admin.usuarios"))

    return render_template("registro.html", tecnicos=tecnicos, form={}, active_page="admin")
