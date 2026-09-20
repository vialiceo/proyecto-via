/*
 * Migración: guardar el nombre de la solicitud en partes.
 *
 * El formulario de solicitud de cuenta ahora pide primer nombre y primer apellido
 * (obligatorios) y segundo nombre / segundo apellido (opcionales). Se guardan por
 * separado para emparejar contra el archivo de graduados por PALABRAS, sin depender
 * del orden (el archivo a veces trae los apellidos y nombres en columnas cambiadas).
 *
 * Idempotente a mano: si sale el error 1060 (Duplicate column name), ya estaba aplicada.
 */

ALTER TABLE solicitudes_cuenta
  ADD COLUMN primer_nombre    VARCHAR(60) NULL AFTER nombre,
  ADD COLUMN segundo_nombre   VARCHAR(60) NULL AFTER primer_nombre,
  ADD COLUMN primer_apellido  VARCHAR(60) NULL AFTER segundo_nombre,
  ADD COLUMN segundo_apellido VARCHAR(60) NULL AFTER primer_apellido;
