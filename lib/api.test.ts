import { describe, expect, it, vi } from "vitest";
import { resolveTables, type Tables } from "./api";
import golden from "../tests/golden/examples-report.json";

const TABLES: Tables = { units: "a", changes: "b", material: "c", incorporations: "d" };

function reply(status: number, body: unknown): typeof fetch {
  return vi.fn(
    async () => new Response(JSON.stringify(body), { status }),
  ) as unknown as typeof fetch;
}

describe("resolveTables", () => {
  it("posts the four tables as JSON to /api/resolve without caching", async () => {
    const fetchImpl = reply(200, golden);
    await resolveTables(TABLES, { fetchImpl });
    const [url, init] = (fetchImpl as unknown as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(url).toBe("/api/resolve");
    expect(init.method).toBe("POST");
    expect(init.cache).toBe("no-store");
    expect(JSON.parse(init.body as string)).toEqual(TABLES);
  });

  it("accepts the golden report from the Python CLI unchanged", async () => {
    const outcome = await resolveTables(TABLES, { fetchImpl: reply(200, golden) });
    expect(outcome.kind).toBe("ok");
    if (outcome.kind === "ok") {
      expect(outcome.report.decisions).toHaveLength(50);
      expect(outcome.report.counts.out_of_effectivity).toBe(29);
    }
  });

  it("maps 422 to invalid with the parser's problems", async () => {
    const error = {
      error: {
        code: "invalid_input",
        message: "Fix these.",
        problems: [{ table: "units", message: "units.csv: line 3: bad" }],
      },
    };
    const outcome = await resolveTables(TABLES, { fetchImpl: reply(422, error) });
    expect(outcome).toEqual({
      kind: "invalid",
      message: "Fix these.",
      problems: [{ table: "units", message: "units.csv: line 3: bad" }],
    });
  });

  it("maps 413 to limit", async () => {
    const error = { error: { code: "too_large", message: "Too big.", problems: [] } };
    expect((await resolveTables(TABLES, { fetchImpl: reply(413, error) })).kind).toBe("limit");
  });

  it("treats other failures as unavailable and keeps the code", async () => {
    const error = { error: { code: "internal_error", message: "Failed.", problems: [] } };
    const outcome = await resolveTables(TABLES, { fetchImpl: reply(500, error) });
    expect(outcome.kind).toBe("unavailable");
    if (outcome.kind === "unavailable") expect(outcome.message).toContain("internal_error");
  });

  it("never renders a 200 with the wrong shape as results", async () => {
    const outcome = await resolveTables(TABLES, { fetchImpl: reply(200, { decisions: "nope" }) });
    expect(outcome.kind).toBe("unavailable");
  });

  it("rejects a decision with an unknown state", async () => {
    const bad = structuredClone(golden) as typeof golden;
    (bad.decisions[0] as { status: string }).status = "maybe";
    expect((await resolveTables(TABLES, { fetchImpl: reply(200, bad) })).kind).toBe("unavailable");
  });

  it("handles a non-JSON body (a proxy error page)", async () => {
    const fetchImpl = vi.fn(
      async () => new Response("<html>502</html>", { status: 502 }),
    ) as unknown as typeof fetch;
    const outcome = await resolveTables(TABLES, { fetchImpl });
    expect(outcome.kind).toBe("unavailable");
    if (outcome.kind === "unavailable") expect(outcome.message).toContain("502");
  });

  it("reports a network failure as unavailable", async () => {
    const fetchImpl = vi.fn(async () => {
      throw new TypeError("network");
    }) as unknown as typeof fetch;
    expect((await resolveTables(TABLES, { fetchImpl })).kind).toBe("unavailable");
  });

  it("rethrows when the caller aborted, so a superseded run is not shown", async () => {
    const controller = new AbortController();
    controller.abort();
    const fetchImpl = vi.fn(async () => {
      throw new DOMException("aborted", "AbortError");
    }) as unknown as typeof fetch;
    await expect(
      resolveTables(TABLES, { fetchImpl, signal: controller.signal }),
    ).rejects.toBeDefined();
  });
});
