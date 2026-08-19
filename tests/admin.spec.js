const { test, expect } = require('@playwright/test');
const { SESION_EGRESADO } = require('./ayudas');

test.describe('Tickets de soporte', () => {
  test('un mensaje de Contacto llega a la bandeja y se puede responder', async ({ page, browser }) => {
    const asunto = `Prueba automatica ${Date.now()}`;

    // El ticket lo crea un visitante sin cuenta.
    const visitante = await browser.newContext({ storageState: { cookies: [], origins: [] } });
    const paginaVisitante = await visitante.newPage();
    await paginaVisitante.goto('/contacto');
    await paginaVisitante.fill('form.form-soporte input[name="nombre"]', 'Visitante Prueba');
    await paginaVisitante.fill('form.form-soporte input[name="correo"]', 'visitante@example.com');
    await paginaVisitante.fill('form.form-soporte input[name="asunto"]', asunto);
    await paginaVisitante.fill('form.form-soporte textarea[name="mensaje"]', 'Este ticket lo creo una prueba automatica.');
    await paginaVisitante.click('form.form-soporte button[type="submit"]');
    await visitante.close();

    await page.goto(`/admin/soporte?q=${encodeURIComponent(asunto)}`);
    const ticket = page.locator('article.ticket').first();
    await expect(ticket).toContainText(asunto);
    await expect(ticket.locator('.pill')).toContainText(/abierto/i);

    await ticket.locator('textarea[name="respuesta"]').fill(
      'Gracias por escribirnos, ya revisamos tu caso y quedo resuelto.'
    );
    await ticket.getByRole('button', { name: /enviar respuesta y cerrar/i }).click();

    await expect(page.locator('.flash-messages')).toContainText(/respuesta enviada/i);
    await page.goto(`/admin/soporte?q=${encodeURIComponent(asunto)}`);
    await expect(page.locator('article.ticket').first()).toContainText(/respondido por/i);
  });

  test('un egresado no puede entrar a la bandeja', async ({ browser }) => {
    const contexto = await browser.newContext({ storageState: SESION_EGRESADO });
    const page = await contexto.newPage();
    await page.goto('/admin/soporte');
    await expect(page).not.toHaveURL(/\/admin\/soporte/);
    await contexto.close();
  });
});

test.describe('Paginación', () => {
  test('conserva los filtros al cambiar de página', async ({ page }) => {
    await page.goto('/?por_pagina=2&rol=egresado');

    const siguiente = page.locator('a.pag-link[rel="next"]');
    await expect(siguiente).toBeVisible();

    const href = await siguiente.getAttribute('href');
    expect(href).toContain('rol=egresado');
    expect(href).toContain('pagina=2');

    await siguiente.click();
    await expect(page.locator('.pag-info')).toContainText('Página 2');
    // el filtro sigue puesto
    await expect(page.locator('.filtros-form select[name="rol"]')).toHaveValue('egresado');
  });

  test('en la última página no ofrece una siguiente vacía', async ({ page }) => {
    await page.goto('/?por_pagina=2');

    const texto = await page.locator('.pag-info').textContent();
    const paginas = Number(texto.match(/de (\d+)/)[1]);

    await page.goto(`/?por_pagina=2&pagina=${paginas}`);
    await expect(page.locator('a.pag-link[rel="next"]')).toHaveCount(0);
    await expect(page.locator('.pag-link--inerte')).toBeVisible();
  });

  test('muestra el total real de registros', async ({ page }) => {
    await page.goto('/?por_pagina=2');
    await expect(page.locator('.pag-total')).toContainText(/\(\d+ en total\)/);
  });
});
