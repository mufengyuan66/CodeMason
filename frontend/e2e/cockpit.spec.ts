import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:29864'

test.describe('CodeMason 驾驶舱', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL)
  })

  test('页面加载成功', async ({ page }) => {
    await expect(page).toHaveTitle(/CodeMason/)
  })

  test('落地页显示', async ({ page }) => {
    // 检查落地页是否显示
    const landingRoot = page.locator('.landing-root')
    await expect(landingRoot).toBeVisible()
  })

  test('进入驾驶舱', async ({ page }) => {
    // 点击进入按钮
    const enterBtn = page.locator('.enter-app-btn')
    if (await enterBtn.isVisible()) {
      await enterBtn.click()
      
      // 检查驾驶舱是否显示
      const cockpit = page.locator('.cockpit')
      await expect(cockpit).toBeVisible({ timeout: 5000 })
    }
  })

  test('三区架构显示', async ({ page }) => {
    // 先进入驾驶舱
    const enterBtn = page.locator('.enter-app-btn')
    if (await enterBtn.isVisible()) {
      await enterBtn.click()
      await page.waitForSelector('.cockpit', { timeout: 5000 })
    }

    // 检查三区架构
    const sessionRail = page.locator('.session-rail')
    const cpCenter = page.locator('.cp-center')
    const cpDrawer = page.locator('.cp-drawer')

    await expect(sessionRail).toBeVisible()
    await expect(cpCenter).toBeVisible()
    await expect(cpDrawer).toBeVisible()
  })

  test('Composer 输入栏显示', async ({ page }) => {
    // 先进入驾驶舱
    const enterBtn = page.locator('.enter-app-btn')
    if (await enterBtn.isVisible()) {
      await enterBtn.click()
      await page.waitForSelector('.cockpit', { timeout: 5000 })
    }

    // 检查 Composer 组件
    const permission = page.locator('.cp-permission')
    const modeSwitch = page.locator('.cp-mode-switch')
    const input = page.locator('.cp-input')
    const modelSelect = page.locator('.cp-model-select')
    const sendBtn = page.locator('.cp-send')

    await expect(permission).toBeVisible()
    await expect(modeSwitch).toBeVisible()
    await expect(input).toBeVisible()
    await expect(modelSelect).toBeVisible()
    await expect(sendBtn).toBeVisible()
  })

  test('权限控制切换', async ({ page }) => {
    // 先进入驾驶舱
    const enterBtn = page.locator('.enter-app-btn')
    if (await enterBtn.isVisible()) {
      await enterBtn.click()
      await page.waitForSelector('.cockpit', { timeout: 5000 })
    }

    // 点击权限控制切换
    const permission = page.locator('.cp-permission')
    await permission.click()

    // 检查权限标签变化
    const permissionText = page.locator('.cp-permission-text')
    const text = await permissionText.textContent()
    expect(['默认', '自动审查', '完全访问']).toContain(text)
  })

  test('模型选择切换', async ({ page }) => {
    // 先进入驾驶舱
    const enterBtn = page.locator('.enter-app-btn')
    if (await enterBtn.isVisible()) {
      await enterBtn.click()
      await page.waitForSelector('.cockpit', { timeout: 5000 })
    }

    // 点击模型选择
    const modelSelect = page.locator('.cp-model-select')
    await modelSelect.click()

    // 检查模型名称变化
    const modelName = page.locator('.cp-model-name')
    const text = await modelName.textContent()
    expect(text).toBeTruthy()
  })

  test('毛玻璃效果应用', async ({ page }) => {
    // 先进入驾驶舱
    const enterBtn = page.locator('.enter-app-btn')
    if (await enterBtn.isVisible()) {
      await enterBtn.click()
      await page.waitForSelector('.cockpit', { timeout: 5000 })
    }

    // 检查会话栏的 backdrop-filter
    const sessionRail = page.locator('.session-rail')
    const backdropFilter = await sessionRail.evaluate(el => 
      window.getComputedStyle(el).backdropFilter
    )
    expect(backdropFilter).toContain('blur')
  })

  test('主题切换', async ({ page }) => {
    // 先进入驾驶舱
    const enterBtn = page.locator('.enter-app-btn')
    if (await enterBtn.isVisible()) {
      await enterBtn.click()
      await page.waitForSelector('.cockpit', { timeout: 5000 })
    }

    // 点击主题按钮
    const themeBtn = page.locator('[data-testid="cp-theme"]')
    await themeBtn.click()

    // 检查主题面板是否显示
    const themePanel = page.locator('.theme-panel')
    await expect(themePanel).toBeVisible({ timeout: 3000 })
  })
})
