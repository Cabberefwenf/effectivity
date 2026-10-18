"use client";

import { useState } from "react";
import {
  DEMO_USAGE,
  PACKAGES,
  PACKAGE_ORDER,
  isPackageId,
  upgradeEligibility,
  upgradePath,
  type PackageId,
} from "@/lib/profit";

/** Upgrade planner. Shows steps and eligibility for editable usage. It charges nothing and sends nothing. */
export function UpgradePlanner() {
  const [current, setCurrent] = useState<PackageId>("library");
  const [target, setTarget] = useState<PackageId>("pilot");
  const [units, setUnits] = useState(DEMO_USAGE.units ?? 0);
  const usage = { ...DEMO_USAGE, units };
  const path = upgradePath(current, target);
  const eligibility = upgradeEligibility(current, target, usage);
  const limitRows = Object.entries(path.limits_change);
  return (
    <div className="panel p-5">
      <div className="flex flex-wrap gap-6">
        <label className="block">
          <span className="block text-small text-ink-2">Units in use</span>
          <input
            className="mt-1 w-28 border border-rule-strong bg-inset px-3 py-2 text-small text-ink"
            type="number"
            min={0}
            value={units}
            onChange={(event) => setUnits(Number(event.target.value))}
          />
        </label>
        <label className="block">
          <span className="block text-small text-ink-2">Current package</span>
          <select
            className="mt-1 border border-rule-strong bg-inset px-3 py-2 text-small text-ink"
            value={current}
            onChange={(event) => {
              if (isPackageId(event.target.value)) setCurrent(event.target.value);
            }}
          >
            {PACKAGE_ORDER.map((id) => (
              <option key={id} value={id}>
                {PACKAGES[id].name}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="block text-small text-ink-2">Target package</span>
          <select
            className="mt-1 border border-rule-strong bg-inset px-3 py-2 text-small text-ink"
            value={target}
            onChange={(event) => {
              if (isPackageId(event.target.value)) setTarget(event.target.value);
            }}
          >
            {PACKAGE_ORDER.map((id) => (
              <option key={id} value={id}>
                {PACKAGES[id].name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <p className="mt-4 text-small" role="status">
        {path.kind === "same"
          ? "No move needed."
          : eligibility.allowed
            ? `This ${path.kind} is allowed for the demo usage.`
            : `This ${path.kind} is blocked for the demo usage.`}
      </p>
      {eligibility.blockers.length > 0 ? (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-small text-ink-2">
          {eligibility.blockers.map((blocker) => (
            <li key={blocker}>{blocker}</li>
          ))}
        </ul>
      ) : null}
      <ol className="mt-4 list-decimal space-y-2 pl-5 text-small text-ink-2">
        {path.steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      {limitRows.length > 0 ? (
        <table className="mt-4 w-full text-small">
          <thead>
            <tr className="text-left text-ink-3">
              <th scope="col" className="py-2 pr-4 font-normal">
                Limit
              </th>
              <th scope="col" className="py-2 pr-4 font-normal">
                From
              </th>
              <th scope="col" className="py-2 font-normal">
                To
              </th>
            </tr>
          </thead>
          <tbody>
            {limitRows.map(([key, change]) => (
              <tr key={key} className="border-t border-rule">
                <th scope="row" className="py-2 pr-4 text-left font-normal text-ink-2">
                  {key}
                </th>
                <td className="py-2 pr-4 text-ink">{change.from}</td>
                <td className="py-2 text-ink">{change.to}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      <p className="mt-4 text-small text-ink-3">
        Other usage held at the demo values: {DEMO_USAGE.changes} changes, {DEMO_USAGE.pairs} pairs,{" "}
        {DEMO_USAGE.seats} seat. No payment is taken on this page. Billing is off.
      </p>
    </div>
  );
}
