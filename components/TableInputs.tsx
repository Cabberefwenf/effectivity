"use client";

import { useId } from "react";
import { MAX_BODY_BYTES } from "@/lib/limits";
import { TABLES, type Problem, type TableName, type Tables } from "@/lib/api";

const COLUMNS: Record<TableName, string> = {
  units:
    "unit_id, program, effectivity_key, hold_point, hold_point_status, predecessor_hold_status",
  changes:
    "change_id, effectivity_from, effectivity_to, incorporation_hold_point, disposition, supersedes_part, replacement_part",
  material: "unit_id, part, qty_received_to_stores, qty_staged_at_work, qty_installed",
  incorporations: "unit_id, change_id, incorporated",
};

const TITLES: Record<TableName, string> = {
  units: "Units",
  changes: "Changes",
  material: "Material state",
  incorporations: "Incorporations",
};

type Props = {
  tables: Tables;
  problems: readonly Problem[];
  disabled: boolean;
  onChange: (name: TableName, text: string) => void;
  onFileError: (message: string) => void;
};

export function TableInputs({ tables, problems, disabled, onChange, onFileError }: Props) {
  const baseId = useId();
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {TABLES.map((name) => {
        const id = `${baseId}-${name}`;
        const own = problems.filter((p) => p.table === name);
        return (
          <div key={name} className="panel p-4">
            <div className="flex items-baseline justify-between gap-3">
              <label htmlFor={id} className="text-subsection font-semibold text-ink">
                {TITLES[name]}
              </label>
              <label className="btn btn-quiet min-h-0 cursor-pointer px-0 py-0 text-meta">
                Upload CSV
                <input
                  type="file"
                  accept=".csv,text/csv"
                  className="sr-only"
                  disabled={disabled}
                  aria-label={`Upload ${TITLES[name]} CSV file`}
                  onChange={async (event) => {
                    const input = event.currentTarget;
                    const file = input.files?.[0];
                    input.value = "";
                    if (!file) return;
                    if (file.size > MAX_BODY_BYTES) {
                      onFileError(
                        `${file.name} is larger than ${Math.round(MAX_BODY_BYTES / 1024)} KiB, the request limit.`,
                      );
                      return;
                    }
                    onChange(name, await file.text());
                  }}
                />
              </label>
            </div>
            <p id={`${id}-cols`} className="mono-id mt-1 break-words text-ink-3">
              {COLUMNS[name]}
            </p>
            <textarea
              id={id}
              className="field mt-3 h-44 resize-y"
              spellCheck={false}
              autoComplete="off"
              autoCapitalize="off"
              wrap="off"
              value={tables[name]}
              disabled={disabled}
              placeholder="Paste CSV with a header row"
              aria-invalid={own.length > 0}
              aria-describedby={`${id}-cols${own.length > 0 ? ` ${id}-err` : ""}`}
              onChange={(event) => onChange(name, event.target.value)}
            />
            {own.length > 0 ? (
              <ul id={`${id}-err`} className="mt-2 space-y-1 text-small text-conflict">
                {own.map((p, i) => (
                  <li key={i} className="font-mono text-meta break-words">
                    {p.message}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
