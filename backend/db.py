"""Additive SQLite migrations and small transactional persistence boundary."""

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

AGENTS = [
    (
        "supervisor",
        "Supervisor",
        "Jamoa yetakchisi",
        "#dcb677",
        "Reja, vazifalarni taqsimlash va umumiy natija.",
    ),
    (
        "developer",
        "Developer",
        "Dasturchi",
        "#97b5ef",
        "Kod, arxitektura va muammolarni tuzatish.",
    ),
    (
        "qa",
        "QA Engineer",
        "Sifat nazorati",
        "#b8a0e3",
        "Testlar, talablar va regressiyalarni tekshirish.",
    ),
    (
        "devops",
        "DevOps",
        "Infratuzilma",
        "#9bc3b0",
        "CI, build va xavfsiz chiqarishga tayyorlash.",
    ),
    (
        "security",
        "Security",
        "Xavfsizlik",
        "#de9695",
        "Kod, maxfiy kalitlar va ruxsatlarni tekshirish.",
    ),
]


class Database:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version < 1:
                db.executescript("""
                CREATE TABLE agents (id TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL,
                    color TEXT NOT NULL, description TEXT NOT NULL, model TEXT NOT NULL DEFAULT '',
                    persona TEXT NOT NULL DEFAULT '', enabled INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at REAL NOT NULL);
                CREATE TABLE tasks (id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                    title TEXT NOT NULL, description TEXT NOT NULL, agent_id TEXT NOT NULL REFERENCES agents(id),
                    status TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL);
                CREATE TABLE messages (id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                    sender TEXT NOT NULL, text TEXT NOT NULL, created_at REAL NOT NULL);
                CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT REFERENCES projects(id),
                    kind TEXT NOT NULL, text TEXT NOT NULL, created_at REAL NOT NULL);
                CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE INDEX task_project ON tasks(project_id, created_at);
                CREATE INDEX message_project ON messages(project_id, created_at);
                PRAGMA user_version=1;
                """)
                db.executemany(
                    "INSERT INTO agents(id,name,role,color,description) VALUES (?,?,?,?,?)",
                    AGENTS,
                )
                db.execute(
                    "INSERT INTO projects VALUES (?,?,?)",
                    ("default", "Mening jamoam", time.time()),
                )
                self.event(
                    db, "project_created", "Shaxsiy ish maydoni yaratildi.", "default"
                )
            if version < 2:
                db.executescript("""
                CREATE TABLE jobs (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                    agent_id TEXT NOT NULL REFERENCES agents(id), source_kind TEXT NOT NULL,
                    reference_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
                    error_code TEXT, created_at REAL NOT NULL, updated_at REAL NOT NULL,
                    UNIQUE(source_kind, reference_id)
                );
                CREATE INDEX jobs_pending ON jobs(status,created_at);
                CREATE TABLE llm_usage (
                    id TEXT PRIMARY KEY, job_id TEXT NOT NULL REFERENCES jobs(id),
                    agent_id TEXT NOT NULL, model TEXT NOT NULL, status TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    cached_tokens INTEGER NOT NULL DEFAULT 0,
                    budget_tokens INTEGER NOT NULL, created_at REAL NOT NULL
                );
                CREATE INDEX usage_period ON llm_usage(created_at);
                PRAGMA user_version=2;
                """)
            if version < 3:
                db.executescript("""
                BEGIN IMMEDIATE;
                CREATE TABLE telegram_inbox (
                    id INTEGER PRIMARY KEY, bot_id TEXT NOT NULL, update_id INTEGER NOT NULL,
                    payload TEXT NOT NULL, status TEXT NOT NULL, created_at REAL NOT NULL,
                    UNIQUE(bot_id, update_id)
                );
                CREATE TABLE telegram_routes (
                    job_id TEXT PRIMARY KEY REFERENCES jobs(id),
                    chat_id INTEGER NOT NULL, message_id INTEGER NOT NULL,
                    peer_agent TEXT REFERENCES agents(id), first_reply TEXT REFERENCES messages(id)
                );
                CREATE TABLE telegram_outbox (
                    id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agents(id),
                    chat_id INTEGER NOT NULL, reply_to INTEGER NOT NULL,
                    text TEXT NOT NULL, status TEXT NOT NULL,
                    created_at REAL NOT NULL, telegram_message_id INTEGER
                );
                CREATE TABLE telegram_attachments (
                    id INTEGER PRIMARY KEY REFERENCES telegram_inbox(id),
                    project_id TEXT NOT NULL REFERENCES projects(id),
                    kind TEXT NOT NULL, name TEXT NOT NULL, mime TEXT NOT NULL,
                    file_id TEXT NOT NULL, uploader INTEGER NOT NULL, sha256 TEXT NOT NULL,
                    content BLOB NOT NULL, created_at REAL NOT NULL
                );
                CREATE TABLE voice_usage (created_at REAL NOT NULL);
                PRAGMA user_version=3;
                COMMIT;
                """)
            if version < 4:
                db.executescript("""
                BEGIN IMMEDIATE;
                ALTER TABLE llm_usage ADD COLUMN provider_id TEXT NOT NULL DEFAULT 'deepseek';
                PRAGMA user_version=4;
                COMMIT;
                """)
            if version < 5:
                db.executescript("""
                BEGIN IMMEDIATE;
                CREATE TABLE job_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL REFERENCES jobs(id),
                    step TEXT NOT NULL, created_at REAL NOT NULL
                );
                CREATE INDEX job_steps_job ON job_steps(job_id, id);
                PRAGMA user_version=5;
                COMMIT;
                """)
            if version < 6:
                db.executescript("""
                BEGIN IMMEDIATE;
                CREATE TABLE team_reviews (
                    task_id TEXT PRIMARY KEY REFERENCES tasks(id),
                    route TEXT NOT NULL DEFAULT '', clarification TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE team_replies (
                    job_id TEXT PRIMARY KEY REFERENCES jobs(id),
                    message_id TEXT NOT NULL REFERENCES messages(id)
                );
                PRAGMA user_version=6;
                COMMIT;
                """)
        path.chmod(0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def event(self, db, kind, text, project_id=None):
        db.execute(
            "INSERT INTO events(project_id,kind,text,created_at) VALUES (?,?,?,?)",
            (project_id, kind, text, time.time()),
        )

    def setting(self, key, default=None):
        with self.connect() as db:
            row = db.execute(
                "SELECT value FROM settings WHERE key=?", (key,)
            ).fetchone()
        return json.loads(row["value"]) if row else default

    def job_step(self, conn, job_id, step):
        conn.execute(
            "INSERT INTO job_steps(job_id,step,created_at) VALUES (?,?,?)",
            (job_id, step, time.time()),
        )

    def save_setting(self, key, value):
        with self.connect() as db:
            db.execute(
                "INSERT INTO settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value)),
            )

    def snapshot(self, project_id):
        with self.connect() as db:
            return {
                "agents": [
                    {
                        **dict(r),
                        "status": "paused"
                        if not r["enabled"]
                        else "working"
                        if db.execute(
                            "SELECT 1 FROM jobs WHERE agent_id=? AND status='running' LIMIT 1",
                            (r["id"],),
                        ).fetchone()
                        else "idle",
                    }
                    for r in db.execute("SELECT * FROM agents ORDER BY rowid")
                ],
                "projects": [
                    dict(r)
                    for r in db.execute("SELECT * FROM projects ORDER BY created_at")
                ],
                "tasks": [
                    dict(r)
                    for r in db.execute(
                        "SELECT t.*, CASE WHEN t.status='clarification' THEN "
                        "(SELECT m.text FROM team_replies r JOIN jobs j ON j.id=r.job_id "
                        "JOIN messages m ON m.id=r.message_id WHERE j.reference_id=t.id "
                        "AND j.project_id=t.project_id ORDER BY r.rowid DESC LIMIT 1) END AS question "
                        "FROM tasks t WHERE t.project_id=? ORDER BY t.created_at DESC LIMIT 200",
                        (project_id,),
                    )
                ],
                "messages": [
                    dict(r)
                    for r in db.execute(
                        "SELECT * FROM (SELECT * FROM messages WHERE project_id=? ORDER BY created_at DESC LIMIT 100) ORDER BY created_at",
                        (project_id,),
                    )
                ],
                "events": [
                    dict(r)
                    for r in db.execute(
                        "SELECT * FROM events WHERE project_id=? ORDER BY id DESC LIMIT 50",
                        (project_id,),
                    )
                ],
                "attachments": [
                    dict(r)
                    for r in db.execute(
                        "SELECT id,kind,name,length(content) AS size FROM telegram_attachments "
                        "WHERE project_id=? ORDER BY id DESC LIMIT 50",
                        (project_id,),
                    )
                ],
                "jobs": [
                    dict(r)
                    for r in db.execute(
                        "SELECT id,agent_id,source_kind,reference_id,status,error_code,created_at,updated_at "
                        "FROM jobs WHERE project_id=? ORDER BY created_at DESC LIMIT 100",
                        (project_id,),
                    )
                ],
                "job_steps": [
                    dict(r)
                    for r in db.execute(
                        "SELECT s.job_id,s.step,s.created_at FROM job_steps s JOIN jobs j ON j.id=s.job_id "
                        "WHERE j.project_id=? ORDER BY s.id DESC LIMIT 400",
                        (project_id,),
                    )
                ],
            }

    @staticmethod
    def id():
        return uuid.uuid4().hex
