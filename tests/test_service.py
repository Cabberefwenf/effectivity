"""The web function returns exactly what the CLI returns, and enforces its caps."""

from __future__ import annotations

import ast
import io
import json
from pathlib import Path
from typing import Any

import pytest

from effectivity import service
from effectivity.cli import format_table, main
from effectivity.model import Decision

ROOT = Path(__file__).resolve().parent.parent
EX = ROOT / "examples"
GOLDEN = json.loads((ROOT / "tests" / "golden" / "examples-report.json").read_text())
NAMES = ["units", "changes", "material", "incorporations"]
HEADERS = {
    "units": "unit_id,program,effectivity_key,hold_point,hold_point_status,predecessor_hold_status",
    "changes": "change_id,effectivity_from,effectivity_to,incorporation_hold_point,"
    "disposition,supersedes_part,replacement_part",
    "material": "unit_id,part,qty_received_to_stores,qty_staged_at_work,qty_installed",
    "incorporations": "unit_id,change_id,incorporated",
}


def example_tables() -> dict[str, str]:
    return {n: (EX / f"{n}.csv").read_text() for n in NAMES}


def post(body: Any, *, content_type: str = "application/json", method: str = "POST",
         length: int | str | None = None) -> tuple[str, dict[str, str], Any]:
    raw = body if isinstance(body, bytes) else json.dumps(body).encode()
    environ = {
        "REQUEST_METHOD": method,
        "CONTENT_TYPE": content_type,
        "wsgi.input": io.BytesIO(raw),
    }
    if length is None:
        environ["CONTENT_LENGTH"] = str(len(raw))
    elif length != "":
        environ["CONTENT_LENGTH"] = str(length)
    seen: dict[str, Any] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        seen["status"], seen["headers"] = status, dict(headers)

    chunks = service.wsgi_app(environ, start_response)
    return seen["status"], seen["headers"], json.loads(b"".join(chunks))


# --- Golden: API == CLI on the examples ----------------------------------------

def test_function_returns_the_golden_report_for_the_examples() -> None:
    status, headers, body = post(example_tables())
    assert status == "200 OK"
    assert body == GOLDEN
    assert headers["Content-Type"].startswith("application/json")
    assert headers["Cache-Control"] == "no-store"
    assert int(headers["Content-Length"]) > 0


def test_function_equals_the_cli_log_line_and_the_cli_table(tmp_path: Path,
                                                            capsys: pytest.CaptureFixture[str]) -> None:
    log = tmp_path / "run.jsonl"
    argv = [x for n in NAMES for x in (f"--{n}", str(EX / f"{n}.csv"))]
    assert main([*argv, "--log", str(log)]) == 0
    printed = capsys.readouterr().out.rstrip("\n")
    record = json.loads(log.read_text())
    _, _, body = post(example_tables())
    for key in ("rule_version", "input_hash", "counts", "decisions"):
        assert body[key] == record[key], key
    # the printed table is a pure rendering of the function's decisions
    assert format_table([Decision.model_validate(d) for d in body["decisions"]]) == printed
    assert printed == (ROOT / "tests" / "golden" / "examples-table.txt").read_text().rstrip("\n")


def test_function_is_deterministic_and_ignores_csv_formatting() -> None:
    tables = example_tables()
    reformatted = {n: "\ufeff" + t.replace("\n", "\r\n") for n, t in tables.items()}
    assert post(tables)[2] == post(reformatted)[2] == post(tables)[2]


# --- Errors the user can fix ---------------------------------------------------------

def test_every_bad_table_is_reported_at_once() -> None:
    tables = example_tables()
    tables["units"] = tables["units"].replace("0121", "12-3", 1)
    tables["material"] = tables["material"].replace("8,0,0", "-8,0,0", 1)
    status, _, body = post(tables)
    assert status.startswith("422")
    assert body["error"]["code"] == "invalid_input"
    by_table = {p["table"]: p["message"] for p in body["error"]["problems"]}
    assert set(by_table) == {"units", "material"}
    assert by_table["units"].startswith("units:2:") and "malformed key" in by_table["units"]
    assert by_table["material"].startswith("material:2:")


