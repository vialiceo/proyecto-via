import csv
import io

import mysql.connector

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from backend import models, utils
from backend.extensions import limiter

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

COLUMNAS_CSV_GRADUADOS = ("cedula", "nombre", "anio_promocion", "tecnico", "libro_acta")


@admin_bp.route("/")
@utils.admin_required
def dashboard():
    return redirect(url_for("public.index"))


@admin_bp.route("/usuarios")
@utils.admin_required
def usuarios():
    return redirect(url_for("public.index"))


@admin_bp.route("/usuarios/nuevo", methods=["GET", "POST"])
@utils.admin_required
@limiter.limit("20 per hour")
def usuarios_nuevo():
    tecnicos = models.listar_tecnicos_activos()

    if request.method == "POST":
        nombre = (request.form.get("nombre") or "").strip()
        cedula = utils.normalizar_cedula(request.form.get("cedula")) or None
        correo = (request.form.get("correo") or "").strip().lower()
        usuario_login = (request.form.get("usuario") or "").strip().lower()
        rol = request.form.get("rol") or "egresado"
        anio_promocion = request.form.get("anio_promocion", type=int)
        tecnico_id = request.form.get("tecnico_id", type=int) or None

        errores = []
        if not utils.texto_no_vacio(nombre, 3, 150):
            errores.append("El nombre debe tener entre 3 y 150 caracteres.")
        if cedula and not utils.validar_cedula(cedula):
            errores.append("La cédula debe tener entre 6 y 15 dígitos.")
        if not utils.validar_correo(correo):
            errores.append("El correo no es válido.")
        if not utils.texto_no_vacio(usuario_login, 3, 60):
            errores.append("El usuario debe tener entre 3 y 60 caracteres.")
        if rol not in ("egresado", "administrador", "institucion"):
            errores.append("Rol no válido.")

        if errores:
            for error in errores:
                flash(error, "error")
            return render_template("registro.html", tecnicos=tecnicos, form=request.form, active_page="principal"), 400

        graduado = models.buscar_graduado_coincidente(cedula, nombre, anio_promocion) if rol == "egresado" else None
        password_temporal = utils.generar_password_temporal()
        try:
            nuevo_id = models.crear_usuario(
                nombre,
                correo,
                usuario_login,
                utils.hash_password(password_temporal),
                rol,
                anio_promocion,
                tecnico_id,
                cedula=cedula,
                graduado_id=graduado["id"] if graduado and not graduado.get("usuario_id") else None,
            )
        except mysql.connector.IntegrityError:
            flash("Ya existe una cuenta con esa cédula, ese correo o ese usuario.", "error")
            return render_template("registro.html", tecnicos=tecnicos, form=request.form, active_page="principal"), 409

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
        from backend.routes import invalidar_stats_dashboard
        invalidar_stats_dashboard()

        flash(
            f"Cuenta creada. Usuario: {usuario_login} — contraseña temporal: {password_temporal} "
            "(anótala: solo se muestra esta vez si el correo no está configurado).",
            "success",
        )
        return redirect(url_for("public.index"))

    return render_template("registro.html", tecnicos=tecnicos, form={}, active_page="principal")


@admin_bp.route("/solicitudes-cuenta")
@utils.admin_required
def solicitudes_cuenta():
    estado = request.args.get("estado") or None
    busqueda = request.args.get("q", "").strip() or None
    pagina, por_pagina = utils.parametros_paginacion(valor_por_defecto=20, maximo=100)

    if estado not in (None, "pendiente", "aprobada", "rechazada"):
        estado = None

    solicitudes, total = models.listar_solicitudes_cuenta(
        estado=estado, busqueda=busqueda, pagina=pagina, por_pagina=por_pagina
    )

    # Para las pendientes sin coincidencia unica, buscamos los posibles graduados
    # del archivo (mismo primer nombre + primer apellido + anio) para que el admin elija.
    for s in solicitudes:
        if s["estado"] == "pendiente" and not s.get("graduado_id"):
            obligatorios = [p for p in (s.get("primer_nombre"), s.get("primer_apellido")) if p]
            s["candidatos"] = models.buscar_graduados_candidatos(
                nombre=s["nombre"], anio_promocion=s["anio_promocion"],
                obligatorios=obligatorios or None,
            )
        else:
            s["candidatos"] = []

    return render_template(
        "solicitudes_cuenta.html",
        solicitudes=solicitudes,
        total=total,
        estado=estado,
        busqueda=busqueda or "",
        pagina=pagina,
        por_pagina=por_pagina,
        pendientes=models.contar_solicitudes_cuenta_pendientes(),
        active_page="solicitudes_cuenta",
    )


