from backend import db, utils


def listar_tecnicos_activos():
    return db.fetch_all(
        "SELECT id, nombre FROM tecnicos WHERE activo = 1 ORDER BY nombre"
    )


_CAMPOS_USUARIO_ADMIN = {"nombre", "cedula", "correo", "usuario", "rol", "estado", "anio_promocion", "tecnico_id"}


def obtener_usuario_por_id(usuario_id):
    fila = db.fetch_one(
        """SELECT u.*, t.nombre AS tecnico_nombre
           FROM usuarios u LEFT JOIN tecnicos t ON t.id = u.tecnico_id
           WHERE u.id = %s""",
        (usuario_id,),
    )
    if fila and fila.get("cedula"):
        fila["cedula"] = utils.descifrar_cedula(fila["cedula"])
    return fila


def obtener_usuario_por_login(identificador):
    """
    La cedula esta cifrada: se compara con la version cifrada del
    identificador (si no es numerico, cifrar_cedula da None y no casa).
    """
    cedula_cif = utils.cifrar_cedula(utils.normalizar_cedula(identificador))
    fila = db.fetch_one(
        "SELECT * FROM usuarios WHERE correo = %s OR usuario = %s OR cedula = %s LIMIT 1",
        (identificador, identificador, cedula_cif),
    )
    if fila and fila.get("cedula"):
        fila["cedula"] = utils.descifrar_cedula(fila["cedula"])
    return fila


def existe_login(usuario):
    return db.fetch_one("SELECT id FROM usuarios WHERE usuario = %s", (usuario,)) is not None


def crear_usuario(
    nombre,
    correo,
    usuario,
    password_hash,
    rol,
    anio_promocion=None,
    tecnico_id=None,
    cedula=None,
    graduado_id=None,
):
    lastrowid, _ = db.execute(
        """INSERT INTO usuarios
             (cedula, graduado_id, nombre, correo, usuario, password_hash, rol, estado,
              anio_promocion, tecnico_id, forzar_cambio_password)
           VALUES (%s, %s, %s, %s, %s, %s, %s, 'activo', %s, %s, 1)""",
        (utils.cifrar_cedula(cedula), graduado_id, nombre, correo, usuario, password_hash, rol, anio_promocion, tecnico_id),
    )
    return lastrowid


def actualizar_usuario_admin(usuario_id, campos: dict):
    campos = {k: v for k, v in campos.items() if k in _CAMPOS_USUARIO_ADMIN}
    if not campos:
        return 0
    if "cedula" in campos:
        campos["cedula"] = utils.cifrar_cedula(campos["cedula"])
    set_clause = ", ".join(f"{campo} = %s" for campo in campos)
    _, rowcount = db.execute(
        f"UPDATE usuarios SET {set_clause} WHERE id = %s",
        (*campos.values(), usuario_id),
    )
    return rowcount


def cambiar_password(usuario_id, password_hash, forzar_cambio=False):
    db.execute(
        "UPDATE usuarios SET password_hash = %s, forzar_cambio_password = %s WHERE id = %s",
        (password_hash, int(forzar_cambio), usuario_id),
    )


def actualizar_foto(usuario_id, ruta_foto):
    db.execute("UPDATE usuarios SET foto = %s WHERE id = %s", (ruta_foto, usuario_id))


def correo_ocupado_por_otro(correo, usuario_id):
    """El correo es UNIQUE: hay que comprobarlo antes de intentar el UPDATE
    para poder dar un mensaje claro en vez de un error 1062 de MySQL."""
    return db.fetch_one(
        "SELECT id FROM usuarios WHERE correo = %s AND id <> %s LIMIT 1",
        (correo, usuario_id),
    ) is not None


def actualizar_correo(usuario_id, correo):
    _, rowcount = db.execute(
        "UPDATE usuarios SET correo = %s WHERE id = %s", (correo, usuario_id)
    )
    return rowcount


def cambiar_estado(usuario_id, estado):
    _, rowcount = db.execute(
        "UPDATE usuarios SET estado = %s WHERE id = %s", (estado, usuario_id)
    )
    return rowcount


def registrar_login(usuario_id):
    db.execute("UPDATE usuarios SET ultimo_login = NOW() WHERE id = %s", (usuario_id,))