def test_cross_table_contradictions_are_reported() -> None:
    tables = example_tables()
    tables["incorporations"] += "U-NOPE,C-1001,true\n"
    status, _, body = post(tables)
    assert status.startswith("422")
    assert body["error"]["problems"][0]["table"] == "tables"
    assert "unknown unit" in body["error"]["problems"][0]["message"]


@pytest.mark.parametrize(
    "payload,code",
    [
        (b"not json", "bad_json"),
        (b"\xff\xfe", "bad_json"),
        (b"[]", "bad_request"),
        (b'{"units": ""}', "bad_request"),
        (json.dumps({**{n: "" for n in NAMES}, "extra": ""}).encode(), "bad_request"),
        (json.dumps({**{n: "" for n in NAMES}, "units": 5}).encode(), "bad_request"),
        (json.dumps({n: None for n in NAMES}).encode(), "bad_request"),
    ],
)
def test_malformed_bodies_are_400(payload: bytes, code: str) -> None:
    status, _, body = post(payload)
    assert status.startswith("400") and body["error"]["code"] == code


def test_empty_tables_are_reported_as_missing_columns_not_crashes() -> None:
    status, _, body = post({n: "" for n in NAMES})
    assert status.startswith("422")
    assert {p["table"] for p in body["error"]["problems"]} == set(NAMES)


# --- Caps -----------------------------------------------------------------------------

def table(name: str, rows: list[str]) -> str:
    return "\n".join([HEADERS[name], *rows]) + "\n"


def test_body_larger_than_the_cap_is_413_without_being_read() -> None:
    big = b"x" * (service.MAX_BODY_BYTES + 1)
    status, _, body = post(big)
    assert status.startswith("413") and body["error"]["code"] == "too_large"
    # a lying Content-Length is refused before reading, a short one cannot extend the read
    assert post(b"{}", length=service.MAX_BODY_BYTES + 1)[0].startswith("413")


def test_row_caps_per_table() -> None:
    base = {n: table(n, []) for n in NAMES}
    rows = [f"U{n},P,{n:04d},HP010,open,closed" for n in range(service.MAX_ROWS["units"] + 1)]
    status, _, body = post({**base, "units": table("units", rows)})
    assert status.startswith("413") and body["error"]["code"] == "too_many_rows"
    assert "units" in body["error"]["problems"][0]["table"]
    ok_rows = rows[:-1]
    assert post({**base, "units": table("units", ok_rows)})[0] == "200 OK"


