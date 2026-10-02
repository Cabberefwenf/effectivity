import { readFileSync } from "node:fs";

/**
 * The security headers live in vercel.json (one source of truth, tested in
 * lib/security-headers.test.ts). Vercel applies them itself. Here they are applied
 * to a local production server (`next start`, used by the E2E suite) so the same
 * policy is exercised before deploy. `next dev` needs eval and websockets, so it
 * runs without the policy.
 */
function localHeaders() {
  if (process.env.VERCEL || process.env.NODE_ENV !== "production") return [];
  const config = JSON.parse(readFileSync(new URL("./vercel.json", import.meta.url), "utf8"));
  return config.headers.filter((entry) => entry.source === "/(.*)");
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  compress: true,
  typescript: { ignoreBuildErrors: false },
  // Lint runs as its own gate (`npm run lint`); a build must not mask type errors.
  eslint: { ignoreDuringBuilds: true },
  async headers() {
    return localHeaders();
  },
  async rewrites() {
    // Local only: the Python function is served by tools/dev_api.py. On Vercel,
    // api/resolve.py is deployed by the Python runtime and no rewrite is needed.
    if (process.env.VERCEL) return [];
    const target = process.env.EFFECTIVITY_API_ORIGIN ?? "http://127.0.0.1:8787";
    return [{ source: "/api/:path*", destination: `${target}/api/:path*` }];
  },
};

export default nextConfig;
