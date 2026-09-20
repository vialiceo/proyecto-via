
/*Migración: eventos favoritos (recordatorios por correo)

mysql -u root -p egresados < database/migracion_eventos_favoritos.sql

Guarda qué eventos marcó como favorito cada usuario. El día del evento, una
tarea programada (enviar_recordatorios.py) le manda un correo recordándole
que asista. `recordado_en` evita que se envíe el mismo recordatorio dos veces.

Se corre UNA sola vez. Si la repites, MySQL responde ERROR 1050 (Table
already exists): significa que ya estaba aplicada.*/


SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS eventos_favoritos (
  usuario_id   INT UNSIGNED NOT NULL,
  evento_id    INT UNSIGNED NOT NULL,
  creado_en    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  recordado_en DATETIME NULL, /* cuándo se envió el recordatorio */

  PRIMARY KEY (usuario_id, evento_id), /* un favorito por persona y evento */
  CONSTRAINT fk_favevento_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
  CONSTRAINT fk_favevento_evento  FOREIGN KEY (evento_id)  REFERENCES eventos(id)  ON DELETE CASCADE,
  KEY ix_favevento_evento (evento_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