@admin_bp.route("/solicitudes-cuenta/<int:solicitud_id>/aprobar", methods=["POST"])
@utils.admin_required
@limiter.limit("60 per hour")
def solicitud_cuenta_aprobar(solicitud_id):
    solicitud = models.obtener_solicitud_cuenta(solicitud_id)
    destino = redirect(url_for("admin.solicitudes_cuenta", estado=request.form.get("volver_a") or None))

    if not solicitud:
        flash("Esa solicitud no existe.", "error")
        return destino
    if solicitud["estado"] != "pendiente":
        flash(f"La solicitud #{solicitud_id} ya fue {solicitud['estado']}.", "error")
        return destino

    graduado_id = request.form.get("graduado_id", type=int) or solicitud["graduado_id"]
    crear_graduado = request.form.get("crear_graduado") == "1"

    if not graduado_id:
        if not crear_graduado:
            flash(
                f"No hay ningún graduado en el archivo que coincida con {solicitud['nombre']} "
                f"({solicitud['anio_promocion']}). Verifícalo antes de aprobar.",
                "error",
            )
            return destino
        graduado_id = models.crear_graduado(
            solicitud["cedula"],
            solicitud["nombre"],
            solicitud["anio_promocion"],
            tecnico_id=solicitud["tecnico_id"],
            observaciones=f"Alta desde la solicitud de cuenta #{solicitud_id}",
        )

    usuario_login = utils.sugerir_usuario(solicitud["nombre"], models.existe_login)
    password_temporal = utils.generar_password_temporal()

    try:
        nuevo_id = models.crear_usuario(
            solicitud["nombre"],
            solicitud["correo"],
            usuario_login,
            utils.hash_password(password_temporal),
            "egresado",
            solicitud["anio_promocion"],
            solicitud["tecnico_id"],
            cedula=solicitud["cedula"],
            graduado_id=graduado_id,
        )
    except mysql.connector.IntegrityError:
        flash("Ya existe una cuenta con esa cédula o ese correo. Revisa el listado de usuarios.", "error")
        return destino

    models.marcar_solicitud_cuenta_aprobada(solicitud_id, nuevo_id, graduado_id, current_user.id)

    utils.encolar_tarea(
        models.registrar_bitacora,
        current_user.id,
        "solicitud_cuenta_aprobada",
        detalle=f"Aprobó la solicitud #{solicitud_id} y creó la cuenta #{nuevo_id} ({usuario_login})",
        ip=utils.ip_cliente(),
    )
    utils.enviar_correo_async(
        solicitud["correo"],
        "Tu cuenta V.I.A fue aprobada",
        f"Hola {solicitud['nombre']},\n\nVerificamos tus datos contra el archivo de graduados del "
        f"Liceo Tame y tu cuenta ya está activa.\n\nUsuario: {usuario_login}\n"
        f"Contraseña temporal: {password_temporal}\n\nTe pedirá cambiarla en tu primer ingreso.",
    )
    from backend.routes import invalidar_stats_dashboard
    invalidar_stats_dashboard()

    flash(
        f"Solicitud #{solicitud_id} aprobada. Usuario: {usuario_login} — contraseña temporal: "
        f"{password_temporal} (anótala: solo se muestra esta vez si el correo no está configurado).",
        "success",
    )
    return destino


@admin_bp.route("/solicitudes-cuenta/<int:solicitud_id>/rechazar", methods=["POST"])
@utils.admin_required
@limiter.limit("60 per hour")
def solicitud_cuenta_rechazar(solicitud_id):
    destino = redirect(url_for("admin.solicitudes_cuenta", estado=request.form.get("volver_a") or None))
    motivo = (request.form.get("motivo") or "").strip()

    if not utils.texto_no_vacio(motivo, 5, 300):
        flash("Explica en pocas palabras por qué se rechaza la solicitud.", "error")
        return destino

    solicitud = models.obtener_solicitud_cuenta(solicitud_id)
    if not solicitud or solicitud["estado"] != "pendiente":
        flash("Esa solicitud ya no está pendiente.", "error")
        return destino

    models.rechazar_solicitud_cuenta(solicitud_id, motivo, current_user.id)
    utils.encolar_tarea(
        models.registrar_bitacora,
        current_user.id,
        "solicitud_cuenta_rechazada",
        detalle=f"Rechazó la solicitud #{solicitud_id}: {motivo}",
        ip=utils.ip_cliente(),
    )
    utils.enviar_correo_async(
        solicitud["correo"],
        "Sobre tu solicitud de cuenta V.I.A",
        f"Hola {solicitud['nombre']},\n\nRevisamos tu solicitud (#{solicitud_id}) y por ahora no "
        f"pudimos aprobarla.\n\nMotivo: {motivo}\n\nSi crees que es un error, escríbenos desde la "
        "sección de contacto del portal.",
    )

    flash(f"Solicitud #{solicitud_id} rechazada.", "success")
    return destino


