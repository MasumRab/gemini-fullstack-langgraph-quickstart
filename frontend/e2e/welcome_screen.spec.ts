import { test, expect } from '@playwright/test';

test.describe('Welcome Screen', () => {
  test('should verify footer visibility and text', async ({ page }) => {
    await page.goto('/app/');

    // The footer has role="contentinfo"
    const footer = page.getByRole('contentinfo');

    await expect(footer).toBeVisible();
    await expect(footer).toContainText('Powered by Google Gemini and LangChain LangGraph');
  });
});
