# PyGo E2E Tests

End-to-end tests using Playwright.

## Prerequisites

- Node.js 18+
- Python 3.9+
- A running PyGo application

## Installation

```bash
cd tests
npm install
npx playwright install
```

## Running Tests

### Run all tests
```bash
npm test
```

### Run tests in headed mode (with browser visible)
```bash
npm run test:headed
```

### Run tests in debug mode
```bash
npm run test:debug
```

### Run tests with UI
```bash
npm run test:ui
```

### Run specific test file
```bash
npx playwright test blog.spec.js
```

### Run tests for a specific browser
```bash
npx playwright test --project=chromium
```

## Test Files

- `e2e/blog.spec.js` - Blog application tests
  - Page loading
  - Post navigation
  - HTMX partial updates
  - Comment forms
  - Pagination
  - Search
  - Authentication
  - Admin panel

## Writing New Tests

```javascript
test('should do something', async ({ page }) => {
  await page.goto('/path')
  await page.click('button')
  await expect(page).toHaveURL('/new-path')
})
```

## CI Integration

Tests are automatically run in CI via GitHub Actions:
- `tests/e2e/blog.spec.js` - E2E tests for blog application
- Tests run against Chromium, Firefox, and WebKit
- HTML report generated on failure

## Debug

To debug tests:
1. Run `npm run test:debug`
2. Click "Resume" in the debug panel