@admin_bp.route("/graduados")
@utils.admin_required
def graduados():
    busqueda = request.args.get("q", "").strip() or None
    anio_promocion = request.args.get("anio_promocion", type=int)
    tecnico_id = request.args.get("tecnico_id", type=int)
    con_cuenta = request.args.get("con_cuenta") or None
    pagina, por_pagina = utils.parametros_paginacion(valor_por_defecto=30, maximo=100)

    if con_cuenta not in (None, "si", "no"):
        con_cuenta = None

    items, total = models.buscar_graduados(
        busqueda=busqueda,
        anio_promocion=anio_promocion,
        tecnico_id=tecnico_id,
        con_cuenta=con_cuenta,
        pagina=pagina,
        por_pagina=por_pagina,
    )

    return render_template(
        "graduados.html",
        graduados=items,
        total=total,
        resumen=models.contar_graduados(),
        promociones=models.listar_promociones_graduados(),
        tecnicos=models.listar_tecnicos_activos(),
        filtros={
            "q": busqueda or "",
            "anio_promocion": anio_promocion or "",
            "tecnico_id": tecnico_id or "",
            "con_cuenta": con_cuenta or "",
        },
        pagina=pagina,
        por_pagina=por_pagina,
        columnas_csv=COLUMNAS_CSV_GRADUADOS,
        active_page="graduados",
    )


@admin_bp.route("/graduados/nuevo", methods=["POST"])
@utils.admin_required
@limiter.limit("120 per hour")
def graduados_nuevo():
    nombre = (request.form.get("nombre") or "").strip()
    cedula = utils.normalizar_cedula(request.form.get("cedula")) or None
    anio_promocion = request.form.get("anio_promocion", type=int)
    tecnico_id = request.form.get("tecnico_id", type=int) or None
    libro_acta = (request.form.get("libro_acta") or "").strip() or None

    errores = []
    if not utils.texto_no_vacio(nombre, 5, 150):
        errores.append("El nombre debe tener entre 5 y 150 caracteres.")
    if cedula and not utils.validar_cedula(cedula):
        errores.append("La cédula debe tener entre 6 y 15 dígitos.")
    if not anio_promocion:
        errores.append("Indica el año de graduación.")

    if errores:
        for error in errores:
            flash(error, "error")
        return redirect(url_for("admin.graduados"))

    try:
        models.crear_graduado(cedula, nombre, anio_promocion, tecnico_id, libro_acta)
    except mysql.connector.IntegrityError:
        flash("Ese graduado ya está en el archivo (misma cédula, o mismo nombre y año).", "error")
        return redirect(url_for("admin.graduados"))

    flash(f"{nombre} fue añadido al archivo de graduados.", "success")
    return redirect(url_for("admin.graduados", q=nombre))


@admin_bp.route("/graduados/importar", methods=["POST"])
@utils.admin_required
@limiter.limit("10 per hour")
def graduados_importar():
    archivo = request.files.get("archivo")
    if not archivo or not archivo.filename:
        flash("Selecciona un archivo CSV.", "error")
        return redirect(url_for("admin.graduados"))
    if not archivo.filename.lower().endswith(".csv"):
        flash("El archivo debe ser un CSV.", "error")
        return redirect(url_for("admin.graduados"))

    try:
        contenido = archivo.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        flash("No se pudo leer el archivo. Guárdalo con codificación UTF-8.", "error")
        return redirect(url_for("admin.graduados"))

    lector = csv.DictReader(io.StringIO(contenido))
    if not lector.fieldnames or "nombre" not in lector.fieldnames:
        flash(f"El CSV debe tener al menos las columnas: {', '.join(COLUMNAS_CSV_GRADUADOS)}.", "error")
        return redirect(url_for("admin.graduados"))

    tecnicos_por_nombre = {t["nombre"].strip().lower(): t["id"] for t in models.listar_tecnicos_activos()}
    filas = []
    descartadas = 0

    for numero, fila in enumerate(lector, start=2):
        nombre = (fila.get("nombre") or "").strip()
        try:
            anio = int((fila.get("anio_promocion") or "").strip())
        except (TypeError, ValueError):
            anio = 0
        if not utils.texto_no_vacio(nombre, 5, 150) or not anio:
            descartadas += 1
            continue

        cedula = utils.normalizar_cedula(fila.get("cedula")) or None
        if cedula and not utils.validar_cedula(cedula):
            descartadas += 1
            continue

        filas.append({
            "cedula": cedula,
            "nombre": nombre,
            "anio_promocion": anio,
            "tecnico_id": tecnicos_por_nombre.get((fila.get("tecnico") or "").strip().lower()),
            "libro_acta": (fila.get("libro_acta") or "").strip() or None,
        })

        if len(filas) >= 5000:
            break

    if not filas:
        flash(f"No se importó ninguna fila válida. Se descartaron {descartadas}.", "error")
        return redirect(url_for("admin.graduados"))

    models.importar_graduados(filas)
    utils.encolar_tarea(
        models.registrar_bitacora,
        current_user.id,
        "graduados_importados",
        detalle=f"Importó {len(filas)} graduados desde {archivo.filename}",
        ip=utils.ip_cliente(),
    )

    mensaje = f"Se importaron {len(filas)} graduados."
    if descartadas:
        mensaje += f" Se descartaron {descartadas} filas por datos incompletos o inválidos."
    flash(mensaje, "success")
    return redirect(url_for("admin.graduados"))


