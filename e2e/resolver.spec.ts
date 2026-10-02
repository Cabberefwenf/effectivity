import { expect, test } from "@playwright/test";

const GOLDEN_COUNTS = {
  out_of_effectivity: 29,
  not_yet_reached: 10,
  incorporable: 4,
  late: 2,
  blocked_material: 3,
  incorporated: 2,
} as const;

test.describe("resolver", () => {
  test("starts with an empty state and a disabled Resolve button", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByText("No results yet.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Resolve", exact: true })).toBeDisabled();
  });

  test("loads the sample, resolves it and shows the six counts that the CLI prints", async ({
    page,
  }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Load synthetic sample and run" }).click();
    const group = page.getByRole("list", { name: "Count per state" });
    await expect(group).toBeVisible();
    for (const [state, n] of Object.entries(GOLDEN_COUNTS)) {
      await expect(
        group.getByRole("button", { name: new RegExp(`^${state}\\s*${n}\\b`) }),
      ).toBeVisible();
    }
    await expect(page.getByTestId("input-hash")).toHaveText(/^92fff1e82a01[0-9a-f]{52}$/);
    await expect(page.getByText("1.0.0", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Showing 50 of 50 decisions.")).toBeVisible();
  });

  test("filters by state and by search, and clears", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Load synthetic sample and run" }).click();
    const late = page.getByRole("button", { name: /^late\s*2/ });
    await late.click();
    await expect(late).toHaveAttribute("aria-pressed", "true");
    await expect(
      page.getByText("Showing 2 of 2 filtered decisions (50 in this run)."),
    ).toBeVisible();
    await page.getByLabel("Search unit, change, reason code or rule").fill("zzz-no-match");
    await expect(page.getByText("No decisions match these filters.")).toBeVisible();
    await page.getByRole("button", { name: "Clear filters" }).click();
    await expect(page.getByText("Showing 50 of 50 decisions.")).toBeVisible();
  });

  test("opens the rule text from a rule id", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Load synthetic sample and run" }).click();
    await page.getByRole("button", { name: "Show rule R02" }).first().click();
    const panel = page.getByTestId("rule-panel");
    await expect(panel).toContainText("R02");
    await expect(panel).toContainText("predecessor_hold_status is closed");
    await expect(panel.getByRole("link", { name: "Full decision table" })).toHaveAttribute(
      "href",
      "/rules#R02",
    );
  });

  test("shows the parser's error with its detail and keeps the input", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Load synthetic sample and run" }).click();
    await expect(page.getByTestId("input-hash")).toBeVisible();
    const units = page.getByLabel("Units", { exact: true });
    await units.fill("unit_id,program\nU-1,P\n");
    await page.getByRole("button", { name: "Resolve", exact: true }).click();
    const alert = page.locator('main [role="alert"]').filter({ hasText: "could not be read" });
    await expect(alert).toBeVisible();
    await expect(alert).toContainText(/columns must be exactly/);
    await expect(units).toHaveAttribute("aria-invalid", "true");
    await expect(units).toHaveValue("unit_id,program\nU-1,P\n");
  });

  test("download button produces JSON named after the input hash", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Load synthetic sample and run" }).click();
    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "Download JSON" }).click();
    expect((await download).suggestedFilename()).toMatch(/^effectivity-92fff1e82a01\.json$/);
  });

  test("an unreachable function is reported, not rendered as an empty result", async ({ page }) => {
    await page.route("**/api/resolve", (route) => route.abort());
    await page.goto("/");
    await page.getByRole("button", { name: "Load synthetic sample and run" }).click();
    await expect(page.locator('main [role="alert"]')).toContainText("The resolver could not run");
    await expect(page.getByText("Showing")).toHaveCount(0);
  });

  test("a clear button empties the form and results", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Load synthetic sample and run" }).click();
    await expect(page.getByTestId("input-hash")).toBeVisible();
    await page.getByRole("button", { name: "Clear", exact: true }).click();
    await expect(page.getByText("No results yet.")).toBeVisible();
    await expect(page.getByLabel("Units", { exact: true })).toHaveValue("");
  });

  test("works by keyboard alone", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
    const sample = page.getByRole("button", { name: "Load synthetic sample and run" });
    await sample.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByTestId("input-hash")).toBeVisible();
    const late = page.getByRole("button", { name: /^late\s*2/ });
    await late.focus();
    await page.keyboard.press("Space");
    await expect(late).toHaveAttribute("aria-pressed", "true");
  });
});
