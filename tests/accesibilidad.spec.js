const { test, expect } = require('@playwright/test');

test.describe('Modales accesibles', () => {
  test('el modal declara su rol y atrapa el foco', async ({ page }) => {
    await page.goto('/usuarios/directorio');

    const modal = page.locator('#modalEgresado');
    await expect(modal).toHaveAttribute('role', 'dialog');
    await expect(modal).toHaveAttribute('aria-modal', 'true');

    await page.locator('.egresado-card').first().click();
    await expect(modal).toBeVisible();

    // el foco entra al modal
    const dentro = await page.evaluate(() =>
      document.getElementById('modalEgresado').contains(document.activeElement)
    );
    expect(dentro).toBe(true);

    // Escape lo cierra
    await page.keyboard.press('Escape');
    await expect(modal).toBeHidden();
  });

  test('con el modal abierto la página de atrás no se desplaza', async ({ page }) => {
    await page.goto('/usuarios/directorio');
    await page.locator('.egresado-card').first().click();

    await expect(page.locator('body')).toHaveClass(/modal-abierto/);
    await page.keyboard.press('Escape');
    await expect(page.locator('body')).not.toHaveClass(/modal-abierto/);
  });
});

test.describe('Páginas de error', () => {
  test('una URL que no existe muestra la página 404 propia', async ({ page }) => {
    const respuesta = await page.goto('/esta-ruta-no-existe');
    expect(respuesta.status()).toBe(404);
    await expect(page.locator('h1')).toHaveText('Página no encontrada');
    await expect(page.locator('.error-codigo')).toHaveText('404');
    await expect(page.getByRole('link', { name: /volver al inicio/i })).toBeVisible();
  });

  test('las rutas de API responden JSON, no HTML', async ({ request }) => {
    const r = await request.get('/api/v1/no-existe');
    expect(r.status()).toBe(404);
    expect(r.headers()['content-type']).toContain('application/json');
  });
});

test.describe('Menú en móvil', () => {
  test.skip(({ isMobile }) => !isMobile, 'solo aplica en móvil');

  test('el botón de menú es alcanzable y abre el panel', async ({ page }) => {
    await page.goto('/usuarios/perfil');

    const abrir = page.locator('#navAbrir');
    await expect(abrir).toBeVisible();

    const caja = await abrir.boundingBox();
    expect(caja.width).toBeGreaterThanOrEqual(44);
    expect(caja.height).toBeGreaterThanOrEqual(44);

    await abrir.click();
    await expect(page.locator('#sidebarNav')).toHaveClass(/open/);
    await expect(page.locator('#navFondo')).toBeVisible();

    // El cajón entra desde la IZQUIERDA con una transición de 0.28s: pasa de
    // x = -ancho (oculto) a x = 0 (abierto). Medir justo tras el clic da un
    // valor intermedio, así que expect.poll reintenta hasta que llega a 0.
    await expect
      .poll(async () => {
        const caja = await page.locator('#sidebarNav').boundingBox();
        return Math.round(caja.x);
      })
      .toBeGreaterThanOrEqual(0);

    const panel = await page.locator('#sidebarNav').boundingBox();
    const ancho = page.viewportSize().width;
    // el cajón queda completamente dentro de la pantalla
    expect(panel.x + panel.width).toBeLessThanOrEqual(ancho + 1);
    expect(panel.width).toBeGreaterThan(200);
  });
});