ESTADOS_TICKET = ("abierto", "en_proceso", "cerrado")


@admin_bp.route("/soporte")
@utils.admin_required
def soporte():
    estado = request.args.get("estado")
    if estado not in ESTADOS_TICKET:
        estado = None

    busqueda = (request.args.get("q") or "").strip() or None
    pagina, por_pagina = utils.parametros_paginacion(valor_por_defecto=15, maximo=50)

    tickets, total = models.listar_tickets_admin(
        estado=estado, busqueda=busqueda, pagina=pagina, por_pagina=por_pagina
    )

    return render_template(
        "soporte.html",
        tickets=tickets,
        total=total,
        estado=estado,
        busqueda=busqueda or "",
        pagina=pagina,
        por_pagina=por_pagina,
        conteos=models.contar_tickets_por_estado(),
        active_page="soporte",
    )


def _volver_a_soporte():
    return redirect(
        url_for("admin.soporte", estado=request.form.get("volver_a") or None)
    )


@admin_bp.route("/soporte/<int:ticket_id>/estado", methods=["POST"])
@utils.admin_required
def soporte_estado(ticket_id):
    estado = request.form.get("estado")
    if estado not in ESTADOS_TICKET:
        flash("Estado no válido.", "error")
        return _volver_a_soporte()

    if not models.obtener_ticket(ticket_id):
        flash(f"El ticket #{ticket_id} no existe.", "error")
        return _volver_a_soporte()

    models.actualizar_estado_ticket(ticket_id, estado)
    utils.encolar_tarea(
        models.registrar_bitacora,
        current_user.id,
        "ticket_estado",
        detalle=f"Ticket #{ticket_id} pasó a {estado}",
        ip=utils.ip_cliente(),
    )
    flash(f"Ticket #{ticket_id} marcado como {estado.replace('_', ' ')}.", "success")
    return _volver_a_soporte()


@admin_bp.route("/soporte/<int:ticket_id>/responder", methods=["POST"])
@utils.admin_required
@limiter.limit("60 per hour")
def soporte_responder(ticket_id):
    ticket = models.obtener_ticket(ticket_id)
    if not ticket:
        flash(f"El ticket #{ticket_id} no existe.", "error")
        return _volver_a_soporte()

    if ticket["estado"] == "cerrado":
        flash(f"El ticket #{ticket_id} ya fue respondido y cerrado.", "error")
        return _volver_a_soporte()

    respuesta = (request.form.get("respuesta") or "").strip()
    if not utils.texto_no_vacio(respuesta, 10, 2000):
        flash("La respuesta debe tener entre 10 y 2000 caracteres.", "error")
        return _volver_a_soporte()

    models.responder_ticket(ticket_id, respuesta, current_user.id)

    utils.enviar_correo_async(
        ticket["correo"],
        f"Respuesta a tu solicitud de soporte #{ticket_id}",
        f"Hola {ticket['nombre']}:\n\n"
        f"Recibimos tu mensaje sobre \"{ticket['asunto']}\" y esta es nuestra respuesta:\n\n"
        f"{respuesta}\n\n"
        "Si necesitas algo más, respóndenos desde la página de Contacto.\n\n"
        "Equipo V.I.A — Institución Educativa Liceo Tame",
    )

    utils.encolar_tarea(
        models.registrar_bitacora,
        current_user.id,
        "ticket_respondido",
        detalle=f"Ticket #{ticket_id} respondido a {ticket['correo']}",
        ip=utils.ip_cliente(),
    )

    flash(f"Respuesta enviada a {ticket['correo']}. El ticket #{ticket_id} quedó cerrado.", "success")
    return _volver_a_soporte()
