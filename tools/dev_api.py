"""Local stand-in for Vercel's Python runtime: serves api/resolve.py on 127.0.0.1:8787.

Used by `npm run dev:api` and the Playwright suite. Next proxies /api/* here when
it is not running on Vercel. Request bodies are not logged.
"""

import sys
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

from resolve import app as _app  # noqa: E402


class _Counting:
    """Counts the bytes the function actually read, so only the unread rest is drained."""

    def __init__(self, stream):
        self.stream = stream
        self.read_bytes = 0

    def read(self, size=-1):
        data = self.stream.read(size)
        self.read_bytes += len(data)
        return data


def app(environ, start_response):
    """Run the real function, then drain any body it refused to read.

    The function rejects an oversized body from Content-Length without reading it, which is right
    on Vercel. A local proxy would otherwise hit a closed pipe while still sending it.
    """
    counting = _Counting(environ["wsgi.input"])
    environ["wsgi.input"] = counting
    result = list(_app(environ, start_response))  # run it fully before draining
    try:
        remaining = min(int(environ.get("CONTENT_LENGTH") or 0), 16 * 1024 * 1024)
    except ValueError:
        remaining = 0
    remaining -= counting.read_bytes
    while remaining > 0:
        chunk = counting.stream.read(min(remaining, 65536))
        if not chunk:
            break
        remaining -= len(chunk)
    return result


class QuietHandler(WSGIRequestHandler):
    def log_message(self, format, *args):  # noqa: A002
        return None


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    with make_server("127.0.0.1", port, app, handler_class=QuietHandler) as server:
        print(f"effectivity api on http://127.0.0.1:{port}/api/resolve", flush=True)
        server.serve_forever()
