import type { Decision } from "./schema";
import { STATE_ORDER, type State } from "./states";

/** No selected states means all states. The query matches any text field, case-insensitively. */
export function filterDecisions(
  decisions: readonly Decision[],
  selected: ReadonlySet<State>,
  query: string,
): Decision[] {
  const needle = query.trim().toLowerCase();
  return decisions.filter((d) => {
    if (selected.size > 0 && !selected.has(d.status)) return false;
    if (needle === "") return true;
    const haystack = [d.unit_id, d.change_id, d.status, d.reason_code, ...d.rule_ids]
      .join(" ")
      .toLowerCase();
    return haystack.includes(needle);
  });
}

export function toggleState(selected: ReadonlySet<State>, state: State): Set<State> {
  const next = new Set(selected);
  if (next.has(state)) next.delete(state);
  else next.add(state);
  return next;
}

/** Counts per state for a list of decisions, always with all six keys, in canonical order. */
export function countByState(decisions: readonly Decision[]): Record<State, number> {
  const counts = Object.fromEntries(STATE_ORDER.map((s) => [s, 0])) as Record<State, number>;
  for (const d of decisions) counts[d.status] += 1;
  return counts;
}
