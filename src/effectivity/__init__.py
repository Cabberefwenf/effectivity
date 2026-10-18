"""Deterministic as-built effectivity resolver."""

from effectivity.applicability import ApplicabilityRule
from effectivity.conflicts import Conflict, Supersession, find_conflicts
from effectivity.model import (
    Change,
    Decision,
    Disposition,
    Incorporation,
    MaterialState,
    Status,
    Unit,
)
from effectivity.pipeline import run_extended
from effectivity.resolve import RULE_VERSION, decide_pair, resolve
from effectivity.trace import trace_all, trace_pair
from effectivity.verify import verify_log

__all__ = [
    "RULE_VERSION",
    "ApplicabilityRule",
    "Change",
    "Conflict",
    "Decision",
    "Disposition",
    "Incorporation",
    "MaterialState",
    "Status",
    "Supersession",
    "Unit",
    "decide_pair",
    "find_conflicts",
    "resolve",
    "run_extended",
    "trace_all",
    "trace_pair",
    "verify_log",
]
