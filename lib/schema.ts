import { z } from "zod";
import { STATE_ORDER } from "./states";

/** The function's reply is validated, not trusted: a proxy error page must never render as results. */
const count = z.number().int().nonnegative();

export const DecisionSchema = z.object({
  unit_id: z.string(),
  change_id: z.string(),
  status: z.enum(STATE_ORDER),
  reason_code: z.string().regex(/^[A-Z][A-Z_]*$/),
  rule_ids: z.array(z.string().regex(/^R\d\d$/)).min(1),
});

export const ReportSchema = z.object({
  rule_version: z.string(),
  input_hash: z.string().regex(/^[0-9a-f]{64}$/),
  inputs: z.object({ units: count, changes: count, material: count, incorporations: count }),
  counts: z.object({
    out_of_effectivity: count,
    not_yet_reached: count,
    incorporable: count,
    late: count,
    blocked_material: count,
    incorporated: count,
  }),
  decisions: z.array(DecisionSchema),
});

export const ApiErrorSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    problems: z.array(z.object({ table: z.string(), message: z.string() })),
  }),
});

export type Decision = z.infer<typeof DecisionSchema>;
export type Report = z.infer<typeof ReportSchema>;
export type ApiError = z.infer<typeof ApiErrorSchema>;
