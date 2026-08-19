from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from backend import models, utils
from backend.extensions import cache, limiter

public_bp = Blueprint("public", __name__)

ANIO_PROMOCION_MIN = 1967


@public_bp.route("/")
def index():
    if not current_user.is_authenticated:
        # Portada publica: quien llega sin sesion debe entender que es V.I.A
        # y como pedir una cuenta, no aterrizar en la pagina de Ayuda.
        return render_template(
            "portada.html",
            promociones_recientes=_promociones_recientes_publicas(),
            stats=_stats_publicas(),
        )

    if current_user.rol == "administrador":
        busqueda = request.args.get("q", "").strip() or None
        rol = request.args.get("rol") or None
        estado = request.args.get("estado") or None
        tecnico_id = request.args.get("tecnico_id", type=int)
        pagina, por_pagina = utils.parametros_paginacion(valor_por_defecto=10, maximo=100)

        usuarios, total_usuarios = models.listar_usuarios_admin(
            busqueda=busqueda, rol=rol, estado=estado, tecnico_id=tecnico_id, pagina=pagina, por_pagina=por_pagina
        )
        _, total_solicitudes_abiertas = models.listar_solicitudes_admin(estado="pendiente", pagina=1, por_pagina=1)

        return render_template(
            "index.html",
            stats=_stats_dashboard_cacheadas(),
            total_solicitudes_abiertas=total_solicitudes_abiertas,
            total_solicitudes_cuenta=models.contar_solicitudes_cuenta_pendientes(),
            total_tickets_abiertos=models.contar_tickets_abiertos(),
            usuarios=usuarios,
            total_usuarios=total_usuarios,
            pagina=pagina,
            por_pagina=por_pagina,
            tecnicos=models.listar_tecnicos_activos(),
            filtros={"q": busqueda or "", "rol": rol or "", "estado": estado or "", "tecnico_id": tecnico_id or ""},
        )

    return render_template("index.html", promociones_recientes=_promociones_recientes_cacheadas())


@cache.memoize(timeout=600)
def _promociones_recientes_publicas():
    """La portada la ve gente sin cuenta y es la pagina mas visitada:
    10 minutos de cache evitan repetir la misma consulta en cada visita."""
    try:
        return models.listar_promociones_recientes(limite=4)
    except Exception:
        # La portada nunca debe caerse por la base: sin datos se muestra igual.
        return []


@cache.memoize(timeout=600)
def _stats_publicas():
    try:
        return models.contar_publicas()
    except Exception:
        return {}


@cache.memoize(timeout=180)
def _promociones_recientes_cacheadas():
    return models.listar_promociones_recientes(limite=4)


@cache.memoize(timeout=120)
def _stats_dashboard_cacheadas():
    return models.contar_usuarios_por_estado()


def invalidar_stats_dashboard():
    cache.delete_memoized(_stats_dashboard_cacheadas)


@public_bp.route("/ayuda")
def ayuda():
    return render_template("ayuda.html")


@public_bp.route("/aviso-legal")
def aviso_legal():
    return render_template("aviso_legal.html")


def validar_solicitud_cuenta(datos):
    cedula = utils.normalizar_cedula(datos.get("cedula"))
    nombre = (datos.get("nombre") or "").strip()
    correo = (datos.get("correo") or "").strip().lower()
    telefono = (datos.get("telefono") or "").strip() or None
    mensaje = (datos.get("mensaje") or "").strip() or None

    try:
        anio_promocion = int(datos.get("anio_promocion") or 0)
    except (TypeError, ValueError):
        anio_promocion = 0
    try:
        tecnico_id = int(datos.get("tecnico_id")) or None
    except (TypeError, ValueError):
        tecnico_id = None

    errores = []
    if not utils.validar_cedula(cedula):
        errores.append("La cédula debe tener entre 6 y 15 dígitos.")
    if not utils.texto_no_vacio(nombre, 5, 150):
        errores.append("Escribe tu nombre completo tal como aparece en el acta de grado.")
    if not utils.validar_correo(correo):
        errores.append("El correo no es válido.")
    if not ANIO_PROMOCION_MIN <= anio_promocion <= date.today().year:
        errores.append(f"El año de graduación debe estar entre {ANIO_PROMOCION_MIN} y {date.today().year}.")
    if telefono and len(telefono) > 40:
        errores.append("El teléfono es demasiado largo.")
    if mensaje and len(mensaje) > 500:
        errores.append("El mensaje no puede superar los 500 caracteres.")

    if errores:
        return None, errores

    if models.existe_cuenta_con(cedula, correo):
        errores.append("Ya existe una cuenta con esa cédula o ese correo. Usa 'Recuperar contraseña' si no puedes entrar.")
    elif models.existe_solicitud_cuenta_pendiente(cedula, correo):
        errores.append("Ya tienes una solicitud en revisión. Te avisaremos por correo cuando sea aprobada.")

    if errores:
        return None, errores

    return {
        "cedula": cedula,
        "nombre": nombre,
        "correo": correo,
        "telefono": telefono,
        "anio_promocion": anio_promocion,
        "tecnico_id": tecnico_id,
        "mensaje": mensaje,
    }, []


def registrar_solicitud_cuenta(limpios, origen="formulario", ip_origen=None):
    graduado = models.buscar_graduado_coincidente(
        cedula=limpios["cedula"],
        nombre=limpios["nombre"],
        anio_promocion=limpios["anio_promocion"],
    )
    solicitud_id = models.crear_solicitud_cuenta(
        cedula=limpios["cedula"],
        nombre=limpios["nombre"],
        correo=limpios["correo"],
        anio_promocion=limpios["anio_promocion"],
        telefono=limpios["telefono"],
        tecnico_id=limpios["tecnico_id"] or (graduado["tecnico_id"] if graduado else None),
        mensaje=limpios["mensaje"],
        graduado_id=graduado["id"] if graduado else None,
        origen=origen,
        ip_origen=ip_origen,
    )
    utils.enviar_correo_async(
        limpios["correo"],
        "Recibimos tu solicitud de cuenta V.I.A",
        f"Hola {limpios['nombre']},\n\nRecibimos tu solicitud para acceder al portal de egresados "
        f"del Liceo Tame (radicado #{solicitud_id}).\n\nLa institución la revisará contra el archivo de "
        "graduados y te enviaremos tus datos de acceso cuando sea aprobada.",
    )
    return solicitud_id, graduado


@public_bp.route("/solicitar-cuenta", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def solicitar_cuenta():
    tecnicos = models.listar_tecnicos_activos()

    if request.method == "POST":
        limpios, errores = validar_solicitud_cuenta(request.form)
        if errores:
            for error in errores:
                flash(error, "error")
            return render_template(
                "solicitar_cuenta.html", tecnicos=tecnicos, form=request.form, anio_min=ANIO_PROMOCION_MIN
            ), 400

        solicitud_id, _ = registrar_solicitud_cuenta(
            limpios, origen="formulario", ip_origen=utils.ip_cliente()
        )
        flash(
            f"Solicitud recibida (radicado #{solicitud_id}). La institución la revisará y te "
            "escribiremos al correo que registraste.",
            "success",
        )
        return redirect(url_for("public.solicitar_cuenta"))

    return render_template(
        "solicitar_cuenta.html", tecnicos=tecnicos, form={}, anio_min=ANIO_PROMOCION_MIN
    )


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
