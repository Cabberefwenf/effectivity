# ADR 0005: Decision traces, log verification, log backup

Status: Accepted (core rule version still 1.0.0; core decisions unchanged)

## Context

Three audit gaps were listed as limits, not features:

1. A decision carried `rule_ids` but no evidence of why those rules
   fired: the key comparison, the hold comparison, the wrong-material
   quantity, the incorporation record. An auditor had to re-run the
   resolver in their head.
2. The run log is append-only, but nothing ever read it back. A damaged
   log (truncated line, edited counts, broken sequence) would sit
   unnoticed until someone needed it.
3. The log had no backup story: one file, no copy, no checksum.

## Decision

- **Traces.** `effectivity/trace.py` emits one trace per decided pair:
  the decision plus one step per rule R01 to R10, each with whether it
  was evaluated, whether it matched, and the values observed when it
  was checked. The decision always comes from `decide_pair`; the trace
  only explains it. The observed values are the raw inputs to each
  predicate, so a reader can replay the trace against the inputs. CLI:
  `--trace PATH` writes JSONL, one trace per line.
- **Log verification.** `effectivity/verify.py` audits a log file
  without writing to it. It checks the trailing newline, JSON validity,
  the exact record key set, sequence equals line index, input hash shape
  (64 lowercase hex), each decision against the Decision model, decision
  order and uniqueness within a line, and counts recomputed from the
  decisions on that line. It reports the rule versions seen, since
  versions legitimately change across runs. CLI: `--verify-log PATH`,
  exit 0 when clean, 3 when problems are found, 2 when the file is
  missing.
- **Backup.** `tools/backup_log.py` copies a log to a content-hash
  name (`<stem>.<first 12 of sha256>.jsonl`) with a manifest holding the
  full hash, byte count, and line count. The same content twice is a
  no-op; changed content writes a new file, so old backups are never
  overwritten. The copy is hashed after writing and compared to the
  source.

## What verification does not prove

- It does not recompute decisions from inputs. The log does not carry
  inputs, so a log whose decisions were fabricated consistently (valid
  shape, matching counts, sorted) passes verification. Re-run the
  resolver on the inputs and compare decisions if that proof is needed.
- It does not make the log tamper-evident. There is no hash chain and
  no signature; anyone with write access can rewrite a log and it will
  verify. The backup manifest detects accidental damage and later
  edits only if the manifest was kept separately and compared.
- Traces are explanations, not a second decision function. If a trace
  ever disagreed with its decision, the decision is authoritative and
  the trace is a bug. Tests pin the agreement on the examples and on a
  full matrix of inputs.

## Consequences

- Traces and verification are CLI-only. The web function does not
  emit traces and does not read logs; it stays stateless.
- The backup tool is a script, not part of the package. It may use the
  file system, like `effectivity/log.py`; it uses no clock, since names
  derive from content.
