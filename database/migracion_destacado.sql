/*
 * Migración: marcar egresados como "destacados" desde el directorio.
 *
 * La administración puede resaltar a un egresado (imagen 2, "DESTACAR ALUMNO").
 * El egresado destacado aparece con una insignia dorada en su tarjeta y en el
 * detalle. Es un simple interruptor 0/1 sobre la fila del usuario.
 *
 * Idempotente a mano: si al correrla sale el error 1060 (Duplicate column name
 * 'destacado'), significa que la columna ya existe y puedes ignorarlo.
 */

ALTER TABLE usuarios
  ADD COLUMN destacado TINYINT(1) NOT NULL DEFAULT 0 AFTER foto;

/* Índice para poder listar rápido a los destacados si algún día hace falta. */
ALTER TABLE usuarios
  ADD KEY ix_usuarios_destacado (destacado);
