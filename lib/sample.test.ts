import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

describe("loadSample", () => {
  it("returns the examples/*.csv files verbatim, not a copy", async () => {
    const { loadSample } = await import("./sample");
    const sample = loadSample();
    for (const name of ["units", "changes", "material", "incorporations"] as const) {
      expect(sample[name]).toBe(readFileSync(`examples/${name}.csv`, "utf8"));
      expect(sample[name].length).toBeGreaterThan(40);
    }
  });
});
