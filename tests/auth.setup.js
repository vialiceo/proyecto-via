// Inicia sesión UNA sola vez por rol y guarda la cookie en disco.
//
// Antes cada prueba hacía su propio login y la suite chocaba contra el límite
// de "10 por minuto" de /login: a partir de la sexta prueba el servidor
// respondía 429 y las pruebas fallaban por una razón que no tenía nada que ver
// con lo que querían comprobar. El límite es correcto —es una defensa contra
// fuerza bruta—, así que lo que había que cambiar eran las pruebas.

const { test: setup, expect } = require('@playwright/test');
const path = require('path');

const CUENTAS = {
  admin: { usuario: 'admin', contrasena: 'CambiarAhora2026!' },
  egresado: { usuario: 'jgomez', contrasena: 'Egresado123!' },
};

for (const [rol, cuenta] of Object.entries(CUENTAS)) {
  setup(`sesion de ${rol}`, async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[name="usuario"]', cuenta.usuario);
    await page.fill('input[name="contrasena"]', cuenta.contrasena);
    await page.click('button[type="submit"]');
    await page.waitForURL((url) => !url.pathname.startsWith('/login'));

    // Si el login fallara, seguiríamos en /login y guardaríamos una sesión
    // vacía: mejor romper aquí con un mensaje claro.
    await expect(page).not.toHaveURL(/\/login/);

    await page.context().storageState({
      path: path.join(__dirname, `.sesiones/${rol}.json`),
    });
  });
}
