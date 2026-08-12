-- ============================================================
-- V.I.A — Vinculación Integral de Alumnos (Liceo Tame)
-- schema.sql — estructura de la base de datos
--
-- Motor: MySQL 8.0+ (usa InnoDB para soportar FKs y transacciones)
-- Diseñado para ~5000 usuarios: los índices de abajo están puestos
-- pensando en los queries reales que hace la app (login, listado de
-- admin con filtros, perfil propio, feed de comentarios, tickets de
-- soporte). No son índices "por si acaso": cada uno tiene un comentario
-- diciendo qué consulta cubre.
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ------------------------------------------------------------
-- Catálogo de técnicos (programas técnicos del Liceo)
-- Tabla pequeña y estable -> no necesita índices extra además
-- de la PK; se lee completa para llenar selects.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tecnicos (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  nombre        VARCHAR(120) NOT NULL,
  activo        TINYINT(1)   NOT NULL DEFAULT 1,
  creado_en     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_tecnicos_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Usuarios (cuentas). Solo el administrador crea filas aquí
-- (registro cerrado). Contiene únicamente lo que captura el
-- admin al dar de alta: identidad, credenciales, promoción y
-- técnico. Los datos que el propio egresado puede editar viven
-- en perfil_extendido, separados a propósito para que el admin
-- nunca pise por accidente lo que el usuario mantiene.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
  id                     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  nombre                 VARCHAR(150)    NOT NULL,
  correo                 VARCHAR(190)    NOT NULL,
  usuario                VARCHAR(60)     NOT NULL,
  password_hash          VARCHAR(255)    NOT NULL,
  rol                    ENUM('egresado','administrador','institucion') NOT NULL DEFAULT 'egresado',
  estado                 ENUM('activo','inactivo','pendiente')          NOT NULL DEFAULT 'pendiente',
  anio_promocion         SMALLINT UNSIGNED NULL,
  tecnico_id             INT UNSIGNED    NULL,
  foto                   VARCHAR(255)    NULL,
  forzar_cambio_password TINYINT(1)      NOT NULL DEFAULT 1,
  ultimo_login            DATETIME       NULL,
  creado_en              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_usuarios_tecnico FOREIGN KEY (tecnico_id) REFERENCES tecnicos(id) ON DELETE SET NULL,

  -- login por correo o por usuario (recuperar.html acepta ambos) -> ambos únicos
  UNIQUE KEY uq_usuarios_correo (correo),
  UNIQUE KEY uq_usuarios_usuario (usuario),

  -- admin filtra/pagina por rol y estado constantemente (panel de usuarios);
  -- el mismo índice sirve también para agrupar por promoción al calcular
  -- las "4 promociones recientes" del carrusel (WHERE rol/estado + GROUP BY
  -- anio_promocion usa este índice como prefijo).
  KEY ix_usuarios_rol_estado_promocion (rol, estado, anio_promocion),

  -- reporte típico: "egresados de tal técnico en tal promoción"
  KEY ix_usuarios_tecnico_promocion (tecnico_id, anio_promocion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Perfil extendido: 1 fila por usuario, la parte que el propio
-- egresado edita desde /usuarios/perfil (profesión, contacto
-- general, dónde vive, dónde estudió, fecha de nacimiento, y una
-- frase opcional que se muestra en la tarjeta de su promoción).
-- Se guarda fecha_nacimiento en vez de "edad" directa porque la
-- edad cambia con el tiempo; la app la calcula al vuelo.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS perfil_extendido (
  usuario_id        INT UNSIGNED PRIMARY KEY,
  profesion         VARCHAR(150) NULL,
  lugar_residencia  VARCHAR(150) NULL,
  lugar_estudio     VARCHAR(150) NULL,
  fecha_nacimiento  DATE         NULL,
  frase             VARCHAR(200) NULL,
  actualizado_en    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_perfil_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Métodos de contacto del egresado (puede tener varios: celular,
-- whatsapp, redes, correo alterno). Tabla 1-N a propósito, en vez
-- de columnas sueltas, porque "métodos de contacto" es plural por
-- diseño y así se pueden agregar tipos nuevos sin migrar el schema.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contactos (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id    INT UNSIGNED NOT NULL,
  tipo          ENUM('telefono','whatsapp','correo_alterno','instagram','facebook','linkedin','otro') NOT NULL,
  valor         VARCHAR(190) NOT NULL,
  es_principal  TINYINT(1)   NOT NULL DEFAULT 0,
  creado_en     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_contactos_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,

  -- "dame los contactos del usuario X" es el único acceso a esta tabla
  KEY ix_contactos_usuario (usuario_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Tokens de recuperación de contraseña. Se guarda el HASH del
-- token, nunca el token en claro (igual que una contraseña).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS password_reset_tokens (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id  INT UNSIGNED NOT NULL,
  token_hash  CHAR(64)     NOT NULL,
  expira_en   DATETIME     NOT NULL,
  usado_en    DATETIME     NULL,
  creado_en   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_reset_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,

  -- validar un token entrante: búsqueda directa por su hash
  UNIQUE KEY uq_reset_token_hash (token_hash),
  -- limpieza periódica de tokens vencidos / listar tokens de un usuario
  KEY ix_reset_usuario_expira (usuario_id, expira_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Comentarios (feed visible para egresados, moderado por admin).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS comentarios (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id  INT UNSIGNED NOT NULL,
  contenido   VARCHAR(1000) NOT NULL,
  estado      ENUM('visible','oculto','pendiente') NOT NULL DEFAULT 'visible',
  creado_en   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_comentarios_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,

  -- feed público: "visibles, más recientes primero" y cola de moderación
  KEY ix_comentarios_estado_fecha (estado, creado_en),
  -- "comentarios de este usuario"
  KEY ix_comentarios_usuario (usuario_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Canales de soporte: tickets creados desde /contacto o desde el
-- área de usuarios. usuario_id es NULL cuando el formulario público
-- lo llena alguien que aún no tiene cuenta.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS soporte_tickets (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id    INT UNSIGNED NULL,
  nombre        VARCHAR(150) NOT NULL,
  correo        VARCHAR(190) NOT NULL,
  canal         ENUM('formulario','correo','telefono') NOT NULL DEFAULT 'formulario',
  asunto        VARCHAR(200) NOT NULL,
  mensaje       VARCHAR(2000) NOT NULL,
  estado        ENUM('abierto','en_proceso','cerrado') NOT NULL DEFAULT 'abierto',
  creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_soporte_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,

  -- bandeja de admin: filtra por estado, ordena por fecha
  KEY ix_soporte_estado_fecha (estado, creado_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- Bitácora de actividad (auditoría). Registra acciones sensibles:
-- login, cambios de contraseña, cambios que hace un admin sobre
-- una cuenta. usuario_id es quien EJECUTA la acción.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bitacora (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id  INT UNSIGNED NULL,
  accion      VARCHAR(60)   NOT NULL,
  detalle     VARCHAR(500)  NULL,
  ip          VARCHAR(45)   NULL,
  creado_en   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_bitacora_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,

  -- historial de actividad de una cuenta, más reciente primero (vista admin)
  KEY ix_bitacora_usuario_fecha (usuario_id, creado_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
