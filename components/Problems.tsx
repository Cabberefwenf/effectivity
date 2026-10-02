import type { Outcome } from "@/lib/api";

type Failure = Exclude<Outcome, { kind: "ok" }>;

const HEADINGS: Record<Failure["kind"], string> = {
  invalid: "Some tables could not be read",
  limit: "A size limit was reached",
  unavailable: "The resolver could not run",
};

/** Validation errors come straight from the parsers, with file-style line numbers. */
export function Problems({
  outcome,
  headingRef,
}: {
  outcome: Failure;
  headingRef: React.Ref<HTMLHeadingElement>;
}) {
  const problems = outcome.kind === "unavailable" ? [] : outcome.problems;
  return (
    <div role="alert" className="border border-conflict/60 bg-conflict-soft p-4">
      <h3 ref={headingRef} tabIndex={-1} className="text-subsection font-semibold text-ink">
        {HEADINGS[outcome.kind]}
      </h3>
      {outcome.kind === "invalid" && problems.length > 0 ? null : (
        <p className="mt-1 text-small text-ink-2">{outcome.message}</p>
      )}
      {problems.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {problems.map((p, i) => (
            <li key={i} className="text-small">
              <span className="text-meta text-ink-3">{p.table}</span>
              <p className="mono-id break-words">{p.message}</p>
            </li>
          ))}
        </ul>
      ) : null}
      {outcome.kind === "invalid" ? (
        <p className="mt-3 text-small text-ink-3">
          Nothing was resolved. Fix the lines above and run again.
        </p>
      ) : null}
    </div>
  );
}
