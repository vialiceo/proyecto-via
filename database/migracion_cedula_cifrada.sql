/*
 * Migración: cifrado de la cédula por columna (AES-SIV determinista).
 *
 * 1) Ensancha las columnas de cédula para que quepa el texto cifrado
 * (una cédula cifrada en base64 ocupa ~36-48 caracteres).
 * 2) Después de correr esto, ejecuta el cifrado de los datos existentes con:
 * python -c "from cifrar_cedulas_existentes import migrar; migrar()"
 * (o el script equivalente que acompaña esta versión).
 *
 * Idempotente: si las columnas ya son VARCHAR(120), MySQL no se queja.
 */

ALTER TABLE usuarios           MODIFY COLUMN cedula VARCHAR(120) NULL;
ALTER TABLE graduados          MODIFY COLUMN cedula VARCHAR(120) NULL;
ALTER TABLE solicitudes_cuenta MODIFY COLUMN cedula VARCHAR(120) NULL;
