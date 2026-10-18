import { DEMO_USAGE, formatCents } from "@/lib/profit";
import type { dashboardSummary } from "@/lib/profit";

type Summary = ReturnType<typeof dashboardSummary>;

function Row({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <tr className="border-t border-rule">
      <th scope="row" className="py-2 pr-4 text-left font-normal text-ink-2">
        {label}
      </th>
      <td className="py-2 pr-4 text-ink">{value}</td>
      {note !== undefined ? <td className="py-2 text-ink-3">{note}</td> : null}
    </tr>
  );
}

/** Renders dashboard aggregates computed by lib/profit. No data is fetched or stored. */
export function ProfitDashboard({ summary }: { summary: Summary }) {
  const { usage_vs_limits, retention, ledger, funnel, billing } = summary;
  const conversion = (value: number | null) =>
    value === null ? "No data" : `${(value * 100).toFixed(1)}%`;
  return (
    <div className="space-y-12">
      <section aria-labelledby="usage-h" className="panel p-5">
        <h2 id="usage-h" className="text-section font-semibold">
          Usage against the {summary.package.name} limits
        </h2>
        <table className="mt-4 w-full text-small">
          <thead>
            <tr className="text-left text-ink-3">
              <th scope="col" className="py-2 pr-4 font-normal">
                Limit
              </th>
              <th scope="col" className="py-2 pr-4 font-normal">
                Used
              </th>
              <th scope="col" className="py-2 font-normal">
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {(Object.keys(usage_vs_limits) as Array<keyof typeof usage_vs_limits>).map((key) => {
              const row = usage_vs_limits[key];
              return (
                <tr key={key} className="border-t border-rule">
                  <th scope="row" className="py-2 pr-4 text-left font-normal text-ink-2">
                    {key}
                  </th>
                  <td className="py-2 pr-4 text-ink">
                    {row.used} of {row.limit}
                    {row.percent !== null ? ` (${row.percent}%)` : ""}
                  </td>
                  <td className="py-2 text-ink">{row.over ? "Over limit" : "Within limit"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <section aria-labelledby="value-h" className="panel p-5">
        <h2 id="value-h" className="text-section font-semibold">
          Proof of value delivered
        </h2>
        <p className="mt-2 text-small text-ink-2">
          Counts from the value ledger. Each run entry carries an evidence reference. The ledger
          records work done and problems surfaced. It never records revenue.
        </p>
        <table className="mt-4 w-full text-small">
          <tbody>
            <Row label="Ledger entries" value={String(ledger.entries)} />
            <Row label="Decisions recorded" value={String(ledger.totals.decisions)} />
            <Row label="Blocked material caught" value={String(ledger.totals.blocked_material)} />
            <Row label="Late units surfaced" value={String(ledger.totals.late_surfaced)} />
            <Row label="Incorporations recorded" value={String(ledger.totals.incorporated)} />
            <Row
              label="Real revenue"
              value={formatCents(billing.real_revenue_cents)}
              note="Billing is off. No charge has been made."
            />
          </tbody>
        </table>
      </section>

      <section aria-labelledby="funnel-h" className="panel p-5">
        <h2 id="funnel-h" className="text-section font-semibold">
          Conversion
        </h2>
        <p className="mt-2 text-small text-ink-2">
          This site runs no analytics, so the funnel is zero until real counts are supplied. A zero
          funnel reports no rate, not an estimated rate.
        </p>
        <table className="mt-4 w-full text-small">
          <tbody>
            <Row label="Visitors" value={String(funnel.visitors)} />
            <Row label="Trials started" value={String(funnel.trials_started)} />
            <Row label="Pilots started" value={String(funnel.pilots_started)} />
            <Row label="Paid programmes" value={String(funnel.paid_programmes)} />
            <Row label="Visitor to trial" value={conversion(funnel.conversion.visitor_to_trial)} />
            <Row label="Trial to pilot" value={conversion(funnel.conversion.trial_to_pilot)} />
            <Row label="Pilot to paid" value={conversion(funnel.conversion.pilot_to_paid)} />
            <Row label="Visitor to paid" value={conversion(funnel.conversion.visitor_to_paid)} />
          </tbody>
        </table>
      </section>

      <section aria-labelledby="retention-h" className="panel p-5">
        <h2 id="retention-h" className="text-section font-semibold">
          Retention
        </h2>
        <p className="mt-2 text-small text-ink-2">
          Descriptive score from the supplied usage periods. It describes past use. It predicts
          nothing.
        </p>
        <table className="mt-4 w-full text-small">
          <tbody>
            <Row label="Score" value={`${retention.score} of 100`} />
            <Row label="Band" value={retention.band} />
            <Row label="Active periods" value={String(retention.active_periods)} />
            <Row label="Periods supplied" value={String(retention.periods_supplied)} />
            <Row label="Recent period active" value={retention.recent_active ? "Yes" : "No"} />
            <Row label="Value events" value={String(retention.value_events)} />
          </tbody>
        </table>
      </section>

      <p className="text-small text-ink-3">
        Demo usage: {DEMO_USAGE.units} units, {DEMO_USAGE.changes} changes, {DEMO_USAGE.pairs}{" "}
        pairs. Demo ledger only. Not real customers.
      </p>
    </div>
  );
}