def listar_usuarios_admin(busqueda=None, rol=None, estado=None, tecnico_id=None, pagina=1, por_pagina=25):
    condiciones = []
    parametros = []

    if busqueda:
        comodin = f"%{busqueda}%"
        cedula_cif = utils.cifrar_cedula(utils.normalizar_cedula(busqueda))
        if cedula_cif:
            condiciones.append("(u.nombre LIKE %s OR u.correo LIKE %s OR u.usuario LIKE %s OR u.cedula = %s)")
            parametros += [comodin, comodin, comodin, cedula_cif]
        else:
            condiciones.append("(u.nombre LIKE %s OR u.correo LIKE %s OR u.usuario LIKE %s)")
            parametros += [comodin, comodin, comodin]
    if rol:
        condiciones.append("u.rol = %s")
        parametros.append(rol)
    if estado:
        condiciones.append("u.estado = %s")
        parametros.append(estado)
    if tecnico_id:
        condiciones.append("u.tecnico_id = %s")
        parametros.append(tecnico_id)

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    offset = max(pagina - 1, 0) * por_pagina

    items = db.fetch_all(
        f"""SELECT u.id, u.cedula, u.nombre, u.correo, u.usuario, u.rol, u.estado,
                   u.anio_promocion, u.foto, u.destacado,
                   t.nombre AS tecnico_nombre, u.ultimo_login, u.creado_en,
                   pe.profesion, pe.lugar_residencia, pe.lugar_estudio, pe.frase
            FROM usuarios u
            LEFT JOIN tecnicos t ON t.id = u.tecnico_id
            LEFT JOIN perfil_extendido pe ON pe.usuario_id = u.id
            {where}
            ORDER BY u.creado_en DESC
            LIMIT %s OFFSET %s""",
        (*parametros, int(por_pagina), int(offset)),
    )
    for _it in items:
        if _it.get("cedula"):
            _it["cedula"] = utils.descifrar_cedula(_it["cedula"])
    total = db.fetch_one(
        f"SELECT COUNT(*) AS total FROM usuarios u {where}", tuple(parametros)
    )["total"]
    return items, total


def contar_publicas():
    """Cifras para la portada. Nada sensible: totales, no personas."""
    fila = db.fetch_one(
        """SELECT
             (SELECT COUNT(*) FROM graduados)                              AS graduados,
             (SELECT COUNT(DISTINCT anio_promocion) FROM graduados)        AS promociones,
             (SELECT COUNT(*) FROM usuarios WHERE estado = 'activo')       AS egresados_activos,
             (SELECT MIN(anio_promocion) FROM graduados)                   AS primera_promocion"""
    )
    return fila or {}


def contar_usuarios_por_estado():
    filas = db.fetch_all("SELECT estado, COUNT(*) AS total FROM usuarios GROUP BY estado")
    return {fila["estado"]: fila["total"] for fila in filas}


def listar_promociones_recientes(limite=4):
    return db.fetch_all(
        """SELECT
             u.anio_promocion,
             COUNT(*) AS total_egresados,
             MAX(GREATEST(u.creado_en, u.actualizado_en, COALESCE(pe.actualizado_en, u.creado_en))) AS ultima_actividad
           FROM usuarios u
           LEFT JOIN perfil_extendido pe ON pe.usuario_id = u.id
           WHERE u.rol = 'egresado' AND u.estado = 'activo' AND u.anio_promocion IS NOT NULL
           GROUP BY u.anio_promocion
           ORDER BY ultima_actividad DESC
           LIMIT %s""",
        (int(limite),),
    )


def listar_todas_promociones():
    """Todas las promociones del catálogo (1967 en adelante), tenga o no
    egresados registrados. Así la página "Ver promociones" muestra la línea de
    tiempo completa del Liceo. El conteo de egresados sale del LEFT JOIN.

    Se conservan los nombres de columna (anio_promocion, total_egresados) para
    que la plantilla promocion.html no cambie."""
    return db.fetch_all(
        """SELECT pr.anio AS anio_promocion,
                  COUNT(u.id) AS total_egresados
           FROM promociones pr
           LEFT JOIN usuarios u
             ON u.anio_promocion = pr.anio
            AND u.rol = 'egresado' AND u.estado = 'activo'
           WHERE pr.activa = 1
           GROUP BY pr.anio
           ORDER BY pr.anio DESC"""
    )


def listar_egresados_por_promocion(anio, pagina=1, por_pagina=60):
    offset = max(pagina - 1, 0) * por_pagina
    return db.fetch_all(
        """SELECT u.id, u.nombre, u.foto, u.destacado, u.anio_promocion, u.correo,
                  t.nombre AS tecnico_nombre,
                  pe.profesion, pe.lugar_residencia, pe.lugar_estudio, pe.frase,
                  COALESCE(pe.campos_publicos, '') AS campos_publicos
           FROM usuarios u
           LEFT JOIN tecnicos t ON t.id = u.tecnico_id
           LEFT JOIN perfil_extendido pe ON pe.usuario_id = u.id
           WHERE u.rol = 'egresado' AND u.estado = 'activo' AND u.anio_promocion = %s
           ORDER BY u.destacado DESC, u.nombre
           LIMIT %s OFFSET %s""",
        (anio, int(por_pagina), int(offset)),
    )


