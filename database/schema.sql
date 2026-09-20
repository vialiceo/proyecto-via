SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

/*
 * Catálogo de promociones: un año por promoción (desde 1967). La página
 * "Ver promociones" las lista todas, tengan o no egresados aún. Las
 * modalidades/técnicos de cada año se agregan cuando haya datos reales.
 */
CREATE TABLE IF NOT EXISTS promociones (
  anio        SMALLINT UNSIGNED PRIMARY KEY,
  descripcion VARCHAR(200) NULL,
  activa      TINYINT(1) NOT NULL DEFAULT 1,
  creado_en   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS tecnicos (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  nombre        VARCHAR(120) NOT NULL,
  activo        TINYINT(1)   NOT NULL DEFAULT 1,
  creado_en     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_tecnicos_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS graduados (
  id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  cedula         VARCHAR(120)      NULL, /* cifrada (AES-SIV) */
  nombre         VARCHAR(150)      NOT NULL,
  anio_promocion SMALLINT UNSIGNED NOT NULL,
  tecnico_id     INT UNSIGNED      NULL,
  libro_acta     VARCHAR(60)       NULL,
  observaciones  VARCHAR(300)      NULL,
  creado_en      DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_graduados_tecnico FOREIGN KEY (tecnico_id) REFERENCES tecnicos(id) ON DELETE SET NULL,

  UNIQUE KEY uq_graduados_cedula (cedula),
  UNIQUE KEY uq_graduados_nombre_anio (nombre, anio_promocion),
  KEY ix_graduados_anio_nombre (anio_promocion, nombre),
  KEY ix_graduados_tecnico_anio (tecnico_id, anio_promocion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS usuarios (
  id                     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  cedula                 VARCHAR(120)    NULL, /* cifrada (AES-SIV) */
  graduado_id            INT UNSIGNED    NULL,
  nombre                 VARCHAR(150)    NOT NULL,
  correo                 VARCHAR(190)    NOT NULL,
  usuario                VARCHAR(60)     NOT NULL,
  password_hash          VARCHAR(255)    NOT NULL,
  rol                    ENUM('egresado','administrador','institucion') NOT NULL DEFAULT 'egresado',
  estado                 ENUM('activo','inactivo','pendiente')          NOT NULL DEFAULT 'pendiente',
  anio_promocion         SMALLINT UNSIGNED NULL,
  tecnico_id             INT UNSIGNED    NULL,
  foto                   VARCHAR(255)    NULL,
  destacado              TINYINT(1)      NOT NULL DEFAULT 0,
  forzar_cambio_password TINYINT(1)      NOT NULL DEFAULT 1,
  ultimo_login            DATETIME       NULL,
  creado_en              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_usuarios_tecnico FOREIGN KEY (tecnico_id) REFERENCES tecnicos(id) ON DELETE SET NULL,
  CONSTRAINT fk_usuarios_graduado FOREIGN KEY (graduado_id) REFERENCES graduados(id) ON DELETE SET NULL,

  UNIQUE KEY uq_usuarios_cedula (cedula),
  UNIQUE KEY uq_usuarios_correo (correo),
  UNIQUE KEY uq_usuarios_usuario (usuario),
  UNIQUE KEY uq_usuarios_graduado (graduado_id),
  KEY ix_usuarios_rol_estado_promocion (rol, estado, anio_promocion),
  KEY ix_usuarios_tecnico_promocion (tecnico_id, anio_promocion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS perfil_extendido (
  usuario_id        INT UNSIGNED PRIMARY KEY,
  profesion         VARCHAR(150) NULL,
  lugar_residencia  VARCHAR(150) NULL,
  lugar_estudio     VARCHAR(150) NULL,
  fecha_nacimiento  DATE         NULL,
  frase             VARCHAR(200) NULL,
  campos_publicos   VARCHAR(255) NOT NULL DEFAULT 'profesion,frase',
  actualizado_en    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_perfil_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS contactos (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id    INT UNSIGNED NOT NULL,
  tipo          ENUM('telefono','whatsapp','correo_alterno','instagram','facebook','linkedin','otro') NOT NULL,
  valor         VARCHAR(190) NOT NULL,
  es_principal  TINYINT(1)   NOT NULL DEFAULT 0,
  creado_en     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_contactos_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
  KEY ix_contactos_usuario (usuario_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS password_reset_tokens (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id  INT UNSIGNED NOT NULL,
  token_hash  CHAR(64)     NOT NULL,
  expira_en   DATETIME     NOT NULL,
  usado_en    DATETIME     NULL,
  creado_en   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_reset_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
  UNIQUE KEY uq_reset_token_hash (token_hash),
  KEY ix_reset_usuario_expira (usuario_id, expira_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS comentarios (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id  INT UNSIGNED NOT NULL,
  contenido   VARCHAR(1000) NOT NULL,
  estado      ENUM('visible','oculto','pendiente') NOT NULL DEFAULT 'visible',
  creado_en   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_comentarios_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
  KEY ix_comentarios_estado_fecha (estado, creado_en),
  KEY ix_comentarios_usuario (usuario_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS soporte_tickets (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id    INT UNSIGNED NULL,
  nombre        VARCHAR(150) NOT NULL,
  correo        VARCHAR(190) NOT NULL,
  canal         ENUM('formulario','correo','telefono') NOT NULL DEFAULT 'formulario',
  asunto        VARCHAR(200) NOT NULL,
  mensaje       VARCHAR(2000) NOT NULL,
  respuesta     VARCHAR(2000) NULL,
  respondido_por INT UNSIGNED NULL,
  respondido_en DATETIME      NULL,
  estado        ENUM('abierto','en_proceso','cerrado') NOT NULL DEFAULT 'abierto',
  creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_soporte_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,
  CONSTRAINT fk_soporte_respondido_por FOREIGN KEY (respondido_por) REFERENCES usuarios(id) ON DELETE SET NULL,
  KEY ix_soporte_estado_fecha (estado, creado_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS bitacora (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id  INT UNSIGNED NULL,
  accion      VARCHAR(60)   NOT NULL,
  detalle     VARCHAR(500)  NULL,
  ip          VARCHAR(45)   NULL,
  creado_en   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_bitacora_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,
  KEY ix_bitacora_usuario_fecha (usuario_id, creado_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS solicitudes (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id    INT UNSIGNED NOT NULL,
  tipo          VARCHAR(80)   NOT NULL,
  descripcion   VARCHAR(500)  NULL,
  estado        ENUM('pendiente','en_proceso','aprobada','rechazada','cancelada') NOT NULL DEFAULT 'pendiente',
  respuesta     VARCHAR(500)  NULL,
  creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_solicitudes_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
  KEY ix_solicitudes_usuario_fecha (usuario_id, creado_en),
  KEY ix_solicitudes_estado_fecha (estado, creado_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS conversaciones (
  id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_uno_id INT UNSIGNED NOT NULL,
  usuario_dos_id INT UNSIGNED NOT NULL,
  creado_en      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ultimo_mensaje_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_conv_usuario_uno FOREIGN KEY (usuario_uno_id) REFERENCES usuarios(id) ON DELETE CASCADE,
  CONSTRAINT fk_conv_usuario_dos FOREIGN KEY (usuario_dos_id) REFERENCES usuarios(id) ON DELETE CASCADE,
  UNIQUE KEY uq_conv_par (usuario_uno_id, usuario_dos_id),
  KEY ix_conv_usuario_dos (usuario_dos_id, ultimo_mensaje_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS mensajes (
  id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  conversacion_id INT UNSIGNED NOT NULL,
  remitente_id    INT UNSIGNED NOT NULL,
  contenido       VARCHAR(2000) NOT NULL,
  leido_en        DATETIME NULL,
  creado_en       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  CONSTRAINT fk_mensajes_conversacion FOREIGN KEY (conversacion_id) REFERENCES conversaciones(id) ON DELETE CASCADE,
  CONSTRAINT fk_mensajes_remitente FOREIGN KEY (remitente_id) REFERENCES usuarios(id) ON DELETE CASCADE,
  KEY ix_mensajes_conversacion_fecha (conversacion_id, creado_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS eventos (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  titulo        VARCHAR(150) NOT NULL,
  descripcion   VARCHAR(1000) NULL,
  categoria     ENUM('academico','profesional','egresados','taller','cultural','deportivo','otro') NOT NULL DEFAULT 'otro',
  lugar         VARCHAR(150) NULL,
  fecha_inicio  DATETIME NOT NULL,
  fecha_fin     DATETIME NULL,
  creado_por    INT UNSIGNED NULL,
  creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_eventos_creador FOREIGN KEY (creado_por) REFERENCES usuarios(id) ON DELETE SET NULL,
  KEY ix_eventos_fecha (fecha_inicio)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS eventos_favoritos (
  usuario_id   INT UNSIGNED NOT NULL,
  evento_id    INT UNSIGNED NOT NULL,
  creado_en    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  recordado_en DATETIME NULL,
  PRIMARY KEY (usuario_id, evento_id),
  CONSTRAINT fk_favevento_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
  CONSTRAINT fk_favevento_evento  FOREIGN KEY (evento_id)  REFERENCES eventos(id)  ON DELETE CASCADE,
  KEY ix_favevento_evento (evento_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS solicitudes_cuenta (
  id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  cedula         VARCHAR(120)      NULL, /* cifrada (AES-SIV) */
  nombre         VARCHAR(150)      NOT NULL,
  correo         VARCHAR(190)      NOT NULL,
  telefono       VARCHAR(40)       NULL,
  anio_promocion SMALLINT UNSIGNED NOT NULL,
  tecnico_id     INT UNSIGNED      NULL,
  mensaje        VARCHAR(500)      NULL,
  estado         ENUM('pendiente','aprobada','rechazada') NOT NULL DEFAULT 'pendiente',
  graduado_id    INT UNSIGNED      NULL,
  usuario_id     INT UNSIGNED      NULL,
  revisado_por   INT UNSIGNED      NULL,
  revisado_en    DATETIME          NULL,
  motivo_rechazo VARCHAR(300)      NULL,
  origen         ENUM('formulario','api') NOT NULL DEFAULT 'formulario',
  ip_origen      VARCHAR(45)       NULL,
  creado_en      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_soli_cuenta_tecnico  FOREIGN KEY (tecnico_id)   REFERENCES tecnicos(id)  ON DELETE SET NULL,
  CONSTRAINT fk_soli_cuenta_graduado FOREIGN KEY (graduado_id)  REFERENCES graduados(id) ON DELETE SET NULL,
  CONSTRAINT fk_soli_cuenta_usuario  FOREIGN KEY (usuario_id)   REFERENCES usuarios(id)  ON DELETE SET NULL,
  CONSTRAINT fk_soli_cuenta_revisor  FOREIGN KEY (revisado_por) REFERENCES usuarios(id)  ON DELETE SET NULL,

  KEY ix_soli_cuenta_estado_fecha (estado, creado_en),
  KEY ix_soli_cuenta_cedula (cedula),
  KEY ix_soli_cuenta_correo (correo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
