import { test, expect } from '@playwright/test';

test.describe('InputForm Autofocus', () => {
  test('should autofocus on the input textarea when the page loads', async ({ page }) => {
    await page.goto('/');

    const textarea = page.getByPlaceholder('Who won the Euro 2024 and scored the most goals?');

    // Check if the element is focused
    await expect(textarea).toBeFocused();
  });
});
