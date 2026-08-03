"""服务入口。

启动方式（在 backend/ 目录下）：
    python3 -m app.main
默认监听 127.0.0.1:18111，可用环境变量 APP_PORT 覆盖端口。
"""
import os
from http.server import ThreadingHTTPServer

from . import handlers  # noqa: F401  # 导入即注册全部路由
from .db import init_db
from .router import ApiRequestHandler

DEFAULT_PORT = 18111


def create_server(port=None):
    init_db()
    if port is None:
        port = int(os.environ.get("APP_PORT", DEFAULT_PORT))
    return ThreadingHTTPServer(("127.0.0.1", port), ApiRequestHandler)


def main():
    server = create_server()
    host, port = server.server_address[:2]
    print("field-briefing api listening on http://%s:%d" % (host, port), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
