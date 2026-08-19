// Configuración de las pruebas end-to-end.  Se corren con:  npm test
//
// A diferencia de las pruebas de Python (que usan el test client de Flask y no
// abren navegador), estas manejan un Chromium de verdad: hacen clic, escriben
// en los formularios y comprueban lo que el usuario ve en pantalla.

const { defineConfig, devices } = require('@playwright/test');
const path = require('path');

const BASE = process.env.VIA_URL || 'http://127.0.0.1:5000';
const SESIONES = path.join(__dirname, 'tests/.sesiones');

module.exports = defineConfig({
  testDir: './tests',
  timeout: 30_000,
  expect: { timeout: 5_000 },

  // En serie, no en paralelo: todas las pruebas comparten la misma base MySQL
  // y varias escriben en ella. En paralelo se pisarían entre sí.
  fullyParallel: false,
  workers: 1,

  reporter: [['list'], ['html', { outputFolder: 'tests/reporte', open: 'never' }]],

  use: {
    baseURL: BASE,
    locale: 'es-CO',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },

  projects: [
    // Inicia sesión una vez y guarda las cookies; el resto de proyectos las
    // reutilizan. Sin esto la suite chocaba contra el límite de 10 logins
    // por minuto de /login.
    { name: 'setup', testMatch: /auth\.setup\.js/ },

    {
      name: 'publico',
      testMatch: /portada\.spec\.js|errores/,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'admin',
      testMatch: /admin\.spec\.js|accesibilidad\.spec\.js/,
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'], storageState: `${SESIONES}/admin.json` },
    },
    {
      name: 'egresado',
      testMatch: /cuenta\.spec\.js/,
      dependencies: ['setup'],
      use: { ...devices['Desktop Chrome'], storageState: `${SESIONES}/egresado.json` },
    },
    {
      name: 'movil',
      testMatch: /accesibilidad\.spec\.js|portada\.spec\.js/,
      dependencies: ['setup'],
      use: { ...devices['Pixel 5'], storageState: `${SESIONES}/admin.json` },
    },
  ],

  // Levanta Flask solo si no hay uno corriendo ya.
  webServer: {
    command: 'venv\Scripts\python.exe run.py',
    url: BASE,
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
