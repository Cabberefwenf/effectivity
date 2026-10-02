import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const PAGES = ["/", "/rules", "/about"] as const;
const BANNER = "Synthetic data only. Do not upload export-controlled or customer files.";

test.describe("every page", () => {
  for (const path of PAGES) {
    test(`${path}: banner, landmarks, no console errors, no axe violations`, async ({ page }) => {
      const errors: string[] = [];
      page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
      page.on("pageerror", (e) => errors.push(e.message));
      await page.goto(path);
      await expect(page.getByLabel("Data notice")).toContainText(BANNER);
      await expect(
        page.getByLabel("Data notice").getByRole("link", { name: "Limits", exact: true }),
      ).toHaveAttribute("href", /LIMITS\.md$/);
      await expect(page.getByRole("main")).toBeVisible();
      await expect(page.getByRole("navigation", { name: "Primary" })).toBeVisible();
      await expect(page.locator("h1")).toHaveCount(1);
      const results = await new AxeBuilder({ page }).analyze();
      expect(results.violations.map((v) => `${v.id}: ${v.nodes[0]?.target}`)).toEqual([]);
      expect(errors).toEqual([]);
    });
  }

  test("axe is clean after resolving, with the rule panel open and an error showing", async ({
    page,
  }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Load synthetic sample and run" }).click();
    await page.getByRole("button", { name: "Show rule R09" }).first().click();
    await expect(page.getByTestId("rule-panel")).toBeVisible();
    let results = await new AxeBuilder({ page }).analyze();
    expect(results.violations.map((v) => `${v.id}: ${v.nodes[0]?.target}`)).toEqual([]);
    await page.getByLabel("Units", { exact: true }).fill("bad\n1\n");
    await page.getByRole("button", { name: "Resolve", exact: true }).click();
    await expect(page.locator('main [role="alert"]')).toBeVisible();
    results = await new AxeBuilder({ page }).analyze();
    expect(results.violations.map((v) => `${v.id}: ${v.nodes[0]?.target}`)).toEqual([]);
  });

  test("the banner stays visible while scrolling", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Load synthetic sample and run" }).click();
    await page.mouse.wheel(0, 3000);
    await expect(page.getByLabel("Data notice")).toBeInViewport();
  });
});

test.describe("responsive", () => {
  for (const width of [360, 390, 768, 1024, 1440]) {
    test(`no horizontal overflow at ${width}px, with results`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      for (const path of PAGES) {
        await page.goto(path);
        if (path === "/") {
          await page.getByRole("button", { name: "Load synthetic sample and run" }).click();
          await expect(page.getByTestId("input-hash")).toBeVisible();
        }
        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );
        expect(overflow, `${path} at ${width}`).toBeLessThanOrEqual(0);
      }
    });
  }
});

test.describe("deployment surface", () => {
  test("serves the security headers on pages", async ({ request }) => {
    const response = await request.get("/");
    const h = response.headers();
    expect(h["content-security-policy"]).toContain("frame-ancestors 'none'");
    expect(h["x-content-type-options"]).toBe("nosniff");
    expect(h["referrer-policy"]).toBe("strict-origin-when-cross-origin");
    expect(h["x-frame-options"]).toBe("DENY");
    expect(h["x-powered-by"]).toBeUndefined();
  });

  test("metadata: title, description, canonical, Open Graph, icon, noindex off-production", async ({
    page,
    request,
  }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/effectivity/);
    await expect(page.locator('meta[name="description"]')).toHaveAttribute(
      "content",
      /deterministic/,
    );
    await expect(page.locator('meta[property="og:title"]')).toHaveAttribute(
      "content",
      /effectivity/,
    );
    await expect(page.locator('meta[property="og:image"]')).toHaveAttribute(
      "content",
      /opengraph-image/,
    );
    await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute(
      "content",
      "summary_large_image",
    );
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
    await expect(page.locator('link[rel="icon"]').first()).toHaveAttribute("href", /icon/);
    for (const path of ["/icon", "/opengraph-image"]) {
      const res = await request.get(path);
      expect(res.status(), path).toBe(200);
      expect(res.headers()["content-type"]).toContain("image/png");
    }
    expect((await request.get("/robots.txt")).status()).toBe(200);
    expect((await request.get("/sitemap.xml")).status()).toBe(200);
  });

  test("unknown pages get the designed 404 with the banner", async ({ page }) => {
    const response = await page.goto("/does-not-exist");
    expect(response?.status()).toBe(404);
    await expect(page.getByRole("heading", { name: "That page does not exist" })).toBeVisible();
    await expect(page.getByLabel("Data notice")).toBeVisible();
  });
});

test.describe("api through the site", () => {
  test("GET is refused and says so", async ({ request }) => {
    const res = await request.get("/api/resolve");
    expect(res.status()).toBe(405);
    expect((await res.json()).error.code).toBeTruthy();
  });

  test("oversized bodies are refused before parsing", async ({ request }) => {
    const res = await request.post("/api/resolve", {
      headers: { "content-type": "application/json" },
      data: JSON.stringify({
        units: "x".repeat(300_000),
        changes: "",
        material: "",
        incorporations: "",
      }),
    });
    expect(res.status()).toBe(413);
  });
});
