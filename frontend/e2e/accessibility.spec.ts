import { test, expect } from '@playwright/test';

test.describe('Accessibility Checks', () => {
  test('should render the welcome screen footer with visible text', async ({ page }) => {
    await page.goto('/');

    const footer = page.getByRole('contentinfo');
    await expect(footer).toBeVisible();
    await expect(footer).toHaveText(/Powered by Google Gemini and LangChain LangGraph/);
  });
});
