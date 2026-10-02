import { ApiErrorSchema, ReportSchema, type Report } from "./schema";

export const TABLES = ["units", "changes", "material", "incorporations"] as const;
export type TableName = (typeof TABLES)[number];
export type Tables = Record<TableName, string>;

export type Problem = { table: string; message: string };

export type Outcome =
  | { kind: "ok"; report: Report }
  /** The tables were read but are wrong. The user can fix these. */
  | { kind: "invalid"; message: string; problems: Problem[] }
  /** A size cap was hit. */
  | { kind: "limit"; message: string; problems: Problem[] }
  /** The function could not be reached or answered with something unexpected. */
  | { kind: "unavailable"; message: string };

export const RESOLVE_PATH = "/api/resolve";
const TIMEOUT_MS = 20000;

/** POST the four CSV texts. Nothing is cached or stored; the reply is validated before use. */
export async function resolveTables(
  tables: Tables,
  options: { signal?: AbortSignal; fetchImpl?: typeof fetch } = {},
): Promise<Outcome> {
  const fetchImpl = options.fetchImpl ?? fetch;
  const timeout = AbortSignal.timeout(TIMEOUT_MS);
  const signal = options.signal ? AbortSignal.any([options.signal, timeout]) : timeout;
  let response: Response;
  try {
    response = await fetchImpl(RESOLVE_PATH, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(tables),
      cache: "no-store",
      signal,
    });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    const timedOut = timeout.aborted;
    return {
      kind: "unavailable",
      message: timedOut
        ? "The resolver did not answer in time. Try again."
        : "Could not reach the resolver. Check your connection and try again.",
    };
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return {
      kind: "unavailable",
      message: `The resolver answered with an unreadable response (HTTP ${response.status}).`,
    };
  }

  if (response.ok) {
    const parsed = ReportSchema.safeParse(body);
    if (parsed.success) return { kind: "ok", report: parsed.data };
    return {
      kind: "unavailable",
      message: "The resolver's reply did not match the expected shape.",
    };
  }

  const parsedError = ApiErrorSchema.safeParse(body);
  if (!parsedError.success) {
    return { kind: "unavailable", message: `The resolver failed (HTTP ${response.status}).` };
  }
  const { code, message, problems } = parsedError.data.error;
  if (response.status === 422) return { kind: "invalid", message, problems };
  if (response.status === 413) return { kind: "limit", message, problems };
  return { kind: "unavailable", message: `${message} (${code})` };
}
