/*
 * ---------------------------------------------------------------------------
 * Datos iniciales de V.I.A (semilla mínima para arrancar)
 * ---------------------------------------------------------------------------
 * mysql -u root -p egresados < database/datos.sql
 *
 * Crea SOLO lo indispensable para que el sistema funcione desde cero:
 * 1. La cuenta de administrador.
 * 2. El catálogo de promociones (un año por promoción, 1967 a 2026).
 *
 * No incluye egresados, graduados ni técnicos de prueba: esos datos son
 * reales y se cargan desde el panel de administración o por importación.
 * ---------------------------------------------------------------------------
 */

SET NAMES utf8mb4;

/*
 * --- 1. Cuenta de administrador -------------------------------------------
 * Usuario: admin   Contraseña: CambiarAhora2026!
 * forzar_cambio_password = 1 obliga a cambiarla en el primer ingreso.
 */
INSERT INTO usuarios
  (nombre, correo, usuario, password_hash, rol, estado, forzar_cambio_password)
VALUES
  ('Administración V.I.A', 'admin@liceotame.edu.co', 'admin',
   'scrypt:32768:8:1$iEf5LmsMadNgThMc$9d716cd9501b60e1e08d4af4a119b6123761c65cddb41187f387a7888ab745ab677b01f37e38c862e2b66e47da6ad42d55cddf580cea67222e638c15b095c899',
   'administrador', 'activo', 1)
ON DUPLICATE KEY UPDATE nombre = VALUES(nombre);

/*
 * --- 2. Catálogo de promociones (1967 a 2026) -----------------------------
 * Un año por promoción. Las modalidades/técnicos se agregan después.
 */
INSERT INTO promociones (anio) VALUES
  (1967),
  (1968),
  (1969),
  (1970),
  (1971),
  (1972),
  (1973),
  (1974),
  (1975),
  (1976),
  (1977),
  (1978),
  (1979),
  (1980),
  (1981),
  (1982),
  (1983),
  (1984),
  (1985),
  (1986),
  (1987),
  (1988),
  (1989),
  (1990),
  (1991),
  (1992),
  (1993),
  (1994),
  (1995),
  (1996),
  (1997),
  (1998),
  (1999),
  (2000),
  (2001),
  (2002),
  (2003),
  (2004),
  (2005),
  (2006),
  (2007),
  (2008),
  (2009),
  (2010),
  (2011),
  (2012),
  (2013),
  (2014),
  (2015),
  (2016),
  (2017),
  (2018),
  (2019),
  (2020),
  (2021),
  (2022),
  (2023),
  (2024),
  (2025),
  (2026)
ON DUPLICATE KEY UPDATE anio = VALUES(anio);
