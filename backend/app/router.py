"""路由分发与 HTTP 层。

- 支持路径参数，如 /api/v1/projects/{project_id}
- 静态路由优先于带参数路由（如 /api/v1/projects/from_template）
- 统一错误处理：ApiError -> 统一错误格式；JSON 解析失败 -> 400 INVALID_JSON；
  未知路由 -> 404 NOT_FOUND；未捕获异常 -> 500 INTERNAL_ERROR
- 所有响应带 CORS 头，处理 OPTIONS 预检
"""
import json
import re
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from .db import get_conn
from .errors import ApiError

ROUTES = []


class Route:
    def __init__(self, method, pattern, handler):
        self.method = method
        self.pattern = pattern
        self.handler = handler
        regex = re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", r"(?P<\1>[^/]+)", pattern)
        self.regex = re.compile("^%s$" % regex)
        self.is_static = "{" not in pattern

    def match(self, path):
        matched = self.regex.match(path)
        return matched.groupdict() if matched else None


def route(method, pattern):
    """路由注册装饰器，供 handlers 模块使用。"""

    def decorator(func):
        ROUTES.append(Route(method, pattern, func))
        return func

    return decorator


class Request:
    """一次请求的上下文。"""

    def __init__(self, method, path, query, body, conn, path_params):
        self.method = method
        self.path = path
        self.query = query          # dict: str -> str（取第一个值）
        self.body = body            # 解析后的 JSON（通常为 dict），无 body 时为 None
        self.conn = conn            # 本请求独占的 SQLite 连接
        self.path_params = path_params  # 路径参数（字符串）


def _parse_body(body_bytes):
    if not body_bytes:
        return None
    try:
        return json.loads(body_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ApiError(400, "INVALID_JSON", "request body is not valid JSON")


def dispatch(method, raw_path, body_bytes):
    """按方法与路径分发到对应 handler，返回 (status, payload)。"""
    parsed = urlparse(raw_path)
    path = parsed.path
    if len(path) > 1:
        path = path.rstrip("/")
    query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
    body = _parse_body(body_bytes)

    # 静态路由优先
    candidates = []
    for item in sorted(ROUTES, key=lambda r: not r.is_static):
        params = item.match(path)
        if params is not None:
            candidates.append((item, params))

    for item, params in candidates:
        if item.method != method:
            continue
        conn = get_conn()
        try:
            req = Request(method, path, query, body, conn, params)
            result = item.handler(req)
        finally:
            conn.close()
        if isinstance(result, tuple):
            return result
        return 200, result

    raise ApiError(404, "NOT_FOUND", "route not found: %s %s" % (method, path))


class ApiRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):  # noqa: A002 - 保持基类签名
        pass

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PATCH(self):
        self._handle("PATCH")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers(preflight=True)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_cors_headers(self, preflight=False):
        self.send_header("Access-Control-Allow-Origin", "*")
        if preflight:
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _read_body(self):
        length = self.headers.get("Content-Length")
        if not length:
            return b""
        try:
            size = int(length)
        except ValueError:
            return b""
        return self.rfile.read(size) if size > 0 else b""

    def _handle(self, method):
        body_bytes = self._read_body()
        try:
            status, payload = dispatch(method, self.path, body_bytes)
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        except ApiError as exc:
            status = exc.status
            body = json.dumps(exc.to_body(), ensure_ascii=False).encode("utf-8")
        except Exception:
            status = 500
            body = json.dumps(
                {
                    "error_code": "INTERNAL_ERROR",
                    "message": "internal server error",
                    "details": {},
                },
                ensure_ascii=False,
            ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
