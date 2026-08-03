"""SQLite 连接与 schema 初始化。

数据库路径默认 backend/data/app.db，可通过环境变量 APP_DB_PATH 覆盖（测试用）。
"""
import os
import sqlite3
from datetime import datetime, timezone

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_DB_PATH = os.path.join(_BACKEND_ROOT, "data", "app.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_code TEXT UNIQUE NOT NULL,
    project_name TEXT NOT NULL,
    owner_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_code TEXT NOT NULL,
    site_name TEXT NOT NULL,
    address_text TEXT DEFAULT '',
    region TEXT DEFAULT '',
    project_id INTEGER NOT NULL REFERENCES projects(id),
    UNIQUE(project_id, site_code)
);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES sites(id),
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    finding_status TEXT NOT NULL DEFAULT 'draft',
    reported_by TEXT NOT NULL,
    reported_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    storage_note TEXT DEFAULT '',
    linked_finding_id INTEGER NOT NULL REFERENCES findings(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id INTEGER NOT NULL REFERENCES findings(id),
    reviewer_name TEXT NOT NULL,
    conclusion TEXT NOT NULL,
    comment TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    actor TEXT DEFAULT '',
    detail TEXT DEFAULT '{}',
    project_id INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS site_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_name TEXT UNIQUE NOT NULL,
    default_region TEXT DEFAULT '',
    site_items TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def utc_now():
    """返回 ISO8601 UTC 时间字符串（毫秒精度，Z 后缀）。"""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def get_db_path():
    return os.environ.get("APP_DB_PATH") or _DEFAULT_DB_PATH


def get_conn():
    """打开一个新连接（每个请求一个连接，避免跨线程共享）。"""
    path = get_db_path()
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
