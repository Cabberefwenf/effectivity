import type { Metadata } from "next";
import Link from "next/link";
import { UpgradePlanner } from "@/components/UpgradePlanner";
import { PACKAGES, PACKAGE_ORDER, formatCents, priceQuote } from "@/lib/profit";

export const metadata: Metadata = {
  title: "Packaging and proposed pricing",
  description:
    "Three packages for effectivity: Library, Pilot, and Per programme. Proposed prices only. Billing is off and no charge is made.",
  alternates: { canonical: "/packaging" },
};

export default function PackagingPage() {
  return (
    <div className="max-w-prose space-y-12">
      <section aria-labelledby="top-h">
        <p className="kicker">Packaging</p>
        <h1 id="top-h" className="mt-2 font-serif text-statement font-semibold text-ink">
          Three packages. Proposed prices only.
        </h1>
        <p className="mt-5 text-lede text-ink-2">
          Library is the reference tier. Pilot is one programme for one trial period. Per programme
          is one licence per programme. Prices below are proposed. Billing is off, no charge is
          made, and there is no checkout on this site.
        </p>
      </section>

      <section aria-labelledby="packages-h">
        <h2 id="packages-h" className="text-section font-semibold">
          Packages
        </h2>
        <div className="mt-4 space-y-6">
          {PACKAGE_ORDER.map((id) => {
            const pkg = PACKAGES[id];
            const monthly = priceQuote(id, "monthly");
            const annual = priceQuote(id, "annual");
            return (
              <article key={id} className="panel p-5">
                <h3 className="font-serif text-lg font-semibold text-ink">{pkg.name}</h3>
                <p className="mt-1 text-small text-ink-2">{pkg.tagline}</p>
                <p className="mt-3 text-small text-ink">
                  Proposed: {formatCents(monthly.proposed_cents)} per month, or{" "}
                  {formatCents(annual.proposed_cents)} per year. Annual equals 10 monthly payments.
                  Charge: {formatCents(monthly.charge_amount_cents)}. Billing is off.
                </p>
                <ul className="mt-3 list-disc space-y-1 pl-5 text-small text-ink-2">
                  <li>
                    Limits: {pkg.limits.programmes} programme, {pkg.limits.units} units,{" "}
                    {pkg.limits.changes} changes, {pkg.limits.pairs} pairs, {pkg.limits.seats}{" "}
                    seats.
                  </li>
                  {pkg.features.map((feature) => (
                    <li key={feature}>{feature}</li>
                  ))}
                </ul>
              </article>
            );
          })}
        </div>
      </section>

      <section aria-labelledby="upgrade-h">
        <h2 id="upgrade-h" className="text-section font-semibold">
          Upgrade and downgrade flows
        </h2>
        <p className="mt-2 text-small text-ink-2">
          Every move is recorded in the value ledger with a reason before the new limits apply. A
          downgrade changes limits from the next run. It is not a refund. A move is blocked only
          when current usage exceeds a target limit.
        </p>
        <div className="mt-4">
          <UpgradePlanner />
        </div>
      </section>

      <section aria-labelledby="retention-h">
        <h2 id="retention-h" className="text-section font-semibold">
          Retention
        </h2>
        <p className="mt-2 text-small text-ink-2">
          Retention is a descriptive score from supplied usage periods: active periods, recent
          activity, and value events such as blocked material caught and late units surfaced. It
          describes past use. It predicts nothing. The score and band are on the{" "}
          <Link href="/dashboard" className="link">
            dashboard
          </Link>
          .
        </p>
      </section>

      <section aria-labelledby="ledger-h">
        <h2 id="ledger-h" className="text-section font-semibold">
          Ledger and proof of value
        </h2>
        <p className="mt-2 text-small text-ink-2">
          The value ledger records runs, upgrades, downgrades, renewals, and pilot starts and ends.
          Each run entry carries an evidence reference back to the run it records. The ledger proves
          work done and problems surfaced. It never records revenue, and it claims no customer,
          sale, or measured result.
        </p>
      </section>
    </div>
  );
}
