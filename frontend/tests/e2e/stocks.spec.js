import { test, expect } from '@playwright/test';

test.describe('Stock Portfolio E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display page title and header', async ({ page }) => {
    await expect(page).toHaveTitle(/Stock Portfolio/);
    await expect(page.locator('h1')).toHaveText('Stock Portfolio');
  });

  test('should load and display stock cards', async ({ page }) => {
    // Wait for stocks to load
    await page.waitForSelector('[data-testid="stocks-grid"]');
    
    // Check that stock cards are present
    const stockCards = page.locator('[data-testid="stock-card"]');
    await expect(stockCards).toHaveCount(6); // We have 6 stocks in database
    
    // Verify each stock card has name and price
    for (let i = 0; i < 6; i++) {
      const card = stockCards.nth(i);
      await expect(card.locator('[data-testid="stock-name"]')).toBeVisible();
      await expect(card.locator('[data-testid="stock-price"]')).toBeVisible();
    }
  });

  test('should display correct stock information', async ({ page }) => {
    // Wait for stocks to load
    await page.waitForSelector('[data-testid="stocks-grid"]');
    
    // Check for specific stock names (seeded data)
    const stockNames = page.locator('[data-testid="stock-name"]');
    await expect(stockNames).toContainText(['Apple Inc', 'Microsoft Corporation', 'NVDA Corporation']);
    
    // Check that prices are formatted correctly (contains $ symbol)
    const stockPrices = page.locator('[data-testid="stock-price"]');
    const priceCount = await stockPrices.count();
    
    for (let i = 0; i < priceCount; i++) {
      const priceText = await stockPrices.nth(i).textContent();
      expect(priceText).toMatch(/^\$\d+\.\d{2}$/); // Format: $123.45
    }
  });

  test('should show total stock count in header', async ({ page }) => {
    // Wait for stocks to load
    await page.waitForSelector('[data-testid="stocks-grid"]');
    
    // Check total count display
    await expect(page.locator('.app-header p')).toHaveText('Total stocks: 6');
  });

  test('should handle loading state', async ({ page }) => {
    // Intercept the API call to delay it
    await page.route('**/stocks', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      route.continue();
    });
    
    await page.goto('/');
    
    // Check loading state
    await expect(page.locator('.loading-container')).toBeVisible();
    await expect(page.locator('.loading-spinner')).toBeVisible();
    await expect(page.locator('text=Loading stocks...')).toBeVisible();
    
    // Wait for loading to complete
    await page.waitForSelector('[data-testid="stocks-grid"]');
    await expect(page.locator('.loading-container')).not.toBeVisible();
  });

  test('should handle API error gracefully', async ({ page }) => {
    // Intercept the API call to simulate error
    await page.route('**/stocks', async (route) => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal Server Error' })
      });
    });
    
    await page.goto('/');
    
    // Check error state
    await expect(page.locator('.error-container')).toBeVisible();
    await expect(page.locator('.error-message')).toContainText('HTTP error! status: 500');
    await expect(page.locator('.retry-button')).toBeVisible();
  });

  test('should verify stock card styling and layout', async ({ page }) => {
    // Wait for stocks to load
    await page.waitForSelector('[data-testid="stocks-grid"]');
    
    // Check grid layout
    const stocksGrid = page.locator('[data-testid="stocks-grid"]');
    await expect(stocksGrid).toHaveCSS('display', 'grid');
    
    // Check stock card styling
    const stockCard = page.locator('[data-testid="stock-card"]').first();
    await expect(stockCard).toHaveCSS('border', '1px solid rgb(224, 224, 224)');
    await expect(stockCard).toHaveCSS('border-radius', '8px');
    
    // Check responsive behavior
    await page.setViewportSize({ width: 800, height: 600 });
    await expect(stocksGrid).toBeVisible();
  });

  test('should verify stocks are sorted alphabetically', async ({ page }) => {
    // Wait for stocks to load
    await page.waitForSelector('[data-testid="stocks-grid"]');
    
    // Get all stock names
    const stockNames = page.locator('[data-testid="stock-name"]');
    const names = await stockNames.allTextContents();
    
    // Verify alphabetical order
    const sortedNames = [...names].sort();
    expect(names).toEqual(sortedNames);
  });
});