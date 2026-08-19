// Rutas de las sesiones guardadas por auth.setup.js
const path = require('path');

const SESION_ADMIN = path.join(__dirname, '.sesiones/admin.json');
const SESION_EGRESADO = path.join(__dirname, '.sesiones/egresado.json');

// Cédula al azar para que cada corrida cree una solicitud nueva y no choque
// con el UNIQUE de la tabla.
function cedulaAlAzar() {
  return String(Math.floor(1000000000 + Math.random() * 8999999999));
}

module.exports = { SESION_ADMIN, SESION_EGRESADO, cedulaAlAzar };
