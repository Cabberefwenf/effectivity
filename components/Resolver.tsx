"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { resolveTables, TABLES, type Outcome, type TableName, type Tables } from "@/lib/api";
import { countByState, filterDecisions, toggleState } from "@/lib/filter";
import { type Report } from "@/lib/schema";
import type { State } from "@/lib/states";
import { Counts } from "./Counts";
import { DecisionTable } from "./DecisionTable";
import { Problems } from "./Problems";
import { RulePanel } from "./RulePanel";
import { TableInputs } from "./TableInputs";

const EMPTY: Tables = { units: "", changes: "", material: "", incorporations: "" };

type Phase =
  | { tag: "idle" }
  | { tag: "running" }
  | { tag: "done"; report: Report }
  | { tag: "failed"; outcome: Exclude<Outcome, { kind: "ok" }> };

export function Resolver({ sample }: { sample: Tables }) {
  const [tables, setTables] = useState<Tables>(EMPTY);
  const [phase, setPhase] = useState<Phase>({ tag: "idle" });
  const [selected, setSelected] = useState<ReadonlySet<State>>(new Set());
  const [query, setQuery] = useState("");
  const [rule, setRule] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const controller = useRef<AbortController | null>(null);
  const errorHeading = useRef<HTMLHeadingElement>(null);
  const resultsHeading = useRef<HTMLHeadingElement>(null);

  useEffect(() => () => controller.current?.abort(), []);

  const running = phase.tag === "running";
  const hasInput = TABLES.some((name) => tables[name].trim() !== "");
  const problems =
    phase.tag === "failed" && phase.outcome.kind !== "unavailable" ? phase.outcome.problems : [];

  const edit = useCallback((name: TableName, text: string) => {
    setTables((current) => ({ ...current, [name]: text }));
  }, []);

  const run = useCallback(async (input: Tables) => {
    controller.current?.abort();
    const next = new AbortController();
    controller.current = next;
    setPhase({ tag: "running" });
    setNotice("Resolving.");
    let outcome: Outcome;
    try {
      outcome = await resolveTables(input, { signal: next.signal });
    } catch {
      return; // superseded by a newer run, or the page was left
    }
    if (next.signal.aborted) return;
    if (outcome.kind === "ok") {
      setPhase({ tag: "done", report: outcome.report });
      setSelected(new Set());
      setQuery("");
      setRule(null);
      setNotice(`Resolved ${outcome.report.decisions.length} decisions.`);
      requestAnimationFrame(() => resultsHeading.current?.focus());
    } else {
      setPhase({ tag: "failed", outcome });
      setNotice("Resolving failed. See the errors below.");
      requestAnimationFrame(() => errorHeading.current?.focus());
    }
  }, []);

  const report = phase.tag === "done" ? phase.report : null;
  const visible = useMemo(
    () => (report ? filterDecisions(report.decisions, selected, query) : []),
    [report, selected, query],
  );
  const counts = useMemo(
    () => (report ? (report.counts as Record<State, number>) : countByState([])),
    [report],
  );
  const filtering = selected.size > 0 || query.trim() !== "";

  function download() {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2) + "\n"], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `effectivity-${report.input_hash.slice(0, 12)}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-10">
      <section aria-labelledby="inputs-h" className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="kicker">Input</p>
            <h2 id="inputs-h" className="mt-1 text-section font-semibold">
              Four tables
            </h2>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn"
              disabled={running}
              onClick={() => {
                setTables(sample);
                void run(sample);
              }}
            >
              Load synthetic sample and run
            </button>
            <button
              type="button"
              className="btn"
              disabled={running || !hasInput}
              onClick={() => {
                controller.current?.abort();
                setTables(EMPTY);
                setPhase({ tag: "idle" });
                setNotice("Cleared.");
              }}
            >
              Clear
            </button>
          </div>
        </div>

        <TableInputs
          tables={tables}
          problems={problems}
          disabled={running}
          onChange={edit}
          onFileError={(message) =>
            setPhase({ tag: "failed", outcome: { kind: "limit", message, problems: [] } })
          }
        />

        <div className="flex flex-wrap items-center gap-4">
          <button
            type="button"
            className="btn btn-primary"
            disabled={running || !hasInput}
            onClick={() => void run(tables)}
          >
            {running ? "Resolving" : "Resolve"}
          </button>
          <p className="text-small text-ink-3">
            Sent to the resolver as one request. Not stored, not logged.
          </p>
        </div>
      </section>

      <p role="status" aria-live="polite" className="sr-only">
        {notice}
      </p>

      <section aria-labelledby="results-h" aria-busy={running} className="space-y-4">
        <div>
          <p className="kicker">Result</p>
          <h2
            id="results-h"
            ref={resultsHeading}
            tabIndex={-1}
            className="mt-1 text-section font-semibold"
          >
            Decisions
          </h2>
        </div>

        {phase.tag === "idle" ? (
          <div className="panel p-6">
            <p className="text-ink">No results yet.</p>
            <p className="mt-1 max-w-prose text-small text-ink-3">
              Load the synthetic sample to see all six states, or paste your own tables and press
              Resolve. Every unit is checked against every change.
            </p>
          </div>
        ) : null}

        {running ? (
          <div className="panel p-6" role="status">
            <p className="text-ink">Resolving.</p>
            <div className="mt-3 h-2 w-48 animate-pulse bg-elevated motion-reduce:animate-none" />
          </div>
        ) : null}

        {phase.tag === "failed" ? (
          <Problems outcome={phase.outcome} headingRef={errorHeading} />
        ) : null}

        {report ? (
          <div className="space-y-4">
            <dl className="grid gap-x-8 gap-y-2 text-small sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <dt className="text-meta text-ink-3">Input</dt>
                <dd>
                  {report.inputs.units} units, {report.inputs.changes} changes,{" "}
                  {report.inputs.material} material rows, {report.inputs.incorporations}{" "}
                  incorporation rows
                </dd>
              </div>
              <div>
                <dt className="text-meta text-ink-3">Decisions</dt>
                <dd>{report.decisions.length}</dd>
              </div>
              <div>
                <dt className="text-meta text-ink-3">Rule version</dt>
                <dd className="mono-id">{report.rule_version}</dd>
              </div>
              <div>
                <dt className="text-meta text-ink-3">Input hash (SHA-256)</dt>
                <dd className="mono-id break-all" data-testid="input-hash">
                  {report.input_hash}
                </dd>
              </div>
            </dl>

            <Counts
              counts={counts}
              selected={selected}
              onToggle={(state) => setSelected((current) => toggleState(current, state))}
            />

            <div className="flex flex-wrap items-end gap-3">
              <div className="min-w-[16rem] flex-1">
                <label htmlFor="q" className="text-meta text-ink-3">
                  Search unit, change, reason code or rule
                </label>
                <input
                  id="q"
                  type="search"
                  className="field mt-1 font-sans text-small"
                  value={query}
                  autoComplete="off"
                  onChange={(event) => setQuery(event.target.value)}
                />
              </div>
              {filtering ? (
                <button
                  type="button"
                  className="btn"
                  onClick={() => {
                    setSelected(new Set());
                    setQuery("");
                  }}
                >
                  Clear filters
                </button>
              ) : null}
              <button type="button" className="btn" onClick={download}>
                Download JSON
              </button>
            </div>

            <div className="grid grid-cols-[minmax(0,1fr)] items-start gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
              <div className={rule ? "order-2 min-w-0 lg:order-1" : "min-w-0"}>
                <DecisionTable
                  decisions={visible}
                  total={report.decisions.length}
                  activeRule={rule}
                  onRule={(id) => setRule((current) => (current === id ? null : id))}
                />
              </div>
              {rule ? (
                <div className="order-1 lg:sticky lg:top-24 lg:order-2">
                  <RulePanel ruleId={rule} onClose={() => setRule(null)} />
                </div>
              ) : null}
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