def obtener_perfil_extendido(usuario_id):
    return db.fetch_one(
        "SELECT * FROM perfil_extendido WHERE usuario_id = %s", (usuario_id,)
    )


def upsert_perfil_extendido(usuario_id, profesion, lugar_residencia, lugar_estudio,
                            fecha_nacimiento, frase=None, campos_publicos=None):
    db.execute(
        """INSERT INTO perfil_extendido
             (usuario_id, profesion, lugar_residencia, lugar_estudio, fecha_nacimiento, frase, campos_publicos)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           ON DUPLICATE KEY UPDATE
             profesion = VALUES(profesion),
             lugar_residencia = VALUES(lugar_residencia),
             lugar_estudio = VALUES(lugar_estudio),
             fecha_nacimiento = VALUES(fecha_nacimiento),
             frase = VALUES(frase),
             campos_publicos = VALUES(campos_publicos)""",
        (usuario_id, profesion, lugar_residencia, lugar_estudio, fecha_nacimiento,
         frase, campos_publicos or ""),
    )


def listar_contactos(usuario_id):
    return db.fetch_all(
        "SELECT id, tipo, valor, es_principal FROM contactos WHERE usuario_id = %s ORDER BY es_principal DESC, id",
        (usuario_id,),
    )


def reemplazar_contactos(usuario_id, contactos):
    with db.transaction() as cur:
        cur.execute("DELETE FROM contactos WHERE usuario_id = %s", (usuario_id,))
        if contactos:
            cur.executemany(
                "INSERT INTO contactos (usuario_id, tipo, valor, es_principal) VALUES (%s, %s, %s, %s)",
                [(usuario_id, c["tipo"], c["valor"], int(c.get("es_principal", False))) for c in contactos],
            )


def crear_comentario(usuario_id, contenido):
    lastrowid, _ = db.execute(
        "INSERT INTO comentarios (usuario_id, contenido, estado) VALUES (%s, %s, 'visible')",
        (usuario_id, contenido),
    )
    return lastrowid


def listar_comentarios_visibles(pagina=1, por_pagina=20):
    offset = max(pagina - 1, 0) * por_pagina
    return db.fetch_all(
        """SELECT c.id, c.contenido, c.creado_en, u.nombre AS autor
           FROM comentarios c JOIN usuarios u ON u.id = c.usuario_id
           WHERE c.estado = 'visible'
           ORDER BY c.creado_en DESC
           LIMIT %s OFFSET %s""",
        (int(por_pagina), int(offset)),
    )


def listar_comentarios_admin(estado=None, pagina=1, por_pagina=25):
    offset = max(pagina - 1, 0) * por_pagina
    where = "WHERE c.estado = %s" if estado else ""
    parametros = (estado,) if estado else ()
    return db.fetch_all(
        f"""SELECT c.id, c.contenido, c.estado, c.creado_en, u.nombre AS autor
            FROM comentarios c JOIN usuarios u ON u.id = c.usuario_id
            {where}
            ORDER BY c.creado_en DESC
            LIMIT %s OFFSET %s""",
        (*parametros, int(por_pagina), int(offset)),
    )


def moderar_comentario(comentario_id, estado):
    _, rowcount = db.execute(
        "UPDATE comentarios SET estado = %s WHERE id = %s", (estado, comentario_id)
    )
    return rowcount


