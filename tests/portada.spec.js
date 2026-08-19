const { test, expect } = require('@playwright/test');

test.describe('Portada pública', () => {
  // La portada es lo que ve alguien SIN cuenta. Con sesión, `/` muestra el
  // panel, así que se limpia el estado heredado del proyecto.
  test.use({ storageState: { cookies: [], origins: [] } });
  test('un visitante sin cuenta ve la portada, no la página de ayuda', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/V\.I\.A/);
    await expect(page.locator('h1.hero-titulo')).toHaveText('V.I.A');
    await expect(page.getByRole('link', { name: /solicitar mi cuenta/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /ya tengo cuenta/i })).toBeVisible();
  });

  test('la portada explica cómo se obtiene una cuenta', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: /la institución verifica/i })).toBeVisible();
    await expect(page.locator('.pasos-lista li')).toHaveCount(3);
  });

  test('tiene exactamente un h1 y la jerarquía no salta niveles', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toHaveCount(1);

    const niveles = await page.$$eval('h1,h2,h3,h4,h5,h6', (hs) =>
      hs.map((h) => Number(h.tagName[1]))
    );
    const saltos = niveles.filter((n, i) => i > 0 && n - niveles[i - 1] > 1);
    expect(saltos).toEqual([]);
  });

  test('el escudo es un botón que lleva al sitio de la institución', async ({ page }) => {
    await page.goto('/');
    const escudo = page.locator('.topbar-shield-link');
    await expect(escudo).toHaveAttribute('href', 'https://ieliceotame.edu.co');
    await expect(escudo).toHaveAttribute('target', '_blank');
    // rel=noopener evita que la pestaña nueva pueda manipular la original
    await expect(escudo).toHaveAttribute('rel', /noopener/);
  });

  test('no se desborda horizontalmente', async ({ page }) => {
    await page.goto('/');
    const desborde = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth
    );
    expect(desborde).toBeLessThanOrEqual(1);
  });
});
