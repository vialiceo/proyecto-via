import hashlib
import logging
import os
import re
import base64
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from functools import wraps

from flask import abort, current_app, flash, redirect, request, url_for
from flask_login import current_user, login_required
from cryptography.hazmat.primitives.ciphers.aead import AESSIV
from markupsafe import escape
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


def _cuerpo_html(asunto, cuerpo_texto):
    """Envuelve el texto del correo en una plantilla HTML con la identidad del
    Liceo (verde + dorado). El texto se escapa y se respeta en párrafos, así que
    sirve igual para una contraseña temporal que para un aviso largo. Usa estilos
    en línea y tablas porque es lo único que los clientes de correo renderizan
    de forma fiable."""
    bloques = [b.strip() for b in cuerpo_texto.split("\n\n") if b.strip()]
    parrafos = "".join(
        '<p style="margin:0 0 16px;line-height:1.6;color:#333333;font-size:15px;">'
        + str(escape(b)).replace("\n", "<br>")
        + "</p>"
        for b in bloques
    ) or '<p style="margin:0;color:#333333;font-size:15px;">&nbsp;</p>'

    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#eef2ea;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef2ea;padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 14px rgba(13,35,24,0.10);font-family:'Segoe UI',Roboto,Arial,sans-serif;">
        <tr><td style="background-color:#1a3d2b;background-image:linear-gradient(135deg,#0d2318,#1a3d2b);padding:26px 32px;">
          <div style="font-family:Georgia,'Times New Roman',serif;font-size:22px;font-weight:bold;color:#ffffff;letter-spacing:1px;">V.I.A</div>
          <div style="font-size:11px;color:#c9a227;letter-spacing:2px;text-transform:uppercase;margin-top:4px;">Liceo Tame &middot; Vinculaci&oacute;n Integral de Alumnos</div>
        </td></tr>
        <tr><td style="height:4px;background:#c9a227;font-size:0;line-height:0;">&nbsp;</td></tr>
        <tr><td style="padding:32px;">
          <h1 style="margin:0 0 20px;font-size:18px;color:#0d2318;font-family:Georgia,serif;font-weight:bold;">{str(escape(asunto))}</h1>
          {parrafos}
        </td></tr>
        <tr><td style="padding:18px 32px;background:#f4f6f2;border-top:1px solid #e3e8e0;">
          <p style="margin:0;font-size:12px;color:#8a9a90;line-height:1.5;">
            Mensaje autom&aacute;tico del sistema V.I.A de la Instituci&oacute;n Educativa Liceo Tame. Por favor no respondas a este correo.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def enviar_correo_sync(destinatario, asunto, cuerpo_texto):
    """Envía un correo AQUÍ MISMO (sin hilo). La usan los scripts como
    enviar_recordatorios.py, que terminan enseguida y no pueden dejar el envío
    en un hilo en segundo plano.

    Sin `MAIL_SERVER` configurado no falla: escribe el correo completo en
    `logs/correos.log`, que hace las veces de bandeja de salida.
    """
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

    """
    Se manda texto plano (body) Y una versión HTML con la identidad del Liceo.
    El cliente de correo muestra el HTML; si no puede, cae al texto plano.
    """
    mensaje = Message(
        asunto,
        recipients=[destinatario],
        body=cuerpo_texto,
        html=_cuerpo_html(asunto, cuerpo_texto),
    )
    mail.send(mensaje)
    logger.info(
        "CORREO ENVIADO  para=%s  asunto=%s",
        destinatario,
        asunto,
        extra={"es_correo": True},
    )


def enviar_correo_async(destinatario, asunto, cuerpo_texto):
    """Manda el correo en segundo plano para no dejar esperando al usuario.
    Delega el envío en `enviar_correo_sync` dentro de una tarea del pool."""
    encolar_tarea(enviar_correo_sync, destinatario, asunto, cuerpo_texto)


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


def _clave_cedula():
    b64 = current_app.config.get("CEDULA_ENC_KEY")
    return base64.b64decode(b64) if b64 else None


def cifrar_cedula(cedula):
    """Cifra la cedula de forma DETERMINISTA (AES-SIV): el mismo numero da
    siempre el mismo texto cifrado, asi se conservan la unicidad, el login por
    cedula y el cruce con el archivo de graduados. Devuelve None si no hay
    cedula; y el valor tal cual si no hay clave (modo desarrollo)."""
    cedula = (cedula or "").strip()
    if not cedula:
        return None
    clave = _clave_cedula()
    if not clave:
        return cedula
    token = AESSIV(clave).encrypt(cedula.encode("utf-8"), [])
    return base64.b64encode(token).decode("ascii")


def descifrar_cedula(token):
    """Devuelve la cedula en claro. Si el valor no esta cifrado (dato viejo) o
    no hay clave configurada, lo devuelve tal cual."""
    if not token:
        return None
    clave = _clave_cedula()
    if not clave:
        return token
    try:
        return AESSIV(clave).decrypt(base64.b64decode(token), []).decode("utf-8")
    except Exception:
        return token


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
    carpeta = os.path.join(current_app.static_folder, "uploads", "perfiles")
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
