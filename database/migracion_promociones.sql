/*
 * ---------------------------------------------------------------------------
 * Migración: catálogo de promociones (años de egreso)
 * ---------------------------------------------------------------------------
 * mysql -u root -p egresados < database/migracion_promociones.sql
 *
 * Crea la tabla `promociones` y la llena con un año por promoción desde 1967
 * (fundación del Liceo) hasta 2026. La página "Ver promociones" las muestra
 * todas, aunque todavía no tengan egresados registrados.
 *
 * Las modalidades/técnicos de cada promoción se agregan después, cuando se
 * tengan los datos reales; por eso esta tabla solo guarda el año por ahora.
 *
 * Se corre UNA sola vez. Si la repites, el INSERT dará error 1062 (Duplicate
 * entry) porque los años ya están; no hay daño.
 * ---------------------------------------------------------------------------
 */

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS promociones (
  anio        SMALLINT UNSIGNED PRIMARY KEY, /* el año identifica la promoción */
  descripcion VARCHAR(200) NULL, /* opcional (p. ej. lema del año) */
  activa      TINYINT(1) NOT NULL DEFAULT 1, /* se puede ocultar sin borrarla */
  creado_en   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

/* Un año por promoción, de 1967 a 2026. */
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
  (2026);
