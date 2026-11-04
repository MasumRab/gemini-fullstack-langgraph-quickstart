import { test, expect } from '@playwright/test';

test.describe('InputForm Clear Button', () => {
  test('should show clear button when typing and clear input when clicked', async ({ page }) => {
    // Navigate to the app (handle redirect to /app/)
    await page.goto('/app/');

    // Find the textarea (using aria-label or placeholder as seen in code)
    const textarea = page.getByRole('textbox', { name: /chat input/i });

    // Ensure it's empty initially
    await expect(textarea).toBeEmpty();

    // Type something
    await textarea.fill('Hello World');

    // Verify clear button appears
    // The button has aria-label="Clear input"
    const clearButton = page.getByRole('button', { name: /clear input/i });
    await expect(clearButton).toBeVisible();

    // Click the clear button
    await clearButton.click();

    // Verify input is empty
    await expect(textarea).toBeEmpty();

    // Verify clear button disappears
    await expect(clearButton).not.toBeVisible();
  });

  test('should handle keyboard interaction (optional check if implemented, but good for verification)', async ({ page }) => {
     await page.goto('/app/');
     const textarea = page.getByRole('textbox', { name: /chat input/i });
     await textarea.fill('Testing keyboard');

     // Press Tab to focus the clear button (if it's next in tab order)
     // This depends on the DOM order. The clear button is after textarea.
     // Let's just try to tab and check focus.
     await textarea.press('Tab');

     // Verify the clear button is focused.
     // Note: The clear button is only rendered when there is text.
     const clearButton = page.getByRole('button', { name: /clear input/i });
     await expect(clearButton).toBeVisible();
     await expect(clearButton).toBeFocused();

     // Press Enter to activate
     await page.keyboard.press('Enter');

     // Verify cleared
     await expect(textarea).toBeEmpty();
  });
});
