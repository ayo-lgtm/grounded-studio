"""Local review server. Binds to localhost and serves one output folder."""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .chat import answer

ROOT = Path("out/demo")
HOST = "127.0.0.1"
PORT = 8765


def main() -> None:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT.resolve()
    if not (root / "index.html").exists():
        raise SystemExit(f"No review at {root}. Run: python -m grounded.demo {root}")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            path = unquote(urlparse(self.path).path)
            if path in {"", "/"}:
                path = "/index.html"
            target = (root / path.lstrip("/")).resolve()
            if root not in target.parents and target != root:
                self.send_error(404)
                return
            if not target.is_file():
                self.send_error(404)
                return
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("content-type", _type(target))
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/api/chat":
                self.send_error(404)
                return
            length = int(self.headers.get("content-length") or 0)
            if length > 20_000:
                self.send_error(413)
                return
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
                script = json.loads((root / "weekly" / "script.json").read_text(encoding="utf-8"))
                result = answer(script, str(payload.get("question") or ""))
            except (json.JSONDecodeError, OSError):
                self.send_error(400)
                return
            citation = ""
            if result.get("citations"):
                cite = result["citations"][0]
                if cite.get("kind") == "workbook":
                    citation = f"{cite.get('sheet')}!{cite.get('addr')}"
            body = json.dumps(
                {"refused": result["refused"], "text": result["text"], "citation": citation}
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:
            print(f"{self.address_string()} {fmt % args}")

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Grounded Studio  http://{HOST}:{PORT}")
    server.serve_forever()


def _type(path: Path) -> str:
    return {
        ".html": "text/html; charset=utf-8",
        ".mp4": "video/mp4",
        ".vtt": "text/vtt; charset=utf-8",
        ".json": "application/json",
        ".md": "text/plain; charset=utf-8",
    }.get(path.suffix.lower(), "application/octet-stream")


if __name__ == "__main__":
    main()