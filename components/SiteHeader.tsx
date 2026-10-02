import Link from "next/link";
import { SITE } from "@/lib/site";

const NAV = [
  { href: "/", label: "Resolver" },
  { href: "/rules", label: "Rules" },
  { href: "/about", label: "About and limits" },
] as const;

export function SiteHeader() {
  return (
    <header className="border-b border-rule bg-bg">
      <div className="shell flex flex-wrap items-center justify-between gap-x-8 gap-y-2 py-3">
        <Link href="/" className="font-serif text-lg font-semibold text-ink">
          {SITE.name}
        </Link>
        <nav
          aria-label="Primary"
          className="flex flex-wrap items-center gap-x-6 gap-y-1 text-small"
        >
          {NAV.map((item) => (
            <Link key={item.href} href={item.href} className="py-1 text-ink-2 hover:text-ink">
              {item.label}
            </Link>
          ))}
          <a
            href={SITE.repoUrl}
            className="py-1 text-ink-2 hover:text-ink"
            rel="noopener noreferrer"
          >
            Source
          </a>
        </nav>
      </div>
    </header>
  );
}
