/*
 * ---------------------------------------------------------------------------
 * Migración: campos públicos del perfil
 * ---------------------------------------------------------------------------
 * mysql -u root -p egresados < database/migracion_campos_publicos.sql
 *
 * Añade a perfil_extendido la columna `campos_publicos`: una lista separada por
 * comas con los campos que el egresado decidió mostrar en su tarjeta del
 * directorio (por ejemplo "profesion,lugar_residencia,correo"). El
 * administrador ve todos los campos aunque no estén en la lista.
 *
 * Se corre UNA sola vez. Si la repites, MySQL responde ERROR 1060 (Duplicate
 * column name), que significa que ya estaba aplicada.
 * ---------------------------------------------------------------------------
 */

SET NAMES utf8mb4;

ALTER TABLE perfil_extendido
  ADD COLUMN campos_publicos VARCHAR(255) NOT NULL DEFAULT 'profesion,frase' AFTER frase;
