import type { Metadata } from "next";
import Link from "next/link";
import { MAX_BODY_BYTES, MAX_PAIRS, MAX_ROWS } from "@/lib/limits";
import { SITE } from "@/lib/site";

export const metadata: Metadata = {
  title: "About and limits",
  description:
    "What effectivity is and is not, what this site does with your input, and its size limits.",
  alternates: { canonical: "/about" },
};

export default function AboutPage() {
  return (
    <div className="max-w-prose space-y-12">
      <section aria-labelledby="what-h">
        <p className="kicker">About</p>
        <h1 id="what-h" className="mt-2 font-serif text-statement font-semibold">
          What this is, and is not
        </h1>
        <p className="mt-5 text-lede text-ink-2">
          A small resolver for one question that is usually answered by hand: for each unit and each
          engineering change, is the change in effect, has the unit reached the incorporation hold
          point, is superseded material in the way, and is the change already incorporated.
        </p>
        <ul className="mt-6 list-disc space-y-2 pl-5 text-small text-ink-2">
          <li>It classifies. It does not authorize work. A human still signs incorporation.</li>
          <li>
            The decision logic is one Python module with no clock, database, network or model. This
            site is a thin shell around it. The browser never decides anything.
          </li>
          <li>
            The input is the four tables described in the{" "}
            <a href={SITE.repoUrl} className="link" rel="noopener noreferrer">
              repository
            </a>
            . The effectivity key rule is in{" "}
            <a href={SITE.adrKeyUrl} className="link" rel="noopener noreferrer">
              ADR 0001
            </a>
            .
          </li>
          <li>
            There are no customers and no measured results to report. This is a demonstration of a
            method on synthetic data.
          </li>
        </ul>
      </section>

      <section id="privacy" aria-labelledby="privacy-h" className="scroll-mt-28">
        <p className="kicker">Your input</p>
        <h2 id="privacy-h" className="mt-1 text-section font-semibold">
          What this site does with what you paste
        </h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-small text-ink-2">
          <li>
            The four tables are sent in one request to a stateless function, resolved in memory and
            returned. There is no database, file store or queue. The function does not write the
            request body anywhere and does not log it.
          </li>
          <li>
            There are no accounts, cookies, analytics or third-party requests from these pages.
          </li>
          <li>
            The hosting platform records ordinary request metadata, such as time, path and status,
            as any host does. That metadata does not contain the request body.
          </li>
          <li>
            Use synthetic data only. Do not upload export-controlled or customer files. This is a
            public demonstration, not an approved system for controlled data.
          </li>
        </ul>
      </section>

      <section aria-labelledby="limits-h">
        <p className="kicker">Limits</p>
        <h2 id="limits-h" className="mt-1 text-section font-semibold">
          Size caps and cold starts
        </h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-small text-ink-2">
          <li>
            Request body: {MAX_BODY_BYTES / 1024} KiB. Rows: {MAX_ROWS.units} units,{" "}
            {MAX_ROWS.changes} changes, {MAX_ROWS.material} material rows, {MAX_ROWS.incorporations}{" "}
            incorporation rows. At most {MAX_PAIRS} unit and change pairs. Past a cap the request is
            refused with a message, never truncated.
          </li>
          <li>
            The function can take a second or two on the first request after idle (a cold start).
          </li>
          <li>The results are not saved. Download the JSON if you need to keep them.</li>
        </ul>
        <p className="mt-4 text-small">
          The full list is in{" "}
          <a href={SITE.limitsUrl} className="link" rel="noopener noreferrer">
            LIMITS.md
          </a>
          . Back to the{" "}
          <Link href="/" className="link">
            resolver
          </Link>
          .
        </p>
      </section>
    </div>
  );
}
