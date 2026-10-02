import { STATES, type Role, type State } from "@/lib/states";
import { StateGlyph } from "./StateGlyph";

const ROLE_CLASS: Record<Role, string> = {
  governing: "border-governing/50 bg-governing-soft text-governing",
  unresolved: "border-unresolved/50 bg-unresolved-soft text-unresolved",
  conflict: "border-conflict/50 bg-conflict-soft text-conflict",
  superseded: "border-rule-strong bg-inset text-ink-3",
};

/** Glyph plus the state's own identifier. The identifier is a value the resolver outputs, so it is mono. */
export function StateChip({ state }: { state: State }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 border px-2 py-0.5 font-mono text-meta ${ROLE_CLASS[STATES[state].role]}`}
    >
      <StateGlyph state={state} size={14} />
      {state}
    </span>
  );
}

export const ROLE_TEXT: Record<Role, string> = {
  governing: "text-governing",
  unresolved: "text-unresolved",
  conflict: "text-conflict",
  superseded: "text-ink-3",
};
