"""CSV text to validated models. Rules are in docs/state-machine.md ("Input rules")."""

from __future__ import annotations

import csv
import io
from typing import TypeVar

from pydantic import BaseModel, ValidationError

M = TypeVar("M", bound=BaseModel)


class RowLimitError(ValueError):
    """A table has more data rows than the caller allows."""


def parse_csv(text: str, model: type[M], source: str, max_rows: int | None = None) -> list[M]:
    """Parse CSV text. The header must be exactly the model's fields, each once, any order.

    A leading byte order mark is ignored. Any problem raises ValueError that
    names `source` and the line. If `max_rows` is given, more data rows than
    that raise RowLimitError.
    """
    expected = set(model.model_fields)
    rows: list[M] = []
    try:
        reader = csv.DictReader(io.StringIO(text.removeprefix("\ufeff"), newline=""))
        names = list(reader.fieldnames or [])
        duplicated = sorted({n for n in names if names.count(n) > 1})
        if duplicated:
            raise ValueError(f"{source}: duplicate column(s) {duplicated}")
        missing, unexpected = sorted(expected - set(names)), sorted(set(names) - expected)
        if missing or unexpected:
            raise ValueError(
                f"{source}: columns must be exactly {sorted(expected)}; "
                f"missing {missing}, unexpected {unexpected}"
            )
        for row in reader:
            where = f"{source}:{reader.line_num}"
            if max_rows is not None and len(rows) >= max_rows:
                raise RowLimitError(f"{where}: more than {max_rows} rows")
            if None in row or None in row.values():
                raise ValueError(f"{where}: wrong number of fields")
            try:
                rows.append(model.model_validate(row))
            except ValidationError as exc:
                problems = "; ".join(
                    f"{'.'.join(map(str, e['loc'])) or 'row'}: "
                    f"{e['msg'].removeprefix('Value error, ')}"
                    for e in exc.errors()
                )
                raise ValueError(f"{where}: {problems}") from exc
    except csv.Error as exc:
        raise ValueError(f"{source}: malformed CSV ({exc})") from exc
    return rows
