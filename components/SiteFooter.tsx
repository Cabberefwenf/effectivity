import { RULE_VERSION } from "@/lib/rules";
import { SITE } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t border-rule">
      <div className="shell flex flex-wrap items-baseline justify-between gap-x-8 gap-y-2 py-8 text-meta text-ink-3">
        <p>
          Classifies; does not authorize work. A human still signs incorporation. Rule version{" "}
          <span className="mono-id">{RULE_VERSION}</span>.
        </p>
        <p>
          <a href={SITE.repoUrl} className="link" rel="noopener noreferrer">
            Source on GitHub
          </a>
          {" · "}
          <a href={SITE.limitsUrl} className="link" rel="noopener noreferrer">
            LIMITS.md
          </a>
        </p>
      </div>
    </footer>
  );
}
