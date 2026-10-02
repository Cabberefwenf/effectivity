import { describe, expect, it } from "vitest";
import { SITE, isIndexable, siteOrigin } from "./site";

describe("siteOrigin", () => {
  it("prefers the explicit URL and strips trailing slashes", () => {
    expect(siteOrigin({ NEXT_PUBLIC_SITE_URL: "https://x.example/" })).toBe("https://x.example");
  });
  it("falls back to the Vercel production URL, then localhost", () => {
    expect(siteOrigin({ VERCEL_PROJECT_PRODUCTION_URL: "eff.vercel.app" })).toBe(
      "https://eff.vercel.app",
    );
    expect(siteOrigin({})).toBe("http://localhost:3000");
  });
});

describe("isIndexable", () => {
  it("is true only for the production deployment", () => {
    expect(isIndexable({ VERCEL_ENV: "production" })).toBe(true);
    expect(isIndexable({ VERCEL_ENV: "preview" })).toBe(false);
    expect(isIndexable({ VERCEL_ENV: "development" })).toBe(false);
    expect(isIndexable({})).toBe(false);
  });
});

describe("SITE", () => {
  it("carries the exact banner sentence", () => {
    expect(SITE.notice).toBe(
      "Synthetic data only. Do not upload export-controlled or customer files.",
    );
  });
});
