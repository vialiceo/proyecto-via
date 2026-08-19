const { test, expect } = require('@playwright/test');
const { SESION_ADMIN, cedulaAlAzar } = require('./ayudas');

test.describe('Solicitud y creación de cuenta', () => {
  // El formulario es público: sin sesión.
  test.use({ storageState: { cookies: [], origins: [] } });
  test('el formulario público pide cédula, nombre y correo', async ({ page }) => {
    await page.goto('/solicitar-cuenta');
    await expect(page.locator('input[name="cedula"]')).toBeVisible();
    await expect(page.locator('input[name="nombre"]')).toBeVisible();
    await expect(page.locator('input[name="correo"]')).toBeVisible();
    await expect(page.locator('input[name="anio_promocion"]')).toBeVisible();
  });

  test('una solicitud válida entra a la bandeja del administrador', async ({ page, browser }) => {
    const cedula = cedulaAlAzar();
    const nombre = `Egresado Prueba ${cedula.slice(-4)}`;

    await page.goto('/solicitar-cuenta');
    await page.fill('input[name="cedula"]', cedula);
    await page.fill('input[name="nombre"]', nombre);
    await page.fill('input[name="correo"]', `prueba.${cedula}@example.com`);
    await page.fill('input[name="anio_promocion"]', '2019');
    const respuesta = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/solicitar-cuenta') && r.request().method() === 'POST'),
      page.click('button[type="submit"]'),
    ]).then(([r]) => r);

    // Mismo límite de 5 por hora que en la prueba de validación.
    test.skip(respuesta.status() === 429, 'Cuota de 5 solicitudes por hora agotada');

    await expect(page.locator('.flash-messages')).toContainText(/solicitud/i);

    // El administrador la ve. Se abre un contexto aparte con la sesión de
    // admin en vez de iniciar sesión otra vez.
    const contextoAdmin = await browser.newContext({ storageState: SESION_ADMIN });
    const paginaAdmin = await contextoAdmin.newPage();
    await paginaAdmin.goto(`/admin/solicitudes-cuenta?q=${cedula}`);
    await expect(paginaAdmin.getByText(nombre)).toBeVisible();
    await contextoAdmin.close();
  });

  test('rechaza datos inválidos sin crear nada', async ({ page }) => {
    await page.goto('/solicitar-cuenta');
    await page.fill('input[name="cedula"]', 'abc');
    await page.fill('input[name="nombre"]', 'X');
    await page.fill('input[name="correo"]', 'no-es-un-correo');
    await page.fill('input[name="anio_promocion"]', '1800');
    const respuesta = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/solicitar-cuenta') && r.request().method() === 'POST'),
      page.click('button[type="submit"]'),
    ]).then(([r]) => r);

    // El formulario admite 5 envíos por hora y por IP. Si se agotó la cuota,
    // el servidor responde 429 y la prueba no puede comprobar la validación:
    // no es un fallo del formulario, así que se marca como omitida.
    test.skip(respuesta.status() === 429, 'Cuota de 5 solicitudes por hora agotada');

    await expect(page.locator('.flash--error').first()).toBeVisible();
  });
});

test.describe('Perfil editable', () => {
  test('un egresado edita su perfil y los cambios quedan guardados', async ({ page }) => {
    await page.goto('/usuarios/perfil');

    await page.click('#btnEditarPerfil');

    const marca = `Probado ${Date.now()}`;
    await page.fill('input[name="profesion"]', marca);
    await page.fill('input[name="lugar_residencia"]', 'Tame, Arauca');
    await page.click('button[type="submit"]');

    await expect(page.locator('.flash-messages')).toContainText(/perfil actualizado/i);
    await expect(page.getByText(marca)).toBeVisible();
  });

  test('puede cambiar su propio correo', async ({ page }) => {
    await page.goto('/usuarios/perfil');
    await page.click('#btnEditarPerfil');

    const nuevo = `jgomez.${Date.now()}@example.com`;
    await page.fill('input[name="correo"]', nuevo);
    await page.click('button[type="submit"]');
    await expect(page.locator('.flash-messages')).toContainText(nuevo);

    // se devuelve al original para no dejar la base sucia
    await page.click('#btnEditarPerfil');
    await page.fill('input[name="correo"]', 'jgomez@example.com');
    await page.click('button[type="submit"]');
  });

  test('no deja usar el correo de otra cuenta', async ({ page }) => {
    await page.goto('/usuarios/perfil');
    await page.click('#btnEditarPerfil');
    await page.fill('input[name="correo"]', 'admin@liceotame.edu.co');
    await page.click('button[type="submit"]');
    await expect(page.locator('.flash--error')).toContainText(/ya está registrado/i);
  });

  test('el campo de foto acepta solo imágenes y dice el tamaño', async ({ page }) => {
    await page.goto('/usuarios/perfil');
    await expect(page.locator('input[name="foto"]')).toHaveAttribute(
      'accept', '.png,.jpg,.jpeg,.webp'
    );
    await expect(page.locator('.foto-ayuda')).toContainText(/400×400/);
  });
});
