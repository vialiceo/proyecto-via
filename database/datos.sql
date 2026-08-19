SET NAMES utf8mb4;

INSERT INTO tecnicos (nombre) VALUES
  ('Técnico en Sistemas'),
  ('Técnico en Contabilidad y Finanzas'),
  ('Técnico en Gestión Empresarial'),
  ('Técnico en Salud Ocupacional'),
  ('Técnico Agropecuario')
ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);

INSERT INTO graduados (cedula, nombre, anio_promocion, tecnico_id, libro_acta) VALUES
  ('1116801234', 'Julián Gómez',    2019, (SELECT id FROM tecnicos WHERE nombre = 'Técnico en Sistemas'),                 'L-2019-014'),
  ('1116805566', 'Camila Rojas',    2019, (SELECT id FROM tecnicos WHERE nombre = 'Técnico en Salud Ocupacional'),        'L-2019-031'),
  ('1116809988', 'Mariana López',   2021, (SELECT id FROM tecnicos WHERE nombre = 'Técnico en Gestión Empresarial'),      'L-2021-007'),
  ('1116812345', 'Andrés Peña',     2023, (SELECT id FROM tecnicos WHERE nombre = 'Técnico Agropecuario'),                'L-2023-022'),
  ('1116803311', 'Laura Martínez',  2019, (SELECT id FROM tecnicos WHERE nombre = 'Técnico en Contabilidad y Finanzas'),  'L-2019-045'),
  ('1116807722', 'Sergio Bautista', 2021, (SELECT id FROM tecnicos WHERE nombre = 'Técnico en Sistemas'),                 'L-2021-019'),
  ('1116811100', 'Diana Quintero',  2023, (SELECT id FROM tecnicos WHERE nombre = 'Técnico en Gestión Empresarial'),      'L-2023-008'),
  (NULL,         'Hernán Salcedo',  1985, NULL,                                                                          'L-1985-003')
ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);

INSERT INTO usuarios
  (nombre, correo, usuario, password_hash, rol, estado, forzar_cambio_password)
VALUES
  ('Administración V.I.A', 'admin@liceotame.edu.co', 'admin',
   'scrypt:32768:8:1$iEf5LmsMadNgThMc$9d716cd9501b60e1e08d4af4a119b6123761c65cddb41187f387a7888ab745ab677b01f37e38c862e2b66e47da6ad42d55cddf580cea67222e638c15b095c899',
   'administrador', 'activo', 1)
ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);

INSERT INTO usuarios
  (cedula, graduado_id, nombre, correo, usuario, password_hash, rol, estado, anio_promocion, tecnico_id, forzar_cambio_password)
SELECT g.cedula, g.id, g.nombre, d.correo, d.usuario,
       'scrypt:32768:8:1$n32V5ytLkbOaa9Ov$b7faa2e42980d45d53dd8668f49404ad981d5da2e0a3cb3503ded811fde66c805f05c326f2bf7001ac621bb57da5df2fe25c1bcd6653832af500ddd9d02b8405',
       'egresado', 'activo', g.anio_promocion, g.tecnico_id, 1
FROM graduados g
JOIN (
  SELECT '1116801234' AS cedula, 'jgomez@example.com' AS correo, 'jgomez' AS usuario
  UNION ALL SELECT '1116805566', 'crojas@example.com', 'crojas'
  UNION ALL SELECT '1116809988', 'mlopez@example.com', 'mlopez'
  UNION ALL SELECT '1116812345', 'apena@example.com',  'apena'
) d ON d.cedula = g.cedula
ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);

INSERT INTO perfil_extendido (usuario_id, profesion, lugar_residencia, lugar_estudio, fecha_nacimiento, frase)
SELECT id, 'Desarrollador de software', 'Tame, Arauca', 'Universidad Nacional de Colombia', '2001-04-12',
       'Gracias Liceo Tame por los años que me formaron.'
FROM usuarios WHERE usuario = 'jgomez'
ON DUPLICATE KEY UPDATE profesion = VALUES(profesion), frase = VALUES(frase);

INSERT INTO contactos (usuario_id, tipo, valor, es_principal)
SELECT id, 'whatsapp', '+57 300 000 0000', 1 FROM usuarios WHERE usuario = 'jgomez';

INSERT INTO solicitudes (usuario_id, tipo, descripcion, estado)
SELECT id, 'Certificado de egresado', 'Necesito el certificado para un proceso laboral.', 'pendiente'
FROM usuarios WHERE usuario = 'jgomez';

INSERT INTO eventos (titulo, descripcion, categoria, lugar, fecha_inicio, creado_por)
SELECT 'Encuentro de Egresados 2026', 'Reencuéntrate con tus compañeros de promoción.', 'egresados',
       'Auditorio Principal, Liceo Tame', DATE_ADD(NOW(), INTERVAL 20 DAY), id
FROM usuarios WHERE usuario = 'admin';

INSERT INTO eventos (titulo, descripcion, categoria, lugar, fecha_inicio, creado_por)
SELECT 'Feria de Empleo y Networking', 'Conecta con empresas aliadas de la región.', 'profesional',
       'Plazoleta Central', DATE_ADD(NOW(), INTERVAL 35 DAY), id
FROM usuarios WHERE usuario = 'admin';

INSERT INTO conversaciones (usuario_uno_id, usuario_dos_id)
SELECT LEAST(a.id, b.id), GREATEST(a.id, b.id)
FROM usuarios a, usuarios b
WHERE a.usuario = 'jgomez' AND b.usuario = 'mlopez'
ON DUPLICATE KEY UPDATE usuario_uno_id = VALUES(usuario_uno_id);

INSERT INTO solicitudes_cuenta
  (cedula, nombre, correo, telefono, anio_promocion, tecnico_id, mensaje, estado, graduado_id, origen)
SELECT '1116803311', 'Laura Martínez', 'lmartinez@example.com', '+57 310 111 2233', 2019,
       (SELECT id FROM tecnicos WHERE nombre = 'Técnico en Contabilidad y Finanzas'),
       'Quiero acceder a mi perfil de egresada para actualizar mis datos.',
       'pendiente', (SELECT id FROM graduados WHERE cedula = '1116803311'), 'formulario';

INSERT INTO solicitudes_cuenta
  (cedula, nombre, correo, telefono, anio_promocion, tecnico_id, mensaje, estado, graduado_id, origen)
VALUES
  ('1116899999', 'Persona No Registrada', 'desconocido@example.com', NULL, 2015, NULL,
   'Creo que me gradué ese año pero no estoy seguro.', 'pendiente', NULL, 'formulario');

INSERT INTO mensajes (conversacion_id, remitente_id, contenido)
SELECT c.id, u.id, '¡Hola! ¿Cómo te ha ido después de graduarte?'
FROM conversaciones c
JOIN usuarios u ON u.usuario = 'mlopez'
JOIN usuarios j ON j.usuario = 'jgomez'
WHERE c.usuario_uno_id = LEAST(u.id, j.id) AND c.usuario_dos_id = GREATEST(u.id, j.id);
