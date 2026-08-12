SET NAMES utf8mb4;

INSERT INTO tecnicos (nombre) VALUES
  ('Técnico en Sistemas'),
  ('Técnico en Contabilidad y Finanzas'),
  ('Técnico en Gestión Empresarial'),
  ('Técnico en Salud Ocupacional'),
  ('Técnico Agropecuario')
ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);

INSERT INTO usuarios
  (nombre, correo, usuario, password_hash, rol, estado, forzar_cambio_password)
VALUES
  ('Administración V.I.A', 'admin@liceotame.edu.co', 'admin',
   'scrypt:32768:8:1$WKkEWXDJxgtxTvvi$79b00b0d5d117b10476a2c485b4346658eb25d791f05aacc01c8d858e4318c54cd4a9e06c923981b24747fe6c2db927eb4352ec1d220a820b7a89d6764436a4d',
   'administrador', 'activo', 1)
ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);

INSERT INTO usuarios
  (nombre, correo, usuario, password_hash, rol, estado, anio_promocion, tecnico_id, forzar_cambio_password)
VALUES
  ('Julián Gómez', 'jgomez@example.com', 'jgomez',
   'scrypt:32768:8:1$n32V5ytLkbOaa9Ov$b7faa2e42980d45d53dd8668f49404ad981d5da2e0a3cb3503ded811fde66c805f05c326f2bf7001ac621bb57da5df2fe25c1bcd6653832af500ddd9d02b8405',
   'egresado', 'activo', 2019, (SELECT id FROM tecnicos WHERE nombre = 'Técnico en Sistemas'), 1),
  ('Camila Rojas', 'crojas@example.com', 'crojas',
   'scrypt:32768:8:1$n32V5ytLkbOaa9Ov$b7faa2e42980d45d53dd8668f49404ad981d5da2e0a3cb3503ded811fde66c805f05c326f2bf7001ac621bb57da5df2fe25c1bcd6653832af500ddd9d02b8405',
   'egresado', 'activo', 2019, (SELECT id FROM tecnicos WHERE nombre = 'Técnico en Salud Ocupacional'), 1),
  ('Mariana López', 'mlopez@example.com', 'mlopez',
   'scrypt:32768:8:1$n32V5ytLkbOaa9Ov$b7faa2e42980d45d53dd8668f49404ad981d5da2e0a3cb3503ded811fde66c805f05c326f2bf7001ac621bb57da5df2fe25c1bcd6653832af500ddd9d02b8405',
   'egresado', 'activo', 2021, (SELECT id FROM tecnicos WHERE nombre = 'Técnico en Gestión Empresarial'), 1),
  ('Andrés Peña', 'apena@example.com', 'apena',
   'scrypt:32768:8:1$n32V5ytLkbOaa9Ov$b7faa2e42980d45d53dd8668f49404ad981d5da2e0a3cb3503ded811fde66c805f05c326f2bf7001ac621bb57da5df2fe25c1bcd6653832af500ddd9d02b8405',
   'egresado', 'activo', 2023, (SELECT id FROM tecnicos WHERE nombre = 'Técnico Agropecuario'), 1)
ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);

INSERT INTO perfil_extendido (usuario_id, profesion, lugar_residencia, lugar_estudio, fecha_nacimiento, frase)
SELECT id, 'Desarrollador de software', 'Tame, Arauca', 'Universidad Nacional de Colombia', '2001-04-12',
       'Gracias Liceo Tame por los años que me formaron.'
FROM usuarios WHERE usuario = 'jgomez'
ON DUPLICATE KEY UPDATE profesion = VALUES(profesion), frase = VALUES(frase);

INSERT INTO contactos (usuario_id, tipo, valor, es_principal)
SELECT id, 'whatsapp', '+57 300 000 0000', 1 FROM usuarios WHERE usuario = 'jgomez';
