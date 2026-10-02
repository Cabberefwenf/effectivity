"""Vercel Python function: POST /api/resolve.

All behavior lives in effectivity.service so it is testable without HTTP.
Stateless: nothing is stored and request bodies are never logged.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from effectivity.service import wsgi_app  # noqa: E402


def app(environ, start_response):
    return wsgi_app(environ, start_response)
