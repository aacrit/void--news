import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  testMatch: "uat-test.spec.ts",
  timeout: 180000,
  expect: { timeout: 10000 },
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3001/void--news",
    headless: true,
    viewport: { width: 1280, height: 800 },
    actionTimeout: 10000,
    screenshot: "off",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
