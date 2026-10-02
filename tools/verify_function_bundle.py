"""Simulate what Vercel ships for api/resolve.py, then run it against the golden report.

Copies only what vercel.json bundles (api/, src/, requirements.txt), installs requirements.txt
into a clean virtualenv WITHOUT installing this package, and sends one real WSGI request. This
proves the function imports `effectivity` from src/ and that requirements.txt alone is enough.
It cannot prove anything about Vercel's own runtime; that needs a deploy.

    python tools/verify_function_bundle.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden" / "examples-report.json"

DRIVER = """
import io, json, sys
sys.path.insert(0, "api")
from resolve import app

body = json.dumps(json.load(sys.stdin)).encode()
environ = {
    "REQUEST_METHOD": "POST",
    "CONTENT_TYPE": "application/json",
    "CONTENT_LENGTH": str(len(body)),
    "wsgi.input": io.BytesIO(body),
}
seen = {}
def start_response(status, headers, exc=None):
    seen["status"] = status
    seen["headers"] = dict(headers)
out = b"".join(app(environ, start_response))
print(json.dumps({"status": seen["status"], "headers": seen["headers"], "body": json.loads(out)}))
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        bundle = Path(tmp) / "bundle"
        shutil.copytree(ROOT / "api", bundle / "api", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(ROOT / "src", bundle / "src", ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
        shutil.copy(ROOT / "requirements.txt", bundle / "requirements.txt")

        venv = Path(tmp) / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        python = venv / "bin" / "python"
        subprocess.run(
            [str(python), "-m", "pip", "install", "--quiet", "-r", str(bundle / "requirements.txt")],
            check=True,
        )

        payload = json.dumps(
            {name: (ROOT / "examples" / f"{name}.csv").read_text() for name in
             ("units", "changes", "material", "incorporations")}
        )
        done = subprocess.run(
            [str(python), "-c", DRIVER],
            input=payload, text=True, capture_output=True, cwd=bundle, check=False,
        )
        if done.returncode != 0:
            print(done.stderr, file=sys.stderr)
            return 1
        result = json.loads(done.stdout)

    golden = json.loads(GOLDEN.read_text())
    problems = []
    if not result["status"].startswith("200"):
        problems.append(f"status {result['status']}")
    if result["body"] != golden:
        problems.append("response differs from tests/golden/examples-report.json")
    if result["headers"].get("Cache-Control") != "no-store":
        problems.append("Cache-Control is not no-store")
    if problems:
        print("bundle check FAILED: " + "; ".join(problems), file=sys.stderr)
        return 1
    print(f"bundle check ok: {len(result['body']['decisions'])} decisions, identical to golden, "
          f"installed only: {(ROOT / 'requirements.txt').read_text().strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
