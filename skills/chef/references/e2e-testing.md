# End-to-end testing: Playwright, Cypress

Builds on `typescript.md`. Verified against @playwright/test 1.65, eslint-plugin-playwright 2.12, @axe-core/playwright 4.14, Cypress 16.3, eslint-plugin-cypress 7.0 (Nov 2026). Look up the current version with `npm view <package> version`. Playwright 1.65 supports Node 22, 24 and 26; Cypress 16 needs Node 22, 24 or 26+.

## Choice

- New project: Playwright. Keep Cypress where the project already uses it; do not mix both.
- End-to-end tests cover critical user flows across pages, not every branch: logic belongs in unit tests.

## Playwright

- Config with named constants, traces on first retry, `test.only` forbidden in CI:
  ```ts
  import { defineConfig, devices, type PlaywrightTestConfig } from "@playwright/test";

  const isCi: boolean = Boolean(process.env.CI);
  const CI_RETRIES: number = 2;
  const BASE_URL: string = "http://localhost:4173";

  const config: PlaywrightTestConfig = defineConfig({
    testDir: "e2e",
    fullyParallel: true,
    forbidOnly: isCi,
    retries: isCi ? CI_RETRIES : 0,
    use: { baseURL: BASE_URL, trace: "on-first-retry" },
    projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
    webServer: { command: "npm run preview", url: BASE_URL, reuseExistingServer: !isCi },
  });
  export default config;
  ```
- Run against a production build (`build` then `preview`/`start`), not the dev server.
- Locators by role, label or text (`getByRole("button", { name: "Save" })`); no CSS, XPath or test ids.
- Web-first assertions only (`await expect(locator).toBeVisible()`); they retry. Never `waitForTimeout`, `waitForSelector` or `networkidle`.
- Test names state the behavior:
  ```ts
  import { expect, test, type Page } from "@playwright/test";

  test("checkout with an empty cart shows the empty-cart message", async ({ page }: { page: Page }): Promise<void> => {
    await page.goto("/checkout");
    await expect(page.getByRole("heading", { name: "Your cart is empty" })).toBeVisible();
  });
  ```
- Log in once in a `setup` project that saves `storageState`; other projects declare `dependencies: ["setup"]`. Keep `playwright/.auth` out of git.
- Each test creates its own data (API calls or fixtures) and does not depend on another test's state.
- Mock third-party services with `page.route`; never hit real payment or email providers.
- Accessibility: run `new AxeBuilder({ page }).analyze()` on key pages and expect zero violations.
- Lint the `e2e/` folder with `playwright.configs["flat/recommended"]` from `eslint-plugin-playwright` (scoped with `files`).
- CI: upload the HTML report and traces as artifacts; debug failures with `npx playwright show-trace`, not videos.

## Cypress

- Find elements with the built-in `cy.getByRole("button", { name: "Save" })` (Cypress 16) or `@testing-library/cypress`. Do not enable `cypress/require-data-selectors`: it contradicts the role-first query rule.
- No `cy.wait(<number>)`; wait on route aliases (`cy.intercept(...).as("save")`, `cy.wait("@save")`) or assertions.
- Commands are chained, not awaited: no `async` tests, no assigning `cy` return values.
- Log in with `cy.session()` through the API, not the UI, except in the login test itself.
- Do not visit third-party sites; stub them with `cy.intercept`. Use Chrome in CI: the Electron browser is deprecated in Cypress 16.
- Lint with `pluginCypress.configs.recommended` (flat config; the old `eslint-plugin-cypress/flat` path is removed).

## Flakiness

- A flaky test is a bug: find the race (missing await, shared data, animation) and fix it. Retries only collect traces; never raise them to make CI green.
- No `test.skip` / `it.skip` left in the code without an issue link and the user's approval.
