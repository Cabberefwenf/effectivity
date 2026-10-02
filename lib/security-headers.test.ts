import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

type Header = { key: string; value: string };
const config = JSON.parse(readFileSync(new URL("../vercel.json", import.meta.url), "utf8")) as {
  framework: string;
  installCommand: string;
  buildCommand: string;
  functions: Record<string, { maxDuration: number; includeFiles: string }>;
  headers: { source: string; headers: Header[] }[];
};

const all = new Map(
  config.headers.find((h) => h.source === "/(.*)")!.headers.map((h) => [h.key, h.value]),
);
const csp = new Map(
  (all.get("Content-Security-Policy") ?? "").split(";").map((part) => {
    const [name, ...rest] = part.trim().split(/\s+/);
    return [name as string, rest.join(" ")] as const;
  }),
);

describe("security headers (vercel.json is the single source)", () => {
  it("forbids framing, plugins and foreign origins", () => {
    expect(csp.get("frame-ancestors")).toBe("'none'");
    expect(csp.get("default-src")).toBe("'self'");
    expect(csp.get("object-src")).toBe("'none'");
    expect(csp.get("connect-src")).toBe("'self'");
    expect(csp.get("base-uri")).toBe("'self'");
    expect(csp.get("form-action")).toBe("'self'");
    expect(csp.get("script-src-attr")).toBe("'none'");
    expect(csp.has("upgrade-insecure-requests")).toBe(true);
  });
  it("never allows eval or a wildcard or a remote origin in script-src", () => {
    const script = csp.get("script-src") ?? "";
    expect(script).not.toContain("unsafe-eval");
    expect(script).not.toMatch(/\*|https?:/);
  });
  it("sets the standard hardening headers", () => {
    expect(all.get("X-Content-Type-Options")).toBe("nosniff");
    expect(all.get("X-Frame-Options")).toBe("DENY");
    expect(all.get("Referrer-Policy")).toBe("strict-origin-when-cross-origin");
    expect(all.get("Cross-Origin-Opener-Policy")).toBe("same-origin");
    expect(all.get("Cross-Origin-Resource-Policy")).toBe("same-site");
    expect(all.get("Strict-Transport-Security")).toMatch(/max-age=\d{7,}/);
    expect(all.get("Permissions-Policy")).toContain("camera=()");
    expect(all.get("Permissions-Policy")).toContain("geolocation=()");
  });
  it("has no CORS header anywhere: the function is same-origin only", () => {
    for (const entry of config.headers) {
      for (const header of entry.headers)
        expect(header.key.toLowerCase()).not.toMatch(/^access-control-/);
    }
  });
  it("marks the API uncacheable", () => {
    const api = config.headers.find((h) => h.source === "/api/(.*)");
    expect(api?.headers).toContainEqual({ key: "Cache-Control", value: "no-store" });
  });
  it("sets framework, install and build explicitly so no dashboard setting is needed", () => {
    expect(config.framework).toBe("nextjs");
    expect(config.installCommand).toBe("npm ci");
    expect(config.buildCommand).toBe("npm run build");
  });
  it("bundles src/ with the Python function and caps its duration", () => {
    const fn = config.functions["api/resolve.py"];
    expect(fn?.includeFiles).toBe("src/**");
    expect(fn?.maxDuration).toBeLessThanOrEqual(10);
  });
});
