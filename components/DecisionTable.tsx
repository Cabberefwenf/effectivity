"use client";

import { useState } from "react";
import type { Decision } from "@/lib/schema";
import { StateChip } from "./StateChip";

const PAGE = 200;

type Props = {
  decisions: readonly Decision[];
  total: number;
  activeRule: string | null;
  onRule: (id: string) => void;
};

export function DecisionTable({ decisions, total, activeRule, onRule }: Props) {
  const [shown, setShown] = useState(PAGE);
  const visible = decisions.slice(0, shown);

  if (decisions.length === 0) {
    return (
      <div className="panel p-6" role="status">
        <p className="text-ink">No decisions match these filters.</p>
        <p className="mt-1 text-small text-ink-3">
          {total} decision{total === 1 ? "" : "s"} in this run. Clear a state or the search to see
          them.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="panel overflow-x-auto">
        <table className="w-full min-w-[44rem] border-collapse text-left text-small">
          <caption className="sr-only">
            Decisions per unit and change: state, reason code and the rules that fired
          </caption>
          <thead>
            <tr className="border-b border-rule-strong text-meta text-ink-3">
              <th scope="col" className="px-3 py-2 font-medium">
                Unit
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                Change
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                State
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                Reason code
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                Rules fired
              </th>
            </tr>
          </thead>
          <tbody>
            {visible.map((d) => (
              <tr
                key={`${d.unit_id}|${d.change_id}`}
                className="border-b border-rule last:border-b-0"
              >
                <th scope="row" className="mono-id px-3 py-2 font-normal">
                  {d.unit_id}
                </th>
                <td className="mono-id px-3 py-2">{d.change_id}</td>
                <td className="px-3 py-2">
                  <StateChip state={d.status} />
                </td>
                <td className="mono-id px-3 py-2 break-all">{d.reason_code}</td>
                <td className="px-3 py-2">
                  <span className="flex flex-wrap gap-1">
                    {d.rule_ids.map((id) => (
                      <button
                        key={id}
                        type="button"
                        onClick={() => onRule(id)}
                        aria-pressed={activeRule === id}
                        aria-label={`Show rule ${id}`}
                        className={`border px-2 py-0.5 font-mono text-meta text-engineering ${
                          activeRule === id
                            ? "border-engineering bg-engineering-soft"
                            : "border-rule-strong hover:border-engineering"
                        }`}
                      >
                        {id}
                      </button>
                    ))}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-small text-ink-3">
        <p role="status">
          Showing {visible.length} of {decisions.length}
          {decisions.length !== total ? ` filtered decisions (${total} in this run)` : " decisions"}
          .
        </p>
        {visible.length < decisions.length ? (
          <button type="button" className="btn" onClick={() => setShown((n) => n + PAGE)}>
            Show {Math.min(PAGE, decisions.length - visible.length)} more
          </button>
        ) : null}
      </div>
    </div>
  );
}
