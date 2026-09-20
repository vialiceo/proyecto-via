/*
 * ---------------------------------------------------------------------------
 * Migración: archivo de graduados + solicitudes de cuenta
 * ---------------------------------------------------------------------------
 * Solo hace falta si YA tienes una base `egresados` con datos.
 *
 * `database/schema.sql` usa CREATE TABLE IF NOT EXISTS, así que al volverlo a
 * correr sí crea las tablas nuevas (graduados, solicitudes_cuenta) pero NO
 * agrega las columnas `cedula` y `graduado_id` a una tabla `usuarios` que ya
 * existía. Este archivo hace esa parte.
 *
 * mysql -u root -p egresados < database/migracion_graduados.sql
 *
 * Se corre UNA sola vez. Si lo repites, MySQL responderá:
 * ERROR 1060 (Duplicate column name)  -> la columna ya estaba
 * ERROR 1061 (Duplicate key name)     -> el índice ya estaba
 * Ambos significan que la migración ya se había aplicado; no hay daño.
 *
 * En una base nueva no uses este archivo: corre schema.sql y ya queda todo.
 * ---------------------------------------------------------------------------
 */

SET NAMES utf8mb4;

/*
 * 1. Tablas nuevas ----------------------------------------------------------
 * Van primero porque `usuarios.graduado_id` apunta a `graduados.id`.
 */

CREATE TABLE IF NOT EXISTS graduados (
  id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  cedula         VARCHAR(20)       NULL,
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

/*
 * 2. Columnas nuevas en `usuarios` ------------------------------------------
 * Las dos son NULL: las cuentas que ya existen se quedan sin cédula y sin
 * enlace al archivo hasta que un administrador las complete a mano. Por eso
 * no se pueden declarar NOT NULL.
 */

ALTER TABLE usuarios
  ADD COLUMN cedula      VARCHAR(20)  NULL AFTER id,
  ADD COLUMN graduado_id INT UNSIGNED NULL AFTER cedula;

/*
 * UNIQUE con valores NULL: MySQL permite muchas filas en NULL dentro de un
 * índice UNIQUE, así que esto no choca con las cuentas viejas sin cédula.
 */
ALTER TABLE usuarios
  ADD UNIQUE KEY uq_usuarios_cedula (cedula),
  ADD UNIQUE KEY uq_usuarios_graduado (graduado_id),
  ADD CONSTRAINT fk_usuarios_graduado FOREIGN KEY (graduado_id) REFERENCES graduados(id) ON DELETE SET NULL;

/*
 * 3. Bandeja de solicitudes -------------------------------------------------
 * Va al final porque tiene llaves foráneas hacia `graduados` y `usuarios`.
 */

CREATE TABLE IF NOT EXISTS solicitudes_cuenta (
  id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  cedula         VARCHAR(20)       NOT NULL,
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

/*
 * 4. Comprobación -----------------------------------------------------------
 * Descomenta para confirmar que quedó aplicada:
 * SHOW COLUMNS FROM usuarios LIKE 'cedula';
 * SHOW COLUMNS FROM usuarios LIKE 'graduado_id';
 * SHOW TABLES LIKE 'graduados';
 * SHOW TABLES LIKE 'solicitudes_cuenta';
 */
