-- ---------------------------------------------------------------------------
-- Migración: respuestas a los tickets de soporte
-- ---------------------------------------------------------------------------
--   mysql -u root -p egresados < database/migracion_soporte.sql
--
-- Se corre UNA sola vez. Si la repites, MySQL responde ERROR 1060
-- (Duplicate column name), que significa que ya estaba aplicada.
-- ---------------------------------------------------------------------------

SET NAMES utf8mb4;

ALTER TABLE soporte_tickets
  ADD COLUMN respuesta      VARCHAR(2000) NULL AFTER mensaje,
  ADD COLUMN respondido_por INT UNSIGNED  NULL AFTER respuesta,
  ADD COLUMN respondido_en  DATETIME      NULL AFTER respondido_por;

-- Quién contestó. ON DELETE SET NULL: si la cuenta del administrador se borra,
-- la respuesta se conserva (es historial de atención) pero pierde el autor.
ALTER TABLE soporte_tickets
  ADD CONSTRAINT fk_soporte_respondido_por
      FOREIGN KEY (respondido_por) REFERENCES usuarios(id) ON DELETE SET NULL;

-- La bandeja se ordena por fecha dentro de cada estado.
-- El índice ix_soporte_estado_fecha ya existe en schema.sql y cubre eso.
