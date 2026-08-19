import hashlib
import logging
import os
import re
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from functools import wraps

from flask import abort, current_app, flash, redirect, request, url_for
from flask_login import current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

logger = logging.getLogger("via")

CORREO_SIMULADO = """CORREO SIMULADO (no se envio: falta MAIL_SERVER en .env)
  De:     {remitente}
  Para:   {destinatario}
  Asunto: {asunto}
  ----------------------------------------
{cuerpo}
  ----------------------------------------"""



def hash_password(password_plano):
    return generate_password_hash(password_plano)


def verificar_password(password_hash, password_plano):
    return check_password_hash(password_hash, password_plano)


def generar_password_temporal():
    return secrets.token_urlsafe(9)


def generar_token(minutos_validez=30):
    token_plano = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token_plano.encode("utf-8")).hexdigest()
    expira_en = datetime.utcnow() + timedelta(minutes=minutos_validez)
    return token_plano, token_hash, expira_en


def hash_token(token_plano):
    return hashlib.sha256(token_plano.encode("utf-8")).hexdigest()


def roles_required(*roles_permitidos):
    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(*args, **kwargs):
            if current_user.rol not in roles_permitidos:
                if request.path.startswith("/api/"):
                    abort(403)
                flash("No tienes permiso para acceder a esa sección.", "error")
                return redirect(url_for("public.index"))
            return vista(*args, **kwargs)

        return envoltura

    return decorador


def admin_required(vista):
    return roles_required("administrador")(vista)


_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="via-async")


def encolar_tarea(fn, *args, **kwargs):
    app = current_app._get_current_object()

    def _envoltura():
        with app.app_context():
            try:
                fn(*args, **kwargs)
            except Exception:
                logger.exception("Falló una tarea asíncrona (%s)", getattr(fn, "__name__", fn))

    _executor.submit(_envoltura)


def enviar_correo_async(destinatario, asunto, cuerpo_texto):
    """Manda el correo en segundo plano para no dejar esperando al usuario.

    Sin `MAIL_SERVER` configurado no falla: escribe el correo completo en
    `logs/correos.log`, que hace las veces de bandeja de salida. Asi se puede
    ver una contrasena temporal o una respuesta de soporte sin montar SMTP.
    """

    def _enviar():
        remitente = current_app.config.get("MAIL_DEFAULT_SENDER")

        if not current_app.config.get("MAIL_SERVER"):
            logger.info(
                CORREO_SIMULADO.format(
                    remitente=remitente,
                    destinatario=destinatario,
                    asunto=asunto,
                    cuerpo=cuerpo_texto,
                ),
                extra={"es_correo": True},
            )
            return

        from flask_mail import Message

        from backend.extensions import mail

        mensaje = Message(asunto, recipients=[destinatario], body=cuerpo_texto)
        mail.send(mensaje)
        logger.info(
            "CORREO ENVIADO  para=%s  asunto=%s",
            destinatario,
            asunto,
            extra={"es_correo": True},
        )

    encolar_tarea(_enviar)


def parametros_paginacion(valor_por_defecto=25, maximo=100):
    try:
        pagina = max(int(request.args.get("pagina", 1)), 1)
    except (TypeError, ValueError):
        pagina = 1
    try:
        por_pagina = int(request.args.get("por_pagina", valor_por_defecto))
    except (TypeError, ValueError):
        por_pagina = valor_por_defecto
    por_pagina = min(max(por_pagina, 1), maximo)
    return pagina, por_pagina


_CORREO_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_correo(valor):
    return bool(valor) and bool(_CORREO_RE.match(valor.strip()))


_CEDULA_RE = re.compile(r"^\d{6,15}$")


def normalizar_cedula(valor):
    if not valor:
        return ""
    return re.sub(r"[^\d]", "", str(valor))


def validar_cedula(valor):
    return bool(_CEDULA_RE.match(valor or ""))


_ACENTOS = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")


def sugerir_usuario(nombre, existe_login):
    partes = [p for p in nombre.translate(_ACENTOS).lower().split() if p.isalpha()]
    if not partes:
        base = "egresado"
    elif len(partes) == 1:
        base = partes[0]
    else:
        base = f"{partes[0][0]}{partes[1]}"
    base = re.sub(r"[^a-z0-9]", "", base)[:50] or "egresado"

    candidato = base
    sufijo = 1
    while existe_login(candidato):
        sufijo += 1
        candidato = f"{base}{sufijo}"[:60]
    return candidato


def texto_no_vacio(valor, longitud_min=1, longitud_max=1000):
    if valor is None:
        return False
    valor = valor.strip()
    return longitud_min <= len(valor) <= longitud_max


def calcular_edad(fecha_nacimiento):
    if not fecha_nacimiento:
        return None
    if isinstance(fecha_nacimiento, str):
        fecha_nacimiento = date.fromisoformat(fecha_nacimiento)
    elif isinstance(fecha_nacimiento, datetime):
        fecha_nacimiento = fecha_nacimiento.date()
    hoy = date.today()
    return hoy.year - fecha_nacimiento.year - (
        (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
    )


def extension_permitida(nombre_archivo):
    if "." not in nombre_archivo:
        return False
    ext = nombre_archivo.rsplit(".", 1)[1].lower()
    return ext in current_app.config["EXTENSIONES_FOTO_PERMITIDAS"]


def nombre_archivo_seguro(usuario_id, nombre_original):
    ext = nombre_original.rsplit(".", 1)[1].lower()
    return secure_filename(f"usuario_{usuario_id}_{secrets.token_hex(6)}.{ext}")


def es_imagen_real(stream):
    """Mira los primeros bytes del archivo, no el nombre.

    Cambiarle la extensión a un archivo es trivial; cambiarle la cabecera no.
    Deja el cursor donde estaba para que después se pueda guardar completo.
    """
    posicion = stream.tell()
    cabecera = stream.read(12)
    stream.seek(posicion)

    if cabecera.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if cabecera.startswith(b"\xff\xd8\xff"):
        return True
    if cabecera[:4] == b"RIFF" and cabecera[8:12] == b"WEBP":
        return True
    return False


def borrar_archivo_subido(ruta_publica):
    """Borra la foto anterior para que la carpeta de subidas no crezca sin control."""
    if not ruta_publica or not ruta_publica.startswith("/static/uploads/"):
        return
    nombre = os.path.basename(ruta_publica)
    carpeta = os.path.join(current_app.root_path, current_app.config["UPLOAD_FOLDER"])
    destino = os.path.join(carpeta, nombre)
    if os.path.commonpath([os.path.abspath(destino), os.path.abspath(carpeta)]) != os.path.abspath(carpeta):
        return
    try:
        os.remove(destino)
    except OSError:
        pass


def ip_cliente():
    return request.headers.get("X-Forwarded-For", request.remote_addr) or "desconocida"


def redireccion_segura(destino, por_defecto):
    if destino and destino.startswith("/") and not destino.startswith(("//", "/\\")):
        return destino
    return por_defecto
