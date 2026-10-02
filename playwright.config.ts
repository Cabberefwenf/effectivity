import { defineConfig } from "@playwright/test";

const PORT = 3100;
const API_PORT = 8787;
const python = process.env.EFFECTIVITY_PYTHON ?? "python3";

/**
 * The suite runs against a production build (`npm run build` first) served by `next start`,
 * with the real Python function behind it. It needs `pip install -e .` for pydantic.
 * PLAYWRIGHT_CHANNEL=chrome uses an installed Chrome instead of a downloaded Chromium.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `${python} tools/dev_api.py ${API_PORT}`,
      port: API_PORT,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: `npx next start -p ${PORT} -H 127.0.0.1`,
      port: PORT,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
