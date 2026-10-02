import Link from "next/link";
import { findRule } from "@/lib/rules";
import { SITE } from "@/lib/site";
import { StateChip } from "./StateChip";

/** The rule's own text, read from docs/state-machine.md at build time. */
export function RulePanel({ ruleId, onClose }: { ruleId: string; onClose?: () => void }) {
  const rule = findRule(ruleId);
  return (
    <aside aria-label={`Rule ${ruleId}`} className="panel p-4" data-testid="rule-panel">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-mono text-subsection font-medium">{ruleId}</h3>
        {onClose ? (
          <button
            type="button"
            className="btn btn-quiet min-h-0 px-0 py-0 text-meta"
            onClick={onClose}
          >
            Close
          </button>
        ) : null}
      </div>
      {rule ? (
        <>
          <p className="mt-2 text-small text-ink">{rule.condition.replace(/\.$/, "")}.</p>
          <dl className="mt-3 space-y-2 text-small">
            <div>
              <dt className="text-meta text-ink-3">Decides</dt>
              <dd className="mt-1">
                {rule.status ? (
                  <StateChip state={rule.status} />
                ) : (
                  <span className="text-ink-2">
                    No state of its own. It marks the decision as a data error.
                  </span>
                )}
              </dd>
            </div>
            <div>
              <dt className="text-meta text-ink-3">Reason codes it can emit</dt>
              <dd className="mt-1 space-y-1">
                {rule.reasonCodes.map((code) => (
                  <p key={code} className="mono-id break-all">
                    {code}
                  </p>
                ))}
              </dd>
            </div>
          </dl>
        </>
      ) : (
        <p className="mt-2 text-small text-ink-2">
          This rule id is not in this site&apos;s rule version. Open the full decision table to
          compare.
        </p>
      )}
      <p className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-small">
        <Link href={`/rules#${ruleId}`} className="link">
          Full decision table
        </Link>
        <a href={SITE.stateMachineUrl} className="link" rel="noopener noreferrer">
          state-machine.md
        </a>
      </p>
    </aside>
  );
}
