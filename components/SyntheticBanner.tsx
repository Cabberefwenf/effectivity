import Link from "next/link";
import { SITE } from "@/lib/site";

/** Persistent on every page. Not dismissible: the rule it states does not expire. */
export function SyntheticBanner() {
  return (
    <aside
      aria-label="Data notice"
      className="sticky top-0 z-40 border-b border-unresolved/40 bg-unresolved-soft"
    >
      <div className="shell flex flex-wrap items-center gap-x-4 gap-y-1 py-2 text-small text-ink">
        <p className="font-medium">{SITE.notice}</p>
        <p className="text-ink-2">
          This site does not store or log what you paste.{" "}
          <Link href="/about#privacy" className="link">
            How
          </Link>
          {" · "}
          <a href={SITE.limitsUrl} className="link" rel="noopener noreferrer">
            Limits
          </a>
        </p>
      </div>
    </aside>
  );
}
