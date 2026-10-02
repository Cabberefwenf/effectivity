import generated from "./rules.generated.json";
import { isState, type State } from "./states";

export type Rule = {
  id: string;
  condition: string;
  /** null for R03, which annotates a decision instead of deciding one. */
  status: State | null;
  reasonCodes: string[];
};

/** Read from docs/state-machine.md by scripts/gen-rules.mjs; a test fails if it is stale. */
export const RULE_VERSION: string = generated.ruleVersion;

export const RULES: readonly Rule[] = generated.rules.map((rule) => {
  if (rule.status !== null && !isState(rule.status)) {
    throw new Error(`Rule ${rule.id} names an unknown status ${rule.status}`);
  }
  return { ...rule, status: rule.status as State | null };
});

export function findRule(id: string): Rule | undefined {
  return RULES.find((rule) => rule.id === id);
}
