export const SITE = {
  name: "effectivity",
  description:
    "A deterministic as-built effectivity resolver. Per unit and change: six states, a stable reason code and the rule ids that fired. Synthetic data only.",
  repoUrl: "https://github.com/Cabberefwenf/effectivity",
  limitsUrl: "https://github.com/Cabberefwenf/effectivity/blob/main/LIMITS.md",
  stateMachineUrl: "https://github.com/Cabberefwenf/effectivity/blob/main/docs/state-machine.md",
  adrKeyUrl:
    "https://github.com/Cabberefwenf/effectivity/blob/main/docs/adr/0001-effectivity-key.md",
  notice: "Synthetic data only. Do not upload export-controlled or customer files.",
} as const;

/** Absolute origin for canonical URLs and Open Graph images. Never needs a secret. */
export function siteOrigin(env: Record<string, string | undefined> = process.env): string {
  const explicit = env.NEXT_PUBLIC_SITE_URL;
  if (explicit) return explicit.replace(/\/+$/, "");
  const vercel = env.VERCEL_PROJECT_PRODUCTION_URL;
  if (vercel) return `https://${vercel}`;
  return "http://localhost:3000";
}

/** Only the production deployment may be indexed; previews and local builds are noindex. */
export function isIndexable(env: Record<string, string | undefined> = process.env): boolean {
  return env.VERCEL_ENV === "production";
}
