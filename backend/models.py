from backend import db


def listar_tecnicos_activos():
    return db.fetch_all(
        "SELECT id, nombre FROM tecnicos WHERE activo = 1 ORDER BY nombre"
    )


_CAMPOS_USUARIO_ADMIN = {"nombre", "correo", "usuario", "rol", "estado", "anio_promocion", "tecnico_id"}


def obtener_usuario_por_id(usuario_id):
    return db.fetch_one(
        """SELECT u.*, t.nombre AS tecnico_nombre
           FROM usuarios u LEFT JOIN tecnicos t ON t.id = u.tecnico_id
           WHERE u.id = %s""",
        (usuario_id,),
    )


def obtener_usuario_por_login(identificador):
    return db.fetch_one(
        "SELECT * FROM usuarios WHERE correo = %s OR usuario = %s LIMIT 1",
        (identificador, identificador),
    )


def crear_usuario(nombre, correo, usuario, password_hash, rol, anio_promocion=None, tecnico_id=None):
    lastrowid, _ = db.execute(
        """INSERT INTO usuarios
             (nombre, correo, usuario, password_hash, rol, estado, anio_promocion, tecnico_id, forzar_cambio_password)
           VALUES (%s, %s, %s, %s, %s, 'activo', %s, %s, 1)""",
        (nombre, correo, usuario, password_hash, rol, anio_promocion, tecnico_id),
    )
    return lastrowid


def actualizar_usuario_admin(usuario_id, campos: dict):
    campos = {k: v for k, v in campos.items() if k in _CAMPOS_USUARIO_ADMIN}
    if not campos:
        return 0
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
        condiciones.append("(u.nombre LIKE %s OR u.correo LIKE %s OR u.usuario LIKE %s)")
        comodin = f"%{busqueda}%"
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
        f"""SELECT u.id, u.nombre, u.correo, u.usuario, u.rol, u.estado,
                   u.anio_promocion, t.nombre AS tecnico_nombre, u.ultimo_login, u.creado_en
            FROM usuarios u LEFT JOIN tecnicos t ON t.id = u.tecnico_id
            {where}
            ORDER BY u.creado_en DESC
            LIMIT %s OFFSET %s""",
        (*parametros, int(por_pagina), int(offset)),
    )
    total = db.fetch_one(
        f"SELECT COUNT(*) AS total FROM usuarios u {where}", tuple(parametros)
    )["total"]
    return items, total


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


def listar_egresados_por_promocion(anio, pagina=1, por_pagina=60):
    offset = max(pagina - 1, 0) * por_pagina
    return db.fetch_all(
        """SELECT u.id, u.nombre, u.foto, pe.profesion, pe.frase
           FROM usuarios u
           LEFT JOIN perfil_extendido pe ON pe.usuario_id = u.id
           WHERE u.rol = 'egresado' AND u.estado = 'activo' AND u.anio_promocion = %s
           ORDER BY u.nombre
           LIMIT %s OFFSET %s""",
        (anio, int(por_pagina), int(offset)),
    )


def obtener_perfil_extendido(usuario_id):
    return db.fetch_one(
        "SELECT * FROM perfil_extendido WHERE usuario_id = %s", (usuario_id,)
    )


def upsert_perfil_extendido(usuario_id, profesion, lugar_residencia, lugar_estudio, fecha_nacimiento, frase=None):
    db.execute(
        """INSERT INTO perfil_extendido (usuario_id, profesion, lugar_residencia, lugar_estudio, fecha_nacimiento, frase)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON DUPLICATE KEY UPDATE
             profesion = VALUES(profesion),
             lugar_residencia = VALUES(lugar_residencia),
             lugar_estudio = VALUES(lugar_estudio),
             fecha_nacimiento = VALUES(fecha_nacimiento),
             frase = VALUES(frase)""",
        (usuario_id, profesion, lugar_residencia, lugar_estudio, fecha_nacimiento, frase),
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


def listar_tickets_admin(estado=None, pagina=1, por_pagina=25):
    offset = max(pagina - 1, 0) * por_pagina
    where = "WHERE estado = %s" if estado else ""
    parametros = (estado,) if estado else ()
    items = db.fetch_all(
        f"""SELECT * FROM soporte_tickets {where}
            ORDER BY creado_en DESC LIMIT %s OFFSET %s""",
        (*parametros, int(por_pagina), int(offset)),
    )
    total = db.fetch_one(
        f"SELECT COUNT(*) AS total FROM soporte_tickets {where}", parametros
    )["total"]
    return items, total


def actualizar_estado_ticket(ticket_id, estado):
    _, rowcount = db.execute(
        "UPDATE soporte_tickets SET estado = %s WHERE id = %s", (estado, ticket_id)
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
