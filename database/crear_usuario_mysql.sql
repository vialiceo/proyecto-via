-- ---------------------------------------------------------------------------
-- Crea la base y el usuario que usa la aplicación.
-- ---------------------------------------------------------------------------
-- Se corre UNA vez, conectado como root:
--
--   mysql -u root -p < database/crear_usuario_mysql.sql
--
-- ANTES de correrlo, cambia 'CAMBIA_ESTA_CLAVE' por una contraseña tuya
-- (las dos veces que aparece), y pon esa misma contraseña en el archivo .env,
-- en la línea MYSQL_PASSWORD=
--
-- ¿Por qué un usuario aparte y no root? Porque `via_app` solo puede tocar
-- `egresados`. Si alguien lograra inyectar SQL, no podría leer ni borrar otras
-- bases del servidor. Root puede hacer cualquier cosa.
-- ---------------------------------------------------------------------------

CREATE DATABASE IF NOT EXISTS egresados
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'via_app'@'localhost'
  IDENTIFIED BY 'CAMBIA_ESTA_CLAVE';

ALTER USER 'via_app'@'localhost'
  IDENTIFIED BY 'CAMBIA_ESTA_CLAVE';

-- Permisos de datos, nada de administración del servidor.
GRANT SELECT, INSERT, UPDATE, DELETE ON egresados.*
  TO 'via_app'@'localhost';

FLUSH PRIVILEGES;

SELECT 'Listo. Ahora corre schema.sql y datos.sql.' AS mensaje;
