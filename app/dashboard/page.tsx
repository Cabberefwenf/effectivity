import type { Metadata } from "next";
import Link from "next/link";
import { ProfitDashboard } from "@/components/ProfitDashboard";
import { DEMO_LEDGER, DEMO_RETENTION_PERIODS, DEMO_USAGE, dashboardSummary } from "@/lib/profit";

export const metadata: Metadata = {
  title: "Dashboard: usage, conversion, retention",
  description:
    "Dashboard showing usage against package limits, conversion, retention, and proof of value delivered. Demo data only. Billing is off and revenue is zero.",
  alternates: { canonical: "/dashboard" },
};

export default function DashboardPage() {
  const summary = dashboardSummary({
    package_id: "pilot",
    usage: DEMO_USAGE,
    ledger_entries: DEMO_LEDGER,
    retention_periods: DEMO_RETENTION_PERIODS,
  });
  return (
    <div className="max-w-prose space-y-12">
      <section aria-labelledby="top-h">
        <p className="kicker">Dashboard</p>
        <h1 id="top-h" className="mt-2 font-serif text-statement font-semibold text-ink">
          Usage, conversion, retention, and proof of value
        </h1>
        <p className="mt-5 text-lede text-ink-2">
          Demonstration data only. The ledger entries come from the bundled synthetic example and a
          second demonstration run. There are no real customers, no paying programmes, and no
          revenue. Billing is off.
        </p>
        <p className="mt-4 text-small text-ink-2">
          Packages and proposed prices are on the{" "}
          <Link href="/packaging" className="link">
            packaging page
          </Link>
          . The method is in{" "}
          <a
            href="https://github.com/Cabberefwenf/effectivity/blob/main/docs/profit.md"
            className="link"
            rel="noopener noreferrer"
          >
            docs/profit.md
          </a>
          .
        </p>
      </section>
      <ProfitDashboard summary={summary} />
    </div>
  );
}
