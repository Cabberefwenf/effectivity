/** The six output states, in canonical order. Exactly these; the resolver has no others. */
export const STATE_ORDER = [
  "out_of_effectivity",
  "not_yet_reached",
  "incorporable",
  "late",
  "blocked_material",
  "incorporated",
] as const;

export type State = (typeof STATE_ORDER)[number];

/** Colour roles are the design system's six. Status is never colour alone: a glyph and a word too. */
export type Role = "governing" | "unresolved" | "conflict" | "superseded";

export const STATES: Record<State, { role: Role; meaning: string }> = {
  out_of_effectivity: {
    role: "superseded",
    meaning: "The unit is not in the change's effectivity range.",
  },
  not_yet_reached: {
    role: "superseded",
    meaning:
      "The unit has not reached the incorporation hold point, or has not cleared the hold before it.",
  },
  incorporable: {
    role: "governing",
    meaning: "At the incorporation hold point, predecessor closed, nothing blocking.",
  },
  late: {
    role: "unresolved",
    meaning: "The unit has passed the incorporation hold point and the change is not incorporated.",
  },
  blocked_material: {
    role: "conflict",
    meaning: "Superseded material is already staged at the work or installed.",
  },
  incorporated: {
    role: "governing",
    meaning: "An incorporation record exists and the predecessor hold is closed.",
  },
};

export function isState(value: string): value is State {
  return (STATE_ORDER as readonly string[]).includes(value);
}
