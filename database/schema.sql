SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS tecnicos (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  nombre        VARCHAR(120) NOT NULL,
  activo        TINYINT(1)   NOT NULL DEFAULT 1,
  creado_en     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_tecnicos_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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

  UNIQUE KEY uq_usuarios_correo (correo),
  UNIQUE KEY uq_usuarios_usuario (usuario),
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
  estado        ENUM('abierto','en_proceso','cerrado') NOT NULL DEFAULT 'abierto',
  creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  CONSTRAINT fk_soporte_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,
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

SET FOREIGN_KEY_CHECKS = 1;
