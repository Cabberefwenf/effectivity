import type { Metadata } from "next";
import { StateChip } from "@/components/StateChip";
import { RULES, RULE_VERSION } from "@/lib/rules";
import { SITE } from "@/lib/site";

export const metadata: Metadata = {
  title: "Rules",
  description:
    "The ordered rules of the effectivity state machine, with the reason codes each can emit.",
  alternates: { canonical: "/rules" },
};

export default function RulesPage() {
  return (
    <div className="max-w-5xl">
      <p className="kicker">Decision table</p>
      <h1 className="mt-2 font-serif text-statement font-semibold">The rules, in order</h1>
      <p className="mt-5 max-w-prose text-lede text-ink-2">
        Rules are evaluated top to bottom and the first match decides. This page is generated from{" "}
        <a href={SITE.stateMachineUrl} className="link" rel="noopener noreferrer">
          docs/state-machine.md
        </a>
        , so it cannot drift from the repo. Rule version{" "}
        <span className="mono-id">{RULE_VERSION}</span>.
      </p>
      <ol className="mt-10 space-y-3">
        {RULES.map((rule) => (
          <li
            key={rule.id}
            id={rule.id}
            className="panel scroll-mt-28 p-4 target:border-engineering"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <h2 className="font-mono text-subsection font-medium">{rule.id}</h2>
              {rule.status ? (
                <StateChip state={rule.status} />
              ) : (
                <span className="text-meta text-ink-3">data error annotation</span>
              )}
            </div>
            <p className="mt-2 text-small text-ink">{rule.condition.replace(/\.$/, "")}.</p>
            <p className="mt-3 text-meta text-ink-3">Reason codes</p>
            <ul className="mt-1 space-y-1">
              {rule.reasonCodes.map((code) => (
                <li key={code} className="mono-id break-all">
                  {code}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </div>
  );
}
