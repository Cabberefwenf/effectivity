# ADR 0002: No clock, network, or I/O in the decision function

Status: Accepted (rule version 1.0.0)

## Context

The tool is only worth trusting if the same inputs and the same rule version
always give the same decisions, today and in an audit replay next year. A
decision that reads the clock, the network, an environment variable, or a file
cannot promise that.

## Decision

- `effectivity.resolve` is a pure function of already-parsed models. It takes
  no clock, no path, no handle. It imports only `__future__`,
  `collections.abc`, and `effectivity.model`.
- No rule uses time. If a future rule needs time, it must be an explicit input
  field of the models, and the rule version must change.
- The run log (`effectivity.log`) never reads the clock either. The only
  time-like field is `run_at`, an optional opaque string the caller passes in
  (`--run-at` on the CLI). It is stored verbatim, is `null` when not given, is
  never parsed, and is **not** part of the input hash or of any decision.
- The input hash is SHA-256 over a canonical serialization of the four parsed
  input tables (sorted keys, compact separators, rows sorted by their own
  serialization, so row order in the CSV files does not matter).
- The log is append-only: each run builds one whole newline-terminated line and
  writes it with a single unbuffered write to a file opened in binary append
  mode, and existing lines are never rewritten. If anything fails before the
  write, the file is untouched. A short write is reported as an error, but a
  crash or power loss mid-write can still leave a partial line; the next run
  refuses to append to a file that does not end in a newline.

## Enforcement and its limits

- A test parses `resolve.py` and fails on any import outside the allowlist, and
  on calls to `open`, `print`, `eval`, `exec`, `__import__`, or any `now`,
  `today`, `utcnow`, `time` attribute.
- A second test runs the resolver with `time.time`, `time.monotonic`,
  `time.perf_counter`, `socket.socket`, `socket.create_connection`, and `open`
  patched to raise.
- A third test runs the CLI in subprocesses with different `PYTHONHASHSEED`
  values, time zones, locales, and working directories and compares the bytes.
- These are static and behavioural checks of this module. They do not prove
  that no imported third-party code (pydantic) ever touches the clock. The
  guarantee for "no network calls" is the import allowlist plus the patched
  run, nothing stronger. This is stated in LIMITS.md.