def crear_ticket_soporte(nombre, correo, asunto, mensaje, usuario_id=None, canal="formulario"):
    lastrowid, _ = db.execute(
        """INSERT INTO soporte_tickets (usuario_id, nombre, correo, canal, asunto, mensaje)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (usuario_id, nombre, correo, canal, asunto, mensaje),
    )
    return lastrowid


def listar_tickets_admin(estado=None, busqueda=None, pagina=1, por_pagina=25):
    """Los abiertos primero y dentro de cada estado los más antiguos arriba:
    el que lleva más tiempo esperando es el que hay que atender."""
    condiciones = []
    parametros = []

    if estado:
        condiciones.append("t.estado = %s")
        parametros.append(estado)

    if busqueda:
        condiciones.append("(t.nombre LIKE %s OR t.correo LIKE %s OR t.asunto LIKE %s)")
        patron = f"%{busqueda}%"
        parametros.extend([patron, patron, patron])

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    offset = max(pagina - 1, 0) * por_pagina

    items = db.fetch_all(
        f"""SELECT t.*, u.nombre AS revisor_nombre
            FROM soporte_tickets t
            LEFT JOIN usuarios u ON u.id = t.respondido_por
            {where}
            ORDER BY FIELD(t.estado, 'abierto', 'en_proceso', 'cerrado'), t.creado_en ASC
            LIMIT %s OFFSET %s""",
        (*parametros, int(por_pagina), int(offset)),
    )
    total = db.fetch_one(
        f"SELECT COUNT(*) AS total FROM soporte_tickets t {where}", tuple(parametros)
    )["total"]
    return items, total


def obtener_ticket(ticket_id):
    return db.fetch_one(
        """SELECT t.*, u.nombre AS revisor_nombre
           FROM soporte_tickets t
           LEFT JOIN usuarios u ON u.id = t.respondido_por
           WHERE t.id = %s""",
        (ticket_id,),
    )


def contar_tickets_por_estado():
    filas = db.fetch_all(
        "SELECT estado, COUNT(*) AS total FROM soporte_tickets GROUP BY estado"
    )
    return {fila["estado"]: fila["total"] for fila in filas}


def contar_tickets_abiertos():
    fila = db.fetch_one(
        "SELECT COUNT(*) AS total FROM soporte_tickets WHERE estado <> 'cerrado'"
    )
    return fila["total"] if fila else 0


def actualizar_estado_ticket(ticket_id, estado):
    _, rowcount = db.execute(
        "UPDATE soporte_tickets SET estado = %s WHERE id = %s", (estado, ticket_id)
    )
    return rowcount


def responder_ticket(ticket_id, respuesta, respondido_por):
    """Guardar la respuesta y cerrar el ticket es una sola operación:
    si se hicieran por separado, un fallo entre las dos dejaría el ticket
    contestado pero abierto, o cerrado sin respuesta."""
    _, rowcount = db.execute(
        """UPDATE soporte_tickets
           SET respuesta = %s, respondido_por = %s, respondido_en = NOW(), estado = 'cerrado'
           WHERE id = %s""",
        (respuesta, respondido_por, ticket_id),
    )
    return rowcount


def crear_token_reset(usuario_id, token_hash, expira_en):
    lastrowid, _ = db.execute(
        "INSERT INTO password_reset_tokens (usuario_id, token_hash, expira_en) VALUES (%s, %s, %s)",
        (usuario_id, token_hash, expira_en),
    )
    return lastrowid


def obtener_token_valido(token_hash):
    return db.fetch_one(
        """SELECT * FROM password_reset_tokens
           WHERE token_hash = %s AND usado_en IS NULL AND expira_en > NOW()""",
        (token_hash,),
    )


def marcar_token_usado(token_id):
    db.execute("UPDATE password_reset_tokens SET usado_en = NOW() WHERE id = %s", (token_id,))


def registrar_bitacora(usuario_id, accion, detalle=None, ip=None):
    db.execute(
        "INSERT INTO bitacora (usuario_id, accion, detalle, ip) VALUES (%s, %s, %s, %s)",
        (usuario_id, accion, detalle, ip),
    )


def listar_bitacora_usuario(usuario_id, pagina=1, por_pagina=25):
    offset = max(pagina - 1, 0) * por_pagina
    return db.fetch_all(
        """SELECT accion, detalle, ip, creado_en FROM bitacora
           WHERE usuario_id = %s ORDER BY creado_en DESC LIMIT %s OFFSET %s""",
        (usuario_id, int(por_pagina), int(offset)),
    )


def listar_directorio(busqueda=None, tecnico_id=None, anio_promocion=None, pagina=1, por_pagina=24):
    condiciones = ["u.rol = 'egresado'", "u.estado = 'activo'"]
    parametros = []

    if busqueda:
        condiciones.append("(u.nombre LIKE %s OR pe.profesion LIKE %s)")
        comodin = f"%{busqueda}%"
        parametros += [comodin, comodin]
    if tecnico_id:
        condiciones.append("u.tecnico_id = %s")
        parametros.append(tecnico_id)
    if anio_promocion:
        condiciones.append("u.anio_promocion = %s")
        parametros.append(anio_promocion)

    where = "WHERE " + " AND ".join(condiciones)
    offset = max(pagina - 1, 0) * por_pagina

    items = db.fetch_all(
        f"""SELECT u.id, u.nombre, u.foto, u.correo, u.anio_promocion, u.destacado,
                   t.nombre AS tecnico_nombre,
                   pe.profesion, pe.lugar_residencia, pe.lugar_estudio, pe.frase,
                   COALESCE(pe.campos_publicos, '') AS campos_publicos
            FROM usuarios u
            LEFT JOIN tecnicos t ON t.id = u.tecnico_id
            LEFT JOIN perfil_extendido pe ON pe.usuario_id = u.id
            {where}
            ORDER BY u.nombre
            LIMIT %s OFFSET %s""",
        (*parametros, int(por_pagina), int(offset)),
    )
    total = db.fetch_one(
        f"""SELECT COUNT(*) AS total FROM usuarios u
            LEFT JOIN perfil_extendido pe ON pe.usuario_id = u.id {where}""",
        tuple(parametros),
    )["total"]
    return items, total


def alternar_destacado(usuario_id):
    """Prende o apaga la marca de "destacado" de un egresado. Solo la usa la
    administración desde el directorio. Devuelve el nuevo estado (True/False)."""
    fila = db.fetch_one(
        "SELECT destacado FROM usuarios WHERE id = %s AND rol = 'egresado'",
        (usuario_id,),
    )
    if fila is None:
        return None
    nuevo = 0 if fila["destacado"] else 1
    db.execute("UPDATE usuarios SET destacado = %s WHERE id = %s", (nuevo, usuario_id))
    return bool(nuevo)


def crear_solicitud(usuario_id, tipo, descripcion):
    lastrowid, _ = db.execute(
        "INSERT INTO solicitudes (usuario_id, tipo, descripcion) VALUES (%s, %s, %s)",
        (usuario_id, tipo, descripcion),
    )
    return lastrowid


def listar_solicitudes_usuario(usuario_id, estado=None, pagina=1, por_pagina=20):
    condiciones = ["usuario_id = %s"]
    parametros = [usuario_id]
    if estado:
        condiciones.append("estado = %s")
        parametros.append(estado)
    where = "WHERE " + " AND ".join(condiciones)
    offset = max(pagina - 1, 0) * por_pagina
    return db.fetch_all(
        f"SELECT * FROM solicitudes {where} ORDER BY creado_en DESC LIMIT %s OFFSET %s",
        (*parametros, int(por_pagina), int(offset)),
    )


def listar_solicitudes_admin(estado=None, pagina=1, por_pagina=25):
    where = "WHERE s.estado = %s" if estado else ""
    parametros = (estado,) if estado else ()
    offset = max(pagina - 1, 0) * por_pagina
    items = db.fetch_all(
        f"""SELECT s.*, u.nombre AS solicitante
            FROM solicitudes s JOIN usuarios u ON u.id = s.usuario_id
            {where}
            ORDER BY s.creado_en DESC LIMIT %s OFFSET %s""",
        (*parametros, int(por_pagina), int(offset)),
    )
    total = db.fetch_one(f"SELECT COUNT(*) AS total FROM solicitudes s {where}", parametros)["total"]
    return items, total


def actualizar_estado_solicitud(solicitud_id, estado, respuesta=None):
    _, rowcount = db.execute(
        "UPDATE solicitudes SET estado = %s, respuesta = %s WHERE id = %s",
        (estado, respuesta, solicitud_id),
    )
    return rowcount


def obtener_o_crear_conversacion(usuario_a, usuario_b):
    uno, dos = sorted((usuario_a, usuario_b))
    fila = db.fetch_one(
        "SELECT id FROM conversaciones WHERE usuario_uno_id = %s AND usuario_dos_id = %s", (uno, dos)
    )
    if fila:
        return fila["id"]
    lastrowid, _ = db.execute(
        "INSERT INTO conversaciones (usuario_uno_id, usuario_dos_id) VALUES (%s, %s)", (uno, dos)
    )
    return lastrowid


def obtener_conversacion(conversacion_id, usuario_id):
    return db.fetch_one(
        "SELECT * FROM conversaciones WHERE id = %s AND (usuario_uno_id = %s OR usuario_dos_id = %s)",
        (conversacion_id, usuario_id, usuario_id),
    )


def listar_conversaciones(usuario_id):
    return db.fetch_all(
        """SELECT c.id, c.ultimo_mensaje_en,
                  CASE WHEN c.usuario_uno_id = %s THEN c.usuario_dos_id ELSE c.usuario_uno_id END AS otro_id,
                  u.nombre AS otro_nombre, u.foto AS otro_foto,
                  (SELECT contenido FROM mensajes m WHERE m.conversacion_id = c.id
                     ORDER BY m.creado_en DESC LIMIT 1) AS ultimo_mensaje,
                  (SELECT COUNT(*) FROM mensajes m WHERE m.conversacion_id = c.id
                     AND m.remitente_id <> %s AND m.leido_en IS NULL) AS no_leidos
           FROM conversaciones c
           JOIN usuarios u ON u.id = CASE WHEN c.usuario_uno_id = %s THEN c.usuario_dos_id ELSE c.usuario_uno_id END
           WHERE c.usuario_uno_id = %s OR c.usuario_dos_id = %s
           ORDER BY c.ultimo_mensaje_en DESC""",
        (usuario_id, usuario_id, usuario_id, usuario_id, usuario_id),
    )


def listar_mensajes(conversacion_id, pagina=1, por_pagina=50):
    offset = max(pagina - 1, 0) * por_pagina
    return db.fetch_all(
        """SELECT m.*, u.nombre AS remitente_nombre FROM mensajes m
           JOIN usuarios u ON u.id = m.remitente_id
           WHERE m.conversacion_id = %s ORDER BY m.creado_en ASC LIMIT %s OFFSET %s""",
        (conversacion_id, int(por_pagina), int(offset)),
    )


def enviar_mensaje(conversacion_id, remitente_id, contenido):
    lastrowid, _ = db.execute(
        "INSERT INTO mensajes (conversacion_id, remitente_id, contenido) VALUES (%s, %s, %s)",
        (conversacion_id, remitente_id, contenido),
    )
    db.execute("UPDATE conversaciones SET ultimo_mensaje_en = NOW() WHERE id = %s", (conversacion_id,))
    return lastrowid


def marcar_mensajes_leidos(conversacion_id, usuario_id):
    db.execute(
        "UPDATE mensajes SET leido_en = NOW() WHERE conversacion_id = %s AND remitente_id <> %s AND leido_en IS NULL",
        (conversacion_id, usuario_id),
    )


def listar_eventos(momento="proximos", pagina=1, por_pagina=20, usuario_id=None):
    orden = "ASC" if momento == "proximos" else "DESC"
    comparador = ">=" if momento == "proximos" else "<"
    offset = max(pagina - 1, 0) * por_pagina
    return db.fetch_all(
        f"""SELECT e.*, (ef.usuario_id IS NOT NULL) AS es_favorito
            FROM eventos e
            LEFT JOIN eventos_favoritos ef
              ON ef.evento_id = e.id AND ef.usuario_id = %s
            WHERE e.fecha_inicio {comparador} NOW()
            ORDER BY e.fecha_inicio {orden} LIMIT %s OFFSET %s""",
        (usuario_id, int(por_pagina), int(offset)),
    )


def obtener_evento(evento_id, usuario_id=None):
    return db.fetch_one(
        """SELECT e.*, u.nombre AS creador_nombre,
                  (SELECT COUNT(*) FROM eventos_favoritos WHERE evento_id = e.id) AS total_favoritos,
                  EXISTS(SELECT 1 FROM eventos_favoritos
                         WHERE evento_id = e.id AND usuario_id = %s) AS es_favorito
           FROM eventos e
           LEFT JOIN usuarios u ON u.id = e.creado_por
           WHERE e.id = %s""",
        (usuario_id, evento_id),
    )


def alternar_evento_favorito(usuario_id, evento_id):
    """Marca o desmarca un evento como favorito. Devuelve True si quedó marcado."""
    existe = db.fetch_one(
        "SELECT 1 FROM eventos_favoritos WHERE usuario_id = %s AND evento_id = %s",
        (usuario_id, evento_id),
    )
    if existe:
        db.execute(
            "DELETE FROM eventos_favoritos WHERE usuario_id = %s AND evento_id = %s",
            (usuario_id, evento_id),
        )
        return False
    db.execute(
        "INSERT INTO eventos_favoritos (usuario_id, evento_id) VALUES (%s, %s)",
        (usuario_id, evento_id),
    )
    return True


def eventos_para_recordar():
    """Favoritos cuyo evento es HOY y a los que aún no se les envió recordatorio.
    Lo usa la tarea diaria enviar_recordatorios.py."""
    return db.fetch_all(
        """SELECT ef.usuario_id, ef.evento_id, u.nombre AS usuario_nombre, u.correo,
                  e.titulo, e.lugar, e.fecha_inicio
           FROM eventos_favoritos ef
           JOIN eventos e ON e.id = ef.evento_id
           JOIN usuarios u ON u.id = ef.usuario_id
           WHERE DATE(e.fecha_inicio) = CURDATE()
             AND ef.recordado_en IS NULL
             AND u.estado = 'activo'"""
    )


def marcar_recordatorio_enviado(usuario_id, evento_id):
    db.execute(
        "UPDATE eventos_favoritos SET recordado_en = NOW() WHERE usuario_id = %s AND evento_id = %s",
        (usuario_id, evento_id),
    )


def crear_evento(titulo, descripcion, categoria, lugar, fecha_inicio, creado_por):
    lastrowid, _ = db.execute(
        """INSERT INTO eventos (titulo, descripcion, categoria, lugar, fecha_inicio, creado_por)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (titulo, descripcion, categoria, lugar, fecha_inicio, creado_por),
    )
    return lastrowid


