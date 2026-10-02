"use client";

import { STATE_ORDER, STATES, type State } from "@/lib/states";
import { ROLE_TEXT } from "./StateChip";
import { StateGlyph } from "./StateGlyph";

type Props = {
  counts: Record<State, number>;
  selected: ReadonlySet<State>;
  onToggle: (state: State) => void;
};

/** The six counts are also the filters: each is a toggle button with a pressed state. */
export function Counts({ counts, selected, onToggle }: Props) {
  return (
    <ul
      className="grid grid-cols-2 gap-2 md:grid-cols-3 lg:grid-cols-6"
      aria-label="Count per state"
    >
      {STATE_ORDER.map((state) => {
        const pressed = selected.has(state);
        return (
          <li key={state}>
            <button
              type="button"
              aria-pressed={pressed}
              onClick={() => onToggle(state)}
              className={`flex h-full w-full flex-col items-start gap-1 border p-3 text-left transition-colors ${
                pressed
                  ? "border-engineering bg-engineering-soft"
                  : "border-rule bg-surface hover:border-rule-strong"
              }`}
            >
              <span
                className={`flex items-center gap-1.5 font-mono text-meta ${ROLE_TEXT[STATES[state].role]}`}
              >
                <StateGlyph state={state} size={14} />
                {state}
              </span>
              <span className="font-mono text-section font-medium leading-none text-ink">
                {counts[state]}
              </span>
              <span className="text-meta text-ink-3">{STATES[state].meaning}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
