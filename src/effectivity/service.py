"""Request handling for the web function (api/resolve.py). Stateless by construction.

Takes four CSV texts in a JSON body and returns the same report the CLI log
holds. It imports no filesystem, network, clock, or logging module, writes
nothing, and prints nothing: request bodies are never stored or logged. A test
enforces the import list.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from typing import Any

from effectivity.model import Change, Incorporation, MaterialState, Unit
from effectivity.report import build_report
from effectivity.tables import RowLimitError, parse_csv

# Caps. lib/limits.ts repeats MAX_BODY_BYTES; a test keeps the two equal.
MAX_BODY_BYTES = 262_144
MAX_ROWS = {"units": 1_000, "changes": 200, "material": 5_000, "incorporations": 5_000}
MAX_PAIRS = 5_000  # units x changes: keeps the response far below the platform limit

_TABLES: dict[str, type[Any]] = {
    "units": Unit,
    "changes": Change,
    "material": MaterialState,
    "incorporations": Incorporation,
}

StartResponse = Callable[[str, list[tuple[str, str]]], Any]


def _error(
    status: int, code: str, message: str, problems: list[dict[str, str]] | None = None
) -> tuple[int, dict[str, Any]]:
    return status, {"error": {"code": code, "message": message, "problems": problems or []}}


def handle(raw: bytes) -> tuple[int, dict[str, Any]]:
    """Return (HTTP status, JSON body) for a request body. Never raises for bad input."""
    if len(raw) > MAX_BODY_BYTES:
        return _error(413, "too_large", f"Request body is larger than {MAX_BODY_BYTES} bytes.")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return _error(400, "bad_json", "Request body must be UTF-8 JSON.")
    if not isinstance(payload, dict) or set(payload) != set(_TABLES):
        return _error(
            400, "bad_request", f"Body must be a JSON object with exactly the keys {sorted(_TABLES)}."
        )
    if not all(isinstance(payload[name], str) for name in _TABLES):
        return _error(400, "bad_request", "Each table must be a string of CSV text.")

    parsed: dict[str, list[Any]] = {}
    problems: list[dict[str, str]] = []
    for name, model in _TABLES.items():
        try:
            parsed[name] = parse_csv(payload[name], model, name, max_rows=MAX_ROWS[name])
        except RowLimitError as exc:
            return _error(413, "too_many_rows", str(exc), [{"table": name, "message": str(exc)}])
        except ValueError as exc:
            problems.append({"table": name, "message": str(exc)})
    if problems:
        return _error(422, "invalid_input", "Some tables could not be read.", problems)

    if len(parsed["units"]) * len(parsed["changes"]) > MAX_PAIRS:
        message = f"units x changes may not exceed {MAX_PAIRS} pairs."
        return _error(413, "too_many_pairs", message)
    try:
        report = build_report(
            parsed["units"], parsed["changes"], parsed["material"], parsed["incorporations"]
        )
    except ValueError as exc:  # duplicate ids, unknown references, incomparable hold points
        return _error(422, "invalid_input", "The tables contradict each other.",
                      [{"table": "tables", "message": str(exc)}])
    return 200, report


def wsgi_app(environ: dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
    """WSGI entry point: POST application/json only. No CORS: same-origin use."""
    headers = [("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff")]

    def respond(status: int, body: dict[str, Any], extra: list[tuple[str, str]] | None = None):
        data = json.dumps(body, separators=(",", ":")).encode("utf-8")
        reasons = {200: "OK", 400: "Bad Request", 405: "Method Not Allowed", 411: "Length Required",
                   413: "Content Too Large", 415: "Unsupported Media Type",
                   422: "Unprocessable Content", 500: "Internal Server Error"}
        start_response(
            f"{status} {reasons[status]}",
            [*headers, *(extra or []), ("Content-Type", "application/json; charset=utf-8"),
             ("Content-Length", str(len(data)))],
        )
        return [data]

    if environ.get("REQUEST_METHOD") != "POST":
        status, body = _error(405, "method_not_allowed", "Use POST with a JSON body.")
        return respond(status, body, [("Allow", "POST")])
    if environ.get("CONTENT_TYPE", "").split(";")[0].strip().lower() != "application/json":
        return respond(*_error(415, "unsupported_media_type", "Content-Type must be application/json."))
    try:
        length = int(environ.get("CONTENT_LENGTH") or "")
    except ValueError:
        return respond(*_error(411, "length_required", "Content-Length is required."))
    if length < 0:
        return respond(*_error(400, "bad_request", "Invalid Content-Length."))
    if length > MAX_BODY_BYTES:
        return respond(*_error(413, "too_large", f"Request body is larger than {MAX_BODY_BYTES} bytes."))
    try:
        status, body = handle(environ["wsgi.input"].read(length))
    except Exception:  # nothing from the request may reach a log, so nothing is recorded
        status, body = _error(500, "internal", "Unexpected error. Nothing was stored.")
    return respond(status, body)
