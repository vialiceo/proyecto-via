"""
Lógica de dominio del "perfil extendido": lo que cada egresado mantiene
sobre sí mismo (profesión, dónde vive, dónde estudió, edad, métodos de
contacto). Separado de perfil.py a propósito: aquí vive la validación
y el armado del view-model; perfil.py solo conecta HTTP <-> esto.
"""
from datetime import date

from backend import models, utils

TIPOS_CONTACTO_VALIDOS = {"telefono", "whatsapp", "correo_alterno", "instagram", "facebook", "linkedin", "otro"}


def construir_vista_perfil(usuario_id):
    """Junta usuarios + perfil_extendido + contactos en un solo dict
    listo para la plantilla o la respuesta JSON de la API."""
    usuario = models.obtener_usuario_por_id(usuario_id)
    extendido = models.obtener_perfil_extendido(usuario_id) or {}
    contactos = models.listar_contactos(usuario_id)

    return {
        "id": usuario["id"],
        "nombre": usuario["nombre"],
        "correo": usuario["correo"],
        "usuario": usuario["usuario"],
        "rol": usuario["rol"],
        "anio_promocion": usuario["anio_promocion"],
        "tecnico": usuario.get("tecnico_nombre"),
        "foto": usuario.get("foto"),
        "profesion": extendido.get("profesion"),
        "lugar_residencia": extendido.get("lugar_residencia"),
        "lugar_estudio": extendido.get("lugar_estudio"),
        "fecha_nacimiento": extendido.get("fecha_nacimiento"),
        "frase": extendido.get("frase"),
        "edad": utils.calcular_edad(extendido.get("fecha_nacimiento")),
        "contactos": contactos,
    }


def validar_datos_perfil(form):
    """form: dict tipo request.form. Devuelve (errores, datos_limpios)."""
    errores = []

    profesion = (form.get("profesion") or "").strip() or None
    lugar_residencia = (form.get("lugar_residencia") or "").strip() or None
    lugar_estudio = (form.get("lugar_estudio") or "").strip() or None
    fecha_nacimiento_raw = (form.get("fecha_nacimiento") or "").strip() or None
    frase = (form.get("frase") or "").strip() or None

    for etiqueta, valor in (("profesión", profesion), ("lugar de residencia", lugar_residencia), ("lugar de estudio", lugar_estudio)):
        if valor and len(valor) > 150:
            errores.append(f"El campo {etiqueta} es demasiado largo (máximo 150 caracteres).")

    if frase and len(frase) > 200:
        errores.append("La frase es demasiado larga (máximo 200 caracteres).")

    fecha_nacimiento = None
    if fecha_nacimiento_raw:
        try:
            fecha_nacimiento = date.fromisoformat(fecha_nacimiento_raw)
            if fecha_nacimiento >= date.today():
                errores.append("La fecha de nacimiento no puede ser hoy ni en el futuro.")
            if (date.today().year - fecha_nacimiento.year) > 100:
                errores.append("Revisa la fecha de nacimiento, parece incorrecta.")
        except ValueError:
            errores.append("La fecha de nacimiento no es válida.")

    datos = {
        "profesion": profesion,
        "lugar_residencia": lugar_residencia,
        "lugar_estudio": lugar_estudio,
        "fecha_nacimiento": fecha_nacimiento,
        "frase": frase,
    }
    return errores, datos


def validar_contactos(tipos, valores):
    """tipos/valores: listas paralelas que llegan del formulario (varias
    filas de contacto). Devuelve (errores, contactos_limpios)."""
    errores = []
    contactos = []
    principal_asignado = False

    for tipo, valor in zip(tipos, valores):
        valor = (valor or "").strip()
        if not valor:
            continue
        if tipo not in TIPOS_CONTACTO_VALIDOS:
            errores.append(f"Tipo de contacto no reconocido: {tipo}.")
            continue
        if len(valor) > 190:
            errores.append("Uno de los datos de contacto es demasiado largo.")
            continue
        es_principal = not principal_asignado
        principal_asignado = True
        contactos.append({"tipo": tipo, "valor": valor, "es_principal": es_principal})

    if len(contactos) > 10:
        errores.append("Máximo 10 métodos de contacto.")

    return errores, contactos


def guardar_perfil(usuario_id, datos, contactos):
    models.upsert_perfil_extendido(
        usuario_id,
        datos["profesion"],
        datos["lugar_residencia"],
        datos["lugar_estudio"],
        datos["fecha_nacimiento"],
        datos.get("frase"),
    )
    models.reemplazar_contactos(usuario_id, contactos)
    utils.encolar_tarea(models.registrar_bitacora, usuario_id, "perfil_actualizado", ip=utils.ip_cliente())
