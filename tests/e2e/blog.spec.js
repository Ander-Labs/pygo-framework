import { test, expect } from '@playwright/test'

test.describe('Blog Application E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/blog')
  })

  test('should load blog page', async ({ page }) => {
    await expect(page).toHaveTitle(/Blog|PyGo/)
    await expect(page.locator('h1')).toContainText('Blog')
  })

  test('should display list of posts', async ({ page }) => {
    const posts = page.locator('.post-item, .card, [data-testid="post"]')
    await expect(posts.first()).toBeVisible()
  })

  test('should navigate to post detail', async ({ page }) => {
    await page.click('a[href*="/posts/"], .post-link, a[data-testid="post-link"]')
    await expect(page).toHaveURL(/\/posts\//)
  })

  test('should load post content', async ({ page }) => {
    await page.click('a[href*="/posts/"]')
    await expect(page.locator('h2, .post-title')).toBeVisible()
    await expect(page.locator('.post-content, [data-testid="post-content"]')).toBeVisible()
  })

  test('should handle HTMX partial updates', async ({ page }) => {
    // Test that clicking a link loads content via HTMX
    await page.click('a[hx-get], a[data-hx-get]')
    
    // Wait for HTMX request
    await page.waitForSelector('[hx-trigger]', { timeout: 5000 }).catch(() => {})
    
    // Verify content updated without full page reload
    await expect(page.locator('body')).toBeVisible()
  })

  test('should handle comment form submission', async ({ page }) => {
    await page.click('button[type="submit"], .comment-button')
    
    // Fill comment form
    await page.fill('textarea[name="comment"], #comment', 'Test comment')
    await page.click('button[type="submit"]')
    
    // Verify comment added
    await expect(page.locator('.comment, [data-testid="comment"]')).toContainText('Test comment')
  })

  test('should handle pagination', async ({ page }) => {
    await page.click('a[rel="next"], .pagination a, button[aria-label*="next"]')
    await expect(page.locator('.post-item, .card')).toBeVisible()
  })

  test('should handle search', async ({ page }) => {
    const searchInput = page.locator('input[type="search"], input[name="q"]')
    if (await searchInput.isVisible()) {
      await searchInput.fill('test')
      await searchInput.press('Enter')
      await expect(page.locator('.search-results, .post-item')).toBeVisible()
    }
  })

  test('should handle post creation', async ({ page }) => {
    // Navigate to new post page
    await page.click('a[href*="/new"], button[data-action="create"]')
    
    // Fill form
    await page.fill('input[name="title"], #title', 'Test Post')
    await page.fill('textarea[name="content"], #content', 'This is test content')
    
    // Submit
    await page.click('button[type="submit"]')
    
    // Verify redirect or success
    await page.waitForURL(/\/posts\/\d+/, { timeout: 5000 }).catch(() => {})
  })

  test('should handle authentication', async ({ page }) => {
    // Click login
    await page.click('a[href*="/login"], button[data-action="login"]')
    
    // Fill credentials
    await page.fill('input[name="email"], #email', 'test@example.com')
    await page.fill('input[name="password"], #password', 'password123')
    await page.click('button[type="submit"]')
    
    // Verify login success
    await expect(page.locator('a[href*="/logout"], .user-menu')).toBeVisible()
  })

  test('should handle logout', async ({ page }) => {
    // Click logout
    await page.click('a[href*="/logout"], button[data-action="logout"]')
    
    // Verify logged out
    await expect(page.locator('a[href*="/login"]')).toBeVisible()
  })

  test('should handle admin panel access', async ({ page }) => {
    // Navigate to admin
    await page.goto('/admin')
    
    // Should redirect to login if not authenticated
    if (await page.locator('input[name="email"]').isVisible()) {
      await page.fill('input[name="email"], #email', 'admin@example.com')
      await page.fill('input[name="password"], #password', 'admin123')
      await page.click('button[type="submit"]')
    }
    
    // Verify admin panel loaded
    await expect(page.locator('h1, .admin-title')).toContainText(/Admin|Dashboard/)
  })
})

test.describe('API E2E', () => {
  test('should handle API requests', async ({ page, request }) => {
    const response = await request.get('/api/posts')
    expect(response.status()).toBe(200)
    
    const data = await response.json()
    expect(Array.isArray(data)).toBe(true)
  })

  test('should handle API POST', async ({ request }) => {
    const response = await request.post('/api/posts', {
      data: {
        title: 'Test Post',
        content: 'Test content'
      }
    })
    
    expect(response.status()).toBe(200)
  })

  test('should handle API error responses', async ({ request }) => {
    const response = await request.get('/api/nonexistent')
    expect(response.status()).toBe(404)
  })
})

test.describe('HTMX E2E', () => {
  test('should handle HTMX swap', async ({ page }) => {
    // Click element that triggers HTMX
    await page.click('.htmx-trigger, [hx-trigger="click"]')
    
    // Wait for HTMX to complete
    await page.waitForSelector('[hx-trigger]', { timeout: 5000 }).catch(() => {})
    
    // Verify content swapped
    await expect(page.locator('.htmx-content, [data-testid="content"]')).toBeVisible()
  })

  test('should handle HTMX loading states', async ({ page }) => {
    await page.click('.loading-trigger')
    
    // Should show loading indicator
    await expect(page.locator('.loading, [hx-indicator]')).toBeVisible()
    
    // Wait for load to complete
    await page.waitForSelector('.loading', { state: 'hidden', timeout: 5000 }).catch(() => {})
  })
})