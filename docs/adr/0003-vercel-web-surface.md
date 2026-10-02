# ADR 0003: A thin web surface on Vercel, with Python as the only decision logic

Status: Accepted (rule version 1.0.0; no decision behavior changed)

## Context

The tool was a CLI. It now also needs a deployable web page so the six-state
result can be seen without installing anything. The page must not become a
second implementation of the rules: ADR 0002 only holds if there is one
decision function.

## Decision

- **One resolver.** The web function calls the same `effectivity` package that
  the CLI calls. The frontend is TypeScript and contains no state logic. It
  filters, sorts and displays what the function returned, and it validates the
  reply's shape (zod) before showing it. A change to a rule is a change to
  `src/effectivity/resolve.py` and `docs/state-machine.md`, and the rule text on
  the site is generated from that document (`scripts/gen-rules.mjs`, with a
  drift check in CI).
- **Shape.** Next.js 15 (App Router, React 19, TypeScript strict) at the
  repository root, plus one Python function, `api/resolve.py`, in Vercel's
  file-based `/api` convention. The root has no Root Directory setting to
  choose, and `vercel.json` sets framework, install and build commands, so a
  Git import or `vercel --prod` needs no dashboard changes and no environment
  variables.
- **Python function.** `api/resolve.py` is a thin WSGI wrapper. It adds `src/`
  to `sys.path` and exports `effectivity.service.wsgi_app`. `vercel.json`
  bundles `src/**` with the function (`includeFiles`) and leaves out the rest.
  Dependencies are declared in `requirements.txt` (`pydantic>=2,<3`) and in
  `pyproject.toml`; the two agree. `.python-version` pins 3.12.
- **Request.** `POST /api/resolve` with JSON `{units, changes, material,
  incorporations}`, each a CSV text. The reply is the same report the CLI's
  log line carries: `rule_version`, `input_hash`, counts, and decisions with
  reason code and rule ids. `tests/golden/examples-report.json` is the CLI's
  output on `examples/`, and a test requires the function to return exactly it.
- **Stateless.** No database, file store, queue, cookie or session. The
  function does not import `logging`, the file system, the network or the
  clock (a test checks the imports), and an unexpected exception becomes a
  fixed 500 message that echoes nothing from the request.
- **Caps.** 256 KiB body, 1,000 / 200 / 5,000 / 5,000 rows for units / changes
  / material / incorporations, and 5,000 unit-and-change pairs. Past a cap the
  request is refused (413), never truncated. The caps live in `service.py` and
  `lib/limits.ts`; a test keeps them equal.
- **Same origin only.** No CORS headers are sent. The browser calls
  `/api/resolve` on the same host; `connect-src 'self'` enforces it.
- **Headers.** Security headers are set once, in `vercel.json`: CSP with
  `frame-ancestors 'none'`, nosniff, a strict referrer policy,
  `X-Frame-Options`, COOP/CORP, a restrictive Permissions-Policy and HSTS.
  `next start` applies the same list locally so the end-to-end suite sees the
  real policy. A test reads `vercel.json` and asserts the directives.

## Alternatives considered

- **Vercel Services (monorepo with a `web/` and a `api/` service).** Cleaner
  separation, but it is a beta feature and needs the Services configuration to
  be recognized. File-based `/api` functions are the documented, stable path
  and the same shape as Vercel's own Next.js plus Python example.
- **A Python framework preset (FastAPI or Flask).** It would take precedence
  over the file-based function and route every request to Python, which
  defeats the Next.js frontend. It also adds a dependency for one endpoint.
- **Porting the resolver to TypeScript for a pure-Next deployment.** Rejected.
  Two implementations of the rules is exactly the drift ADR 0002 exists to
  prevent.
- **Running the resolver in the browser (Pyodide).** Heavy, slow to start, and
  moves the single source of truth into a bundle we would have to version.

## Consequences

- The function cold-starts on the first request after idle. The page says so.
- The CSP keeps `'unsafe-inline'` for scripts and styles because the Next.js
  App Router emits inline bootstrap scripts, and a nonce-based policy would
  make every page dynamic. There is no `eval`, no remote origin, and no
  user-supplied HTML is ever rendered (React escapes text), so the residual is
  inline code that the site itself ships. Revisit if pages become dynamic.
- Vercel records ordinary request metadata (time, path, status) for any
  deployment. The function adds nothing, and the request body is not part of
  that metadata. The page says what it does and does not control.
- The privacy claim is "the code stores and logs nothing". It is not a claim
  about the host. The site is for synthetic data for that reason.
- Not verified without a Vercel account: that Vercel's Python runtime installs
  `requirements.txt` exactly as the clean-virtualenv check does, and that the
  platform routes `/api/resolve` to the function next to the Next.js build.
  Both follow the documented conventions; the first deploy confirms them.
