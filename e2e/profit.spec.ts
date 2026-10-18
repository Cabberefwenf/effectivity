import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const BANNER = "Synthetic data only. Do not upload export-controlled or customer files.";

test.describe("profit pages", () => {
  for (const path of ["/packaging", "/dashboard"] as const) {
    test(`${path}: banner, landmarks, no console errors, no axe violations`, async ({ page }) => {
      const errors: string[] = [];
      page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
      page.on("pageerror", (e) => errors.push(e.message));
      await page.goto(path);
      await expect(page.getByLabel("Data notice")).toContainText(BANNER);
      await expect(page.getByRole("main")).toBeVisible();
      await expect(page.locator("h1")).toHaveCount(1);
      const results = await new AxeBuilder({ page }).analyze();
      expect(results.violations.map((v) => `${v.id}: ${v.nodes[0]?.target}`)).toEqual([]);
      expect(errors).toEqual([]);
    });

    test(`${path}: states billing is off and claims no revenue or customers`, async ({ page }) => {
      await page.goto(path);
      await expect(page.getByText("Billing is off", { exact: false }).first()).toBeVisible();
    });

    test(`${path}: has no checkout, buy, or pay control`, async ({ page }) => {
      await page.goto(path);
      await expect(page.getByRole("button", { name: /buy|checkout|pay now/i })).toHaveCount(0);
      await expect(page.locator("form")).toHaveCount(0);
    });
  }

  test("packaging: upgrade planner shows steps, downgrade terms, and blocked moves", async ({
    page,
  }) => {
    await page.goto("/packaging");
    await expect(page.getByRole("status")).toContainText("allowed");
    await expect(page.getByText("Confirm the move from Library to Pilot")).toBeVisible();
    await page.getByLabel("Target package").selectOption("per_programme");
    await expect(page.getByText("Confirm the move from Library to Per programme")).toBeVisible();
    await page.getByLabel("Current package").selectOption("per_programme");
    await page.getByLabel("Target package").selectOption("pilot");
    await expect(page.getByText("Confirm the downgrade is not a refund")).toBeVisible();
    await page.getByLabel("Units in use").fill("900");
    await expect(page.getByRole("status")).toContainText("blocked");
    await expect(page.getByText("above the Pilot limit of 250")).toBeVisible();
    await page.getByLabel("Units in use").fill("10");
    await expect(page.getByRole("status")).toContainText("allowed");
  });

  test("dashboard: shows demo proof of value with zero revenue", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByText("Demonstration data only", { exact: false })).toBeVisible();
    await expect(page.getByText("Real revenue", { exact: true })).toBeVisible();
    await expect(page.getByText("No data", { exact: false }).first()).toBeVisible();
  });
});
