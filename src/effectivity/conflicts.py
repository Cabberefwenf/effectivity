"""Exactly-one-match: two live changes claiming one slot BLOCK the run.

ADR 0004. This module never decides a (unit, change) pair. It reads the
core decisions and groups the live ones by the slot they claim, which is
(unit, superseded part). A slot with exactly one live change is fine. A slot
with more than one is BLOCKED: the run names every competing change and
stops, instead of silently preferring one of them. There is no
latest-wins, no highest-revision-wins, no first-row-wins.

A decision is "live" when it still claims work: not_yet_reached,
incorporable, late, or blocked_material. out_of_effectivity claims nothing
for this unit, and incorporated is history, not a claim. That second point
matters for supersession: when an old change is incorporated and its
replacement is live, the replacement is the one live change, so there is no
conflict. Blocking that case would make supersession unusable.

A supersession table may declare that one change replaces another. It is
evidence, not a tie-break: if the superseded change is still live, the
slot is still BLOCKED (rule C02), because the declaration alone does not
prove the old change is done. Only an incorporated record proves that, and
incorporated decisions are not live.

use_as_is changes claim no slot (they supersede nothing) and never
conflict. Two changes for different superseded parts are different slots
and never conflict.

No clock, no network, no randomness. Pure functions of parsed models and
core decisions.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict

from effectivity.model import Change, Decision, Disposition, Status, Text

CONFLICT_VERSION = "1.0.0"

# Rule ids for the conflict layer. C01/C02 are in docs/applicability.md.
C_MULTIPLE = "C01"
C_SUPERSEDED = "C02"

BLOCKED_CONFLICT_MULTIPLE_LIVE_CHANGES = "BLOCKED_CONFLICT_MULTIPLE_LIVE_CHANGES"
BLOCKED_CONFLICT_SUPERSEDED_NOT_RESOLVED = "BLOCKED_CONFLICT_SUPERSEDED_NOT_RESOLVED"

LIVE_STATUSES = (
    Status.NOT_YET_REACHED,
    Status.INCORPORABLE,
    Status.LATE,
    Status.BLOCKED_MATERIAL,
)


class Supersession(BaseModel):
    """A declared replacement: ``change_id`` replaces ``supersedes_change_id``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    change_id: Text
    supersedes_change_id: Text


class CompetingChange(BaseModel):
    """One live change in a conflicted slot, with its core decision attached."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    change_id: str
    status: Status
    reason_code: str
    rule_ids: tuple[str, ...]


class Conflict(BaseModel):
    """One BLOCKED slot: more than one live change claims it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unit_id: str
    supersedes_part: str
    verdict: Literal["BLOCKED"]
    reason_code: str
    rule_ids: tuple[str, ...]
    competing: tuple[CompetingChange, ...]
    supersession_edges: tuple[Supersession, ...]


def validate_supersessions(
    edges: Sequence[Supersession], changes: Sequence[Change]
) -> None:
    """Reject supersession rows that contradict the changes table.

    Both ends must name known changes; a change cannot supersede itself;
    the same edge twice is an error; cycles are errors (a cycle would mean
    each change replaces the other); and both ends must claim the same
    superseded part, because supersession is about one slot. An edge
    involving a use_as_is change is an error: use_as_is claims no slot, so
    there is nothing to supersede.
    """

    by_id = {c.change_id: c for c in changes}
    seen: set[tuple[str, str]] = set()
    for edge in edges:
        if edge.change_id not in by_id:
            raise ValueError(f"supersession names unknown change {edge.change_id!r}")
        if edge.supersedes_change_id not in by_id:
            raise ValueError(
                f"supersession names unknown change {edge.supersedes_change_id!r}"
            )
        if edge.change_id == edge.supersedes_change_id:
            raise ValueError(f"change {edge.change_id!r} cannot supersede itself")
        key = (edge.change_id, edge.supersedes_change_id)
        if key in seen:
            raise ValueError(f"duplicate supersession edge for {key!r}")
        seen.add(key)
        newer, older = by_id[edge.change_id], by_id[edge.supersedes_change_id]
        if newer.disposition is Disposition.USE_AS_IS or older.disposition is Disposition.USE_AS_IS:
            raise ValueError(
                f"supersession {key!r} involves a use_as_is change, which claims no slot"
            )
        if newer.supersedes_part != older.supersedes_part:
            raise ValueError(
                f"supersession {key!r} joins changes for different parts "
                f"({newer.supersedes_part!r} vs {older.supersedes_part!r})"
            )
    graph = {c.change_id: set() for c in changes}
    for edge in edges:
        graph[edge.change_id].add(edge.supersedes_change_id)
    for start in graph:
        stack = list(graph[start])
        visited: set[str] = set()
        while stack:
            node = stack.pop()
            if node == start:
                raise ValueError(f"supersession cycle through {start!r}")
            if node in visited:
                continue
            visited.add(node)
            stack.extend(graph[node])


def find_conflicts(
    decisions: Sequence[Decision],
    changes: Sequence[Change],
    supersessions: Sequence[Supersession] = (),
) -> list[Conflict]:
    """Group live decisions by slot; every group of more than one is a Conflict."""

    validate_supersessions(supersessions, changes)
    by_id = {c.change_id: c for c in changes}
    groups: dict[tuple[str, str], list[Decision]] = {}
    for decision in decisions:
        if decision.status not in LIVE_STATUSES:
            continue
        change = by_id.get(decision.change_id)
        if change is None:
            raise ValueError(f"decision names unknown change {decision.change_id!r}")
        if change.disposition is Disposition.USE_AS_IS:
            continue
        key = (decision.unit_id, change.supersedes_part)
        groups.setdefault(key, []).append(decision)
    conflicts: list[Conflict] = []
    for (unit_id, part), members in sorted(groups.items()):
        if len(members) <= 1:
            continue
        competing_ids = sorted(d.change_id for d in members)
        competing = tuple(
            CompetingChange(
                change_id=d.change_id,
                status=d.status,
                reason_code=d.reason_code,
                rule_ids=d.rule_ids,
            )
            for d in sorted(members, key=lambda d: d.change_id)
        )
        edges = tuple(
            sorted(
                (
                    e
                    for e in supersessions
                    if e.change_id in competing_ids and e.supersedes_change_id in competing_ids
                ),
                key=lambda e: (e.change_id, e.supersedes_change_id),
            )
        )
        if edges:
            reason = BLOCKED_CONFLICT_SUPERSEDED_NOT_RESOLVED
            rule_ids = (C_SUPERSEDED,)
        else:
            reason = BLOCKED_CONFLICT_MULTIPLE_LIVE_CHANGES
            rule_ids = (C_MULTIPLE,)
        conflicts.append(
            Conflict(
                unit_id=unit_id,
                supersedes_part=part,
                verdict="BLOCKED",
                reason_code=reason,
                rule_ids=rule_ids,
                competing=competing,
                supersession_edges=edges,
            )
        )
    return conflicts
