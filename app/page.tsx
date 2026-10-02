import { Resolver } from "@/components/Resolver";
import { loadSample } from "@/lib/sample";

export default function HomePage() {
  const sample = loadSample();
  return (
    <>
      <section aria-labelledby="top-h" className="max-w-prose">
        <p className="kicker">As-built effectivity</p>
        <h1 id="top-h" className="mt-2 font-serif text-statement font-semibold text-ink">
          Which units does this change reach, and where does each one stand?
        </h1>
        <p className="mt-5 text-lede text-ink-2">
          Four tables in: units, changes, material state, incorporations. For every unit and change,
          one of six states, a stable reason code and the rule ids that fired. The same input always
          gives the same answer.
        </p>
        <ul className="mt-6 space-y-2 text-small text-ink-2">
          <li>It classifies. It does not authorize work, and a human still signs incorporation.</li>
          <li>The decision function reads no clock, database, network or model.</li>
          <li>Synthetic data only. Nothing you paste is stored or logged.</li>
        </ul>
      </section>
      <div className="mt-12">
        <Resolver sample={sample} />
      </div>
    </>
  );
}
