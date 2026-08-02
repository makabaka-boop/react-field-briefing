"""HTTP server built on the standard library (zero third-party deps).

Responsibilities kept here (and nowhere else):
  * parse request path/query/body
  * add permissive CORS headers for the Vite dev server
  * translate ApiError instances into the fixed error envelope
  * JSON-encode responses
Business logic lives in Handlers; routing in Router.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .db import Database
from .errors import ApiError
from .handlers import Handlers
from .router import Router

API_PREFIX = "/api/v1"


def build_router(db_path=None):
    db = Database(db_path) if db_path else Database()
    return Router(Handlers(db)), db


class RequestHandler(BaseHTTPRequestHandler):
    router = None  # injected by make_server

    def log_message(self, *args):  # keep test output quiet
        pass

    # --- CORS --------------------------------------------------------------
    def _set_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods",
                         "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors()
        self.end_headers()

    def _write_json(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self._set_cors()
        self.end_headers()
        self.wfile.write(data)

    def _error(self, status, error_code, message, details=None):
        self._write_json(status, {
            "error_code": error_code,
            "message": message,
            "details": details or {},
        })

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ApiError(
                "Request body is not valid JSON.",
                error_code="invalid_json", status_code=400,
            )

    def _handle(self, method):
        parsed = urlparse(self.path)
        path = parsed.path
        if not path.startswith(API_PREFIX):
            self._error(404, "not_found", "Unknown path prefix.",
                        {"path": path})
            return
        route_path = path[len(API_PREFIX):] or "/"
        if route_path.endswith("/") and route_path != "/":
            route_path = route_path.rstrip("/")
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        try:
            body = self._read_body() if method in ("POST", "PUT") else None
            status, payload = self.router.dispatch(
                method, route_path, query, body
            )
            self._write_json(status, payload)
        except ApiError as exc:
            self._error(exc.status_code, exc.error_code, exc.message,
                        exc.details)
        except Exception as exc:  # noqa: BLE001 - last-resort guard
            self._error(500, "internal_error", "Unexpected server error.",
                        {"detail": str(exc)})

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")


def make_server(host="127.0.0.1", port=18111, db_path=None):
    router, db = build_router(db_path)
    handler_cls = type("BoundHandler", (RequestHandler,), {"router": router})
    server = ThreadingHTTPServer((host, port), handler_cls)
    server.db = db
    return server


def main():
    server = make_server()
    host, port = server.server_address
    print(f"Field briefing API listening on http://{host}:{port}{API_PREFIX}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.db.close()
        server.server_close()


if __name__ == "__main__":
    main()