def actualizar_evento(evento_id, titulo, descripcion, categoria, lugar, fecha_inicio):
    db.execute(
        """UPDATE eventos SET titulo = %s, descripcion = %s, categoria = %s, lugar = %s, fecha_inicio = %s
           WHERE id = %s""",
        (titulo, descripcion, categoria, lugar, fecha_inicio, evento_id),
    )


def eliminar_evento(evento_id):
    db.execute("DELETE FROM eventos WHERE id = %s", (evento_id,))


def obtener_graduado(graduado_id):
    return db.fetch_one(
        """SELECT g.*, t.nombre AS tecnico_nombre, u.id AS usuario_id
           FROM graduados g
           LEFT JOIN tecnicos t ON t.id = g.tecnico_id
           LEFT JOIN usuarios u ON u.graduado_id = g.id
           WHERE g.id = %s""",
        (graduado_id,),
    )


def buscar_graduados(busqueda=None, anio_promocion=None, tecnico_id=None, con_cuenta=None, pagina=1, por_pagina=30):
    condiciones = []
    parametros = []

    if busqueda:
        comodin = f"%{busqueda}%"
        cedula_cif = utils.cifrar_cedula(utils.normalizar_cedula(busqueda))
        if cedula_cif:
            condiciones.append("(g.nombre LIKE %s OR g.cedula = %s)")
            parametros += [comodin, cedula_cif]
        else:
            condiciones.append("g.nombre LIKE %s")
            parametros.append(comodin)
    if anio_promocion:
        condiciones.append("g.anio_promocion = %s")
        parametros.append(anio_promocion)
    if tecnico_id:
        condiciones.append("g.tecnico_id = %s")
        parametros.append(tecnico_id)
    if con_cuenta == "si":
        condiciones.append("u.id IS NOT NULL")
    elif con_cuenta == "no":
        condiciones.append("u.id IS NULL")

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    offset = max(pagina - 1, 0) * por_pagina

    items = db.fetch_all(
        f"""SELECT g.id, g.cedula, g.nombre, g.anio_promocion, g.libro_acta,
                   t.nombre AS tecnico_nombre, u.id AS usuario_id
            FROM graduados g
            LEFT JOIN tecnicos t ON t.id = g.tecnico_id
            LEFT JOIN usuarios u ON u.graduado_id = g.id
            {where}
            ORDER BY g.anio_promocion DESC, g.nombre
            LIMIT %s OFFSET %s""",
        (*parametros, int(por_pagina), int(offset)),
    )
    for _it in items:
        if _it.get("cedula"):
            _it["cedula"] = utils.descifrar_cedula(_it["cedula"])
    total = db.fetch_one(
        f"""SELECT COUNT(*) AS total FROM graduados g
            LEFT JOIN usuarios u ON u.graduado_id = g.id {where}""",
        tuple(parametros),
    )["total"]
    return items, total