def test_pair_cap() -> None:
    units = [f"U{n},P,{n:04d},HP010,open,closed" for n in range(service.MAX_ROWS["units"])]
    changes = [f"C{n},0000,9999,HP020,use_as_is,,"for n in range(service.MAX_PAIRS // len(units) + 1)]
    status, _, body = post({"units": table("units", units), "changes": table("changes", changes),
                            "material": table("material", []), "incorporations": table("incorporations", [])})
    assert status.startswith("413") and body["error"]["code"] == "too_many_pairs"


def test_largest_allowed_run_finishes_and_stays_under_the_response_limit() -> None:
    units = [f"U{n:04d},P,{n:04d},HP010,open,closed" for n in range(1000)]
    changes = [f"C{n},0000,9999,HP020,rework,PN-{n},PN-N{n}" for n in range(5)]
    status, headers, body = post({"units": table("units", units), "changes": table("changes", changes),
                                  "material": table("material", []), "incorporations": table("incorporations", [])})
    assert status == "200 OK" and len(body["decisions"]) == 5000
    assert int(headers["Content-Length"]) < 1_500_000   # platform limit is 4.5 MB


# --- HTTP shape --------------------------------------------------------------------------

def test_only_post_json_is_accepted() -> None:
    status, headers, body = post(b"", method="GET")
    assert status.startswith("405") and headers["Allow"] == "POST"
    assert post(example_tables(), content_type="text/plain")[0].startswith("415")
    assert post(example_tables(), content_type="application/json; charset=utf-8")[0] == "200 OK"
    assert post(b"{}", length="")[0].startswith("411")
    assert post(b"{}", length="abc")[0].startswith("411")
    assert post(b"{}", length="-5")[0].startswith("400")


def test_no_cors_headers_are_ever_sent() -> None:
    for response in (post(example_tables()), post(b"x", method="GET"), post(b"nope")):
        assert not any(k.lower().startswith("access-control") for k in response[1])


def test_unexpected_failure_is_a_generic_500_that_echoes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_raw: bytes) -> None:
        raise RuntimeError("SECRET-CSV-CONTENT")

    monkeypatch.setattr(service, "handle", boom)
    status, _, body = post(example_tables())
    assert status.startswith("500")
    assert "SECRET" not in json.dumps(body) and body["error"]["code"] == "internal"


def test_nothing_is_printed_or_logged_while_serving(capsys: pytest.CaptureFixture[str],
                                                    caplog: pytest.LogCaptureFixture) -> None:
    tables = example_tables()
    post(tables)
    tables["units"] = tables["units"].replace("0121", "12-3", 1)
    post(tables)
    out = capsys.readouterr()
    assert out.out == "" and out.err == "" and caplog.records == []


# --- Statelessness is enforced by the import list --------------------------------------------

ALLOWED_SERVICE_IMPORTS = {
    "__future__", "json", "collections.abc", "typing", "effectivity.model",
    "effectivity.report", "effectivity.tables",
}
ALLOWED_REPORT_IMPORTS = {"__future__", "collections.abc", "typing", "effectivity.log",
                          "effectivity.model", "effectivity.resolve"}
ALLOWED_TABLES_IMPORTS = {"__future__", "csv", "io", "typing", "pydantic"}


@pytest.mark.parametrize(
    "module,allowed",
    [("service.py", ALLOWED_SERVICE_IMPORTS), ("report.py", ALLOWED_REPORT_IMPORTS),
     ("tables.py", ALLOWED_TABLES_IMPORTS)],
)
def test_request_path_modules_import_no_filesystem_network_clock_or_logging(module: str, allowed: set[str]) -> None:
    tree = ast.parse((ROOT / "src" / "effectivity" / module).read_text())
    imported = {n.module or "" if isinstance(n, ast.ImportFrom) else a.name
                for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                for a in (n.names if isinstance(n, ast.Import) else [n])}
    assert imported <= allowed, imported - allowed
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"open", "print", "exec", "eval", "__import__"}


def test_the_vercel_entry_point_is_a_thin_wrapper() -> None:
    source = (ROOT / "api" / "resolve.py").read_text()
    tree = ast.parse(source)
    assert any(isinstance(n, ast.FunctionDef) and n.name == "app" for n in tree.body)
    imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imports |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert imports == {"sys", "pathlib", "effectivity.service"}
    for banned in ("open(", "print(", "logging", "os.environ"):
        assert banned not in source


def test_function_imports_the_package_from_src_without_it_being_installed() -> None:
    import subprocess
    import sys

    code = (
        "import sys, json; sys.path = [p for p in sys.path if not p.rstrip('/').endswith('/effectivity/src')]\n"
        "assert 'effectivity' not in sys.modules\n"
        "import importlib.util as u\n"
        f"spec = u.spec_from_file_location('resolve_fn', {str(ROOT / 'api' / 'resolve.py')!r})\n"
        "m = u.module_from_spec(spec); spec.loader.exec_module(m)\n"
        "import io\n"
        "body = json.dumps({'units':'','changes':'','material':'','incorporations':''}).encode()\n"
        "env = {'REQUEST_METHOD':'POST','CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(body)),'wsgi.input':io.BytesIO(body)}\n"
        "out = []\n"
        "m.app(env, lambda s, h: out.append(s))\n"
        "print(out[0])\n"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd="/", capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "422 Unprocessable Content"


def test_body_cap_matches_the_frontend_constant() -> None:
    import re

    match = re.search(r"MAX_BODY_BYTES\s*=\s*([0-9_]+)", (ROOT / "lib" / "limits.ts").read_text())
    assert match and int(match.group(1).replace("_", "")) == service.MAX_BODY_BYTES
