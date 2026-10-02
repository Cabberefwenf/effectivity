"""Pydantic v2 models and the ordered-key rule from ADR 0001."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Any, Literal, NamedTuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class KeyFormatError(ValueError):
    """A key or hold point token does not match the ADR 0001 grammar."""


class IncomparableKeysError(ValueError):
    """Two keys have different prefixes and have no defined order."""


class Key(NamedTuple):
    """Parsed key. Tuple comparison is the ADR 0001 ordering."""

    prefix: str
    number: int
    suffix: str


_KEY_RE = re.compile(r"([A-Z]{0,8})([0-9]+)([A-Z]?)", re.ASCII)


def parse_key(token: str) -> Key:
    """Parse a key per ADR 0001. Never strips or coerces; raises KeyFormatError."""
    match = _KEY_RE.fullmatch(token) if isinstance(token, str) else None
    if match is None:
        raise KeyFormatError(
            f"malformed key {token!r}: expected 0-8 upper-case letters, digits, "
            "then at most one upper-case letter (ADR 0001)"
        )
    prefix, number, suffix = match.groups()
    return Key(prefix, int(number), suffix)


def key_in_range(key: Key, lower: Key, upper: Key) -> bool:
    """Inclusive range test. A different prefix is simply not in the series."""
    if key.prefix != lower.prefix:
        return False
    return lower <= key <= upper


def compare_hold_points(left: Key, right: Key) -> int:
    """Return -1, 0, or 1. Raises IncomparableKeysError across prefixes."""
    if left.prefix != right.prefix:
        raise IncomparableKeysError(
            f"hold points with different prefixes have no order: "
            f"{left.prefix!r} vs {right.prefix!r}"
        )
    return (left > right) - (left < right)


class Disposition(StrEnum):
    USE_AS_IS = "use_as_is"
    REWORK = "rework"
    SCRAP = "scrap"
    RETROFIT = "retrofit"


class Status(StrEnum):
    """The six output states. No others exist."""

    OUT_OF_EFFECTIVITY = "out_of_effectivity"
    NOT_YET_REACHED = "not_yet_reached"
    INCORPORABLE = "incorporable"
    LATE = "late"
    BLOCKED_MATERIAL = "blocked_material"
    INCORPORATED = "incorporated"


HoldStatus = Literal["open", "closed"]
Quantity = Annotated[int, Field(ge=0)]

_FROZEN = ConfigDict(frozen=True, extra="forbid")


def _checked_key(value: str) -> str:
    parse_key(value)
    return value


class Unit(BaseModel):
    model_config = _FROZEN

    unit_id: str = Field(min_length=1)
    program: str
    effectivity_key: str
    hold_point: str
    hold_point_status: HoldStatus
    predecessor_hold_status: HoldStatus

    @field_validator("effectivity_key", "hold_point")
    @classmethod
    def _keys_well_formed(cls, value: str) -> str:
        return _checked_key(value)


class Change(BaseModel):
    model_config = _FROZEN

    change_id: str = Field(min_length=1)
    effectivity_from: str
    effectivity_to: str
    incorporation_hold_point: str
    disposition: Disposition
    supersedes_part: str
    replacement_part: str

    @field_validator("effectivity_from", "effectivity_to", "incorporation_hold_point")
    @classmethod
    def _keys_well_formed(cls, value: str) -> str:
        return _checked_key(value)

    @model_validator(mode="after")
    def _range_and_parts(self) -> Change:
        lower = parse_key(self.effectivity_from)
        upper = parse_key(self.effectivity_to)
        if lower.prefix != upper.prefix:
            raise ValueError("effectivity_from and effectivity_to must share a prefix")
        if lower > upper:
            raise ValueError("effectivity_from must not be greater than effectivity_to")
        if self.disposition is not Disposition.USE_AS_IS and not self.supersedes_part:
            raise ValueError("supersedes_part is required unless disposition is use_as_is")
        return self


class MaterialState(BaseModel):
    model_config = _FROZEN

    unit_id: str = Field(min_length=1)
    part: str
    qty_received_to_stores: Quantity
    qty_staged_at_work: Quantity
    qty_installed: Quantity


class Incorporation(BaseModel):
    model_config = _FROZEN

    unit_id: str = Field(min_length=1)
    change_id: str = Field(min_length=1)
    incorporated: bool

    @field_validator("incorporated", mode="before")
    @classmethod
    def _literal_bool(cls, value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if value == "true":
            return True
        if value == "false":
            return False
        raise ValueError("incorporated must be exactly 'true' or 'false'")


class Decision(BaseModel):
    model_config = _FROZEN

    unit_id: str
    change_id: str
    status: Status
    reason_code: str
    rule_ids: tuple[str, ...]