def buscar_graduado_coincidente(cedula=None, nombre=None, anio_promocion=None):
    fila = None
    if cedula:
        fila = db.fetch_one("SELECT * FROM graduados WHERE cedula = %s", (utils.cifrar_cedula(cedula),))
    if not fila and nombre and anio_promocion:
        fila = db.fetch_one(
            "SELECT * FROM graduados WHERE nombre = %s AND anio_promocion = %s",
            (nombre, anio_promocion),
        )
    if fila and fila.get("cedula"):
        fila["cedula"] = utils.descifrar_cedula(fila["cedula"])
    return fila


def crear_graduado(cedula, nombre, anio_promocion, tecnico_id=None, libro_acta=None, observaciones=None):
    lastrowid, _ = db.execute(
        """INSERT INTO graduados (cedula, nombre, anio_promocion, tecnico_id, libro_acta, observaciones)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (utils.cifrar_cedula(cedula), nombre, anio_promocion, tecnico_id, libro_acta, observaciones),
    )
    return lastrowid


def importar_graduados(filas):
    if not filas:
        return 0
    with db.transaction() as cur:
        cur.executemany(
            """INSERT INTO graduados (cedula, nombre, anio_promocion, tecnico_id, libro_acta)
               VALUES (%s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                 nombre = VALUES(nombre),
                 anio_promocion = VALUES(anio_promocion),
                 tecnico_id = COALESCE(VALUES(tecnico_id), tecnico_id),
                 libro_acta = COALESCE(VALUES(libro_acta), libro_acta)""",
            [
                (utils.cifrar_cedula(f.get("cedula")), f["nombre"], f["anio_promocion"], f.get("tecnico_id"), f.get("libro_acta"))
                for f in filas
            ],
        )
    return len(filas)


def contar_graduados():
    fila = db.fetch_one(
        """SELECT COUNT(*) AS total,
                  COUNT(DISTINCT g.anio_promocion) AS promociones,
                  SUM(CASE WHEN u.id IS NOT NULL THEN 1 ELSE 0 END) AS con_cuenta
           FROM graduados g LEFT JOIN usuarios u ON u.graduado_id = g.id"""
    )
    return {
        "total": fila["total"] or 0,
        "promociones": fila["promociones"] or 0,
        "con_cuenta": int(fila["con_cuenta"] or 0),
    }


def listar_promociones_graduados():
    return db.fetch_all(
        """SELECT anio_promocion, COUNT(*) AS total_graduados
           FROM graduados GROUP BY anio_promocion ORDER BY anio_promocion DESC"""
    )


def crear_solicitud_cuenta(
    cedula, nombre, correo, anio_promocion, telefono=None, tecnico_id=None,
    mensaje=None, graduado_id=None, origen="formulario", ip_origen=None,
):
    lastrowid, _ = db.execute(
        """INSERT INTO solicitudes_cuenta
             (cedula, nombre, correo, telefono, anio_promocion, tecnico_id, mensaje, graduado_id, origen, ip_origen)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (utils.cifrar_cedula(cedula), nombre, correo, telefono, anio_promocion, tecnico_id, mensaje, graduado_id, origen, ip_origen),
    )
    return lastrowid


def existe_solicitud_cuenta_pendiente(cedula, correo):
    return db.fetch_one(
        """SELECT id FROM solicitudes_cuenta
           WHERE estado = 'pendiente' AND (cedula = %s OR correo = %s) LIMIT 1""",
        (utils.cifrar_cedula(cedula), correo),
    ) is not None


def existe_cuenta_con(cedula, correo):
    return db.fetch_one(
        "SELECT id FROM usuarios WHERE cedula = %s OR correo = %s LIMIT 1",
        (utils.cifrar_cedula(cedula), correo),
    ) is not None


def obtener_solicitud_cuenta(solicitud_id):
    fila = db.fetch_one(
        """SELECT sc.*, t.nombre AS tecnico_nombre, g.nombre AS graduado_nombre,
                  g.anio_promocion AS graduado_anio, g.libro_acta
           FROM solicitudes_cuenta sc
           LEFT JOIN tecnicos t ON t.id = sc.tecnico_id
           LEFT JOIN graduados g ON g.id = sc.graduado_id
           WHERE sc.id = %s""",
        (solicitud_id,),
    )
    if fila and fila.get("cedula"):
        fila["cedula"] = utils.descifrar_cedula(fila["cedula"])
    return fila


def listar_solicitudes_cuenta(estado=None, busqueda=None, pagina=1, por_pagina=25):
    condiciones = []
    parametros = []

    if estado:
        condiciones.append("sc.estado = %s")
        parametros.append(estado)
    if busqueda:
        comodin = f"%{busqueda}%"
        cedula_cif = utils.cifrar_cedula(utils.normalizar_cedula(busqueda))
        if cedula_cif:
            condiciones.append("(sc.nombre LIKE %s OR sc.cedula = %s OR sc.correo LIKE %s)")
            parametros += [comodin, cedula_cif, comodin]
        else:
            condiciones.append("(sc.nombre LIKE %s OR sc.correo LIKE %s)")
            parametros += [comodin, comodin]

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    offset = max(pagina - 1, 0) * por_pagina

    items = db.fetch_all(
        f"""SELECT sc.*, t.nombre AS tecnico_nombre, g.nombre AS graduado_nombre, g.libro_acta,
                   r.nombre AS revisor_nombre
            FROM solicitudes_cuenta sc
            LEFT JOIN tecnicos t ON t.id = sc.tecnico_id
            LEFT JOIN graduados g ON g.id = sc.graduado_id
            LEFT JOIN usuarios r ON r.id = sc.revisado_por
            {where}
            ORDER BY sc.creado_en DESC
            LIMIT %s OFFSET %s""",
        (*parametros, int(por_pagina), int(offset)),
    )
    for _it in items:
        if _it.get("cedula"):
            _it["cedula"] = utils.descifrar_cedula(_it["cedula"])
    total = db.fetch_one(
        f"SELECT COUNT(*) AS total FROM solicitudes_cuenta sc {where}", tuple(parametros)
    )["total"]
    return items, total


def contar_solicitudes_cuenta_pendientes():
    return db.fetch_one(
        "SELECT COUNT(*) AS total FROM solicitudes_cuenta WHERE estado = 'pendiente'"
    )["total"]


def marcar_solicitud_cuenta_aprobada(solicitud_id, usuario_id, graduado_id, revisado_por):
    _, rowcount = db.execute(
        """UPDATE solicitudes_cuenta
           SET estado = 'aprobada', usuario_id = %s, graduado_id = %s,
               revisado_por = %s, revisado_en = NOW(), motivo_rechazo = NULL
           WHERE id = %s AND estado = 'pendiente'""",
        (usuario_id, graduado_id, revisado_por, solicitud_id),
    )
    return rowcount


def rechazar_solicitud_cuenta(solicitud_id, motivo, revisado_por):
    _, rowcount = db.execute(
        """UPDATE solicitudes_cuenta
           SET estado = 'rechazada', motivo_rechazo = %s, revisado_por = %s, revisado_en = NOW()
           WHERE id = %s AND estado = 'pendiente'""",
        (motivo, revisado_por, solicitud_id),
    )
    return rowcount
