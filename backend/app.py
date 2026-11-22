"""Pixel Team API. No imports, runtime state or tooling from Ant Colony."""

import os
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote, urlsplit

from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
from dotenv import load_dotenv
import httpx
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .db import Database
from .llm_runtime import TextRuntime
from .project_source import project_brief
from .providers import PROVIDER_ID, validate_endpoint
from .security import AuthStore, OwnerAccessMiddleware, SecuritySettings, auth_router
from .telegram import TelegramBridge
from .team import TASK_KINDS_SQL

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)


class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class ProjectMemory(BaseModel):
    text: str = Field(default="", max_length=800)


class MessageInput(BaseModel):
    project_id: str
    text: str = Field(min_length=1, max_length=6000)


class TaskInput(BaseModel):
    project_id: str
    title: str = Field(min_length=1, max_length=180)
    description: str = Field(default="", max_length=6000)
    agent_id: str = "developer"
    team_review: bool = False


class ClarificationInput(BaseModel):
    text: str = Field(min_length=1, max_length=1500)


class AgentInput(BaseModel):
    model: str = Field(default="", max_length=160)
    persona: str = Field(default="", max_length=2000)
    enabled: bool = True
    monthly_call_limit: int | None = Field(default=None, ge=1, le=10000)
    provider_id: str | None = Field(default=None, max_length=32)


class ProviderInput(BaseModel):
    api_key: str = Field(default="", max_length=2000)
    model: str = Field(min_length=1, max_length=160)
    name: str = Field(default="", max_length=60)
    base_url: str = Field(default="", max_length=250)


class LimitsInput(BaseModel):
    paid_calls_enabled: bool = True
    monthly_call_limit: int = Field(default=100, ge=1, le=10000)
    monthly_token_limit: int = Field(default=250000, ge=1000, le=10000000)
    max_output_tokens: int = Field(default=512, ge=64, le=4096)


def create_app(
    data_dir=None, password_hash=None, llm_transport=None, telegram_transport=None
):
    data = Path(data_dir or os.getenv("PIXEL_DATA_DIR", str(ROOT / "data")))
    db = Database(data / "team.sqlite3")
    auth = AuthStore(data / "auth.sqlite3")
    settings = SecuritySettings(
        password_hash=password_hash
        if password_hash is not None
        else os.getenv("PIXEL_ADMIN_PASSWORD_HASH", ""),
        public_url=os.getenv("APP_PUBLIC_URL", "http://127.0.0.1:8090"),
        production=os.getenv("APP_ENV", "development") == "production",
    )

    @asynccontextmanager
    async def lifespan(app):
        await runtime.start()
        try:
            await telegram.start()
            yield
        finally:
            await telegram.stop()
            await runtime.stop()

    app = FastAPI(title="Pixel Team", version="0.5.0", lifespan=lifespan)
    app.state.db = db
    app.include_router(auth_router(settings, auth, ROOT / "web/dist"))
    app.add_middleware(OwnerAccessMiddleware, settings=settings, store=auth)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "127.0.0.1",
            "localhost",
            urlsplit(settings.public_url).hostname or "localhost",
        ],
    )

    def project_exists(project_id):
        with db.connect() as conn:
            if not conn.execute(
                "SELECT 1 FROM projects WHERE id=?", (project_id,)
            ).fetchone():
                raise HTTPException(404, "Loyiha topilmadi")

    # Initialize once before concurrent requests can save provider settings.
    key_file = data / "provider.key"
    if not key_file.exists():
        fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(Fernet.generate_key())
    provider_cipher = Fernet(key_file.read_bytes())
    runtime = TextRuntime(
        db,
        provider_cipher,
        llm_transport,
        deployment={
            "environment": os.getenv("APP_ENV", "development"),
            "public_url": settings.public_url,
            "server_host": os.getenv("PIXEL_SERVER_HOST", ""),
            "server_ip": os.getenv("PIXEL_SERVER_IP", ""),
            "briefs_dir": os.getenv("PIXEL_PROJECT_BRIEFS_DIR", ""),
        },
    )
    app.state.runtime = runtime
    telegram = TelegramBridge(db, runtime, telegram_transport)
    app.state.telegram = telegram
    app.router.routes[:] = [
        route
        for route in app.router.routes
        if getattr(route, "path", None) != "/health/ready"
    ]

    @app.get("/health/ready")
    def ready():
        try:
            with db.connect() as conn:
                conn.execute("SELECT 1 FROM jobs LIMIT 1")
            with auth.connect() as conn:
                conn.execute("SELECT 1 FROM auth_sessions LIMIT 1")
            healthy = (
                bool(settings.password_hash)
                and runtime.worker is not None
                and not runtime.worker.done()
                and all(not task.done() for task in telegram.tasks)
            )
        except Exception:
            healthy = False
        return JSONResponse(
            {"status": "ready" if healthy else "not_ready"}, 200 if healthy else 503
        )

    @app.get("/api/studio")
    def studio(project_id: str = "default"):
        project_exists(project_id)
        snapshot = db.snapshot(project_id)
        agent_limits = db.setting("agent_call_limits", {})
        for agent in snapshot["agents"]:
            agent["monthly_call_limit"] = agent_limits.get(agent["id"])
            agent["provider_id"] = runtime.provider_for(agent["id"])
        provider = db.setting("provider", {})
        return {
            **snapshot,
            "integrations": {
                "provider": bool(provider.get("encrypted_key")),
                "model": provider.get("model", ""),
                "telegram": telegram.connected,
                "telegram_status": telegram.state(),
                "github": False,
                "executor": runtime.enabled(),
            },
            "usage": runtime.usage(),
            "providers": runtime.providers.public(),
            "project_memory": db.setting(f"memory:{project_id}", ""),
            "project_brief_connected": bool(
                project_brief(runtime.deployment.get("briefs_dir"), project_id)
            ),
            "limits": runtime.limits(),
            "runtime": runtime.deployment_info(),
            "version": "0.5.0",
        }

    @app.post("/api/projects", status_code=201)
    def create_project(payload: ProjectInput):
        name = payload.name.strip()
        if not name:
            raise HTTPException(422, "Loyiha nomini yozing")
        project_id = db.id()
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO projects VALUES (?,?,?)", (project_id, name, time.time())
            )
            db.event(
                conn, "project_created", f"“{name}” loyihasi yaratildi.", project_id
            )
        return {"id": project_id, "name": name}

    @app.put("/api/projects/{project_id}/memory")
    def save_memory(project_id: str, payload: ProjectMemory):
        project_exists(project_id)
        db.save_setting(f"memory:{project_id}", payload.text.strip())
        return {"saved": True}

    @app.get("/api/projects/{project_id}/attachments/{attachment_id}")
    def download_attachment(project_id: str, attachment_id: int):
        with db.connect() as conn:
            row = conn.execute(
                "SELECT content,name FROM telegram_attachments WHERE project_id=? AND id=?",
                (project_id, attachment_id),
            ).fetchone()
        if row is None:
            raise HTTPException(404, "Fayl topilmadi")
        return Response(
            row["content"],
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(row['name'], safe='')}",
            },
        )

    @app.post("/api/tasks/{task_id}/complete")
    def complete_task(task_id: str):
        with db.connect() as conn:
            task = conn.execute(
                "SELECT project_id FROM tasks WHERE id=? AND status='review'",
                (task_id,),
            ).fetchone()
            if task is None:
                raise HTTPException(
                    409, "Faqat ko‘rib chiqilayotgan vazifani yakunlash mumkin"
                )
            changed = conn.execute(
                "UPDATE tasks SET status='done',updated_at=? WHERE id=? AND status='review'",
                (time.time(), task_id),
            ).rowcount
            if not changed:
                raise HTTPException(409, "Vazifa holati o‘zgardi")
            db.event(
                conn, "task_approved", "Egasi vazifani yakunladi.", task["project_id"]
            )
        return {"status": "done"}

    @app.post("/api/messages", status_code=201)
    def message(payload: MessageInput):
        project_exists(payload.project_id)
        text = payload.text.strip()
        if not text:
            raise HTTPException(422, "Xabar bo‘sh bo‘lishi mumkin emas")
        mention = re.match(r"^@(supervisor|developer|qa|devops|security)\b", text, re.I)
        agent_id = mention.group(1).lower() if mention else "supervisor"
        message_id = db.id()
        with db.connect() as conn:
            agent = conn.execute(
                "SELECT enabled FROM agents WHERE id=?", (agent_id,)
            ).fetchone()
            if not agent["enabled"]:
                raise HTTPException(409, "Bu agent pauzada. Avval agentni yoqing.")
            conn.execute(
                "INSERT INTO messages VALUES (?,?,?,?,?)",
                (message_id, payload.project_id, "owner", text, time.time()),
            )
            db.event(
                conn,
                "message_saved",
                "Jamoa chatiga yangi xabar yozildi.",
                payload.project_id,
            )
            queued = runtime.queue(
                conn, payload.project_id, agent_id, "message", message_id
            )
        return {
            "id": message_id,
            "saved": True,
            "execution_started": False,
            "queued": queued,
        }

    @app.post("/api/tasks", status_code=201)
    def task(payload: TaskInput):
        project_exists(payload.project_id)
        title = payload.title.strip()
        if not title:
            raise HTTPException(422, "Vazifa nomini yozing")
        agent_id = "supervisor" if payload.team_review else payload.agent_id
        stage = "team_plan" if payload.team_review else "task"
        with db.connect() as conn:
            agent = conn.execute(
                "SELECT enabled FROM agents WHERE id=?", (agent_id,)
            ).fetchone()
            if not agent:
                raise HTTPException(422, "Agent topilmadi")
            if not agent["enabled"]:
                raise HTTPException(409, "Bu agent pauzada. Avval agentni yoqing.")
            task_id = db.id()
            conn.execute(
                "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?)",
                (
                    task_id,
                    payload.project_id,
                    title,
                    payload.description,
                    agent_id,
                    "new",
                    time.time(),
                    time.time(),
                ),
            )
            db.event(
                conn,
                "task_created",
                f"“{title}” navbatga qo‘shildi.",
                payload.project_id,
            )
            if payload.team_review:
                conn.execute("INSERT INTO team_reviews(task_id) VALUES (?)", (task_id,))
            queued = runtime.queue(conn, payload.project_id, agent_id, stage, task_id)
        return {
            "id": task_id,
            "status": "new",
            "execution_started": False,
            "queued": queued,
        }

    @app.post("/api/tasks/{task_id}/clarification")
    async def clarify_task(task_id: str, payload: ClarificationInput):
        answer = payload.text.strip()
        if not answer:
            raise HTTPException(422, "Javobingizni yozing")
        with db.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            task = conn.execute(
                "SELECT t.project_id FROM tasks t JOIN team_reviews r ON r.task_id=t.id "
                "WHERE t.id=? AND t.status='clarification'",
                (task_id,),
            ).fetchone()
            if not task:
                raise HTTPException(409, "Vazifa aniqlik kutmayapti")
            if not runtime.enabled("supervisor"):
                raise HTTPException(409, "Supervisor provayderi ulanmagan yoki o‘chiq")
            old = conn.execute(
                "SELECT clarification FROM team_reviews WHERE task_id=?", (task_id,)
            ).fetchone()[0]
            if len(old) + len(answer) > 3000:
                raise HTTPException(
                    409,
                    "Aniqliklar limiti tugadi. Talablarni jamlab yangi vazifa oching.",
                )
            now = time.time()
            conn.execute(
                "UPDATE team_reviews SET clarification=?, route='' WHERE task_id=?",
                (f"{old}\n{answer}".strip(), task_id),
            )
            conn.execute(
                "INSERT INTO messages VALUES (?,?,?,?,?)",
                (db.id(), task["project_id"], "owner", answer, now),
            )
            conn.execute(
                f"DELETE FROM team_replies WHERE job_id IN (SELECT id FROM jobs WHERE reference_id=? AND source_kind IN {TASK_KINDS_SQL})",
                (task_id,),
            )
            conn.execute(
                f"UPDATE jobs SET status='cancelled',error_code=NULL WHERE reference_id=? AND source_kind IN {TASK_KINDS_SQL}",
                (task_id,),
            )
            plan = conn.execute(
                "SELECT id FROM jobs WHERE reference_id=? AND source_kind='team_plan'",
                (task_id,),
            ).fetchone()[0]
            conn.execute(
                "UPDATE jobs SET status='queued',updated_at=? WHERE id=?",
                (now, plan),
            )
            db.job_step(conn, plan, "queued")
            conn.execute(
                "UPDATE tasks SET status='new',updated_at=? WHERE id=?", (now, task_id)
            )
        return {"queued": True}

    @app.post("/api/tasks/{task_id}/cancel")
    async def cancel_task(task_id: str):
        with db.connect() as conn:
            task = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not task:
                raise HTTPException(404, "Vazifa topilmadi")
            if task["status"] == "cancelled":
                return {"status": "cancelled"}
            if task["status"] == "done":
                raise HTTPException(409, "Yakunlangan vazifani bekor qilib bo‘lmaydi")
            conn.execute(
                "UPDATE tasks SET status=?,updated_at=? WHERE id=?",
                ("cancelled", time.time(), task_id),
            )
            db.event(
                conn,
                "task_cancelled",
                f"“{task['title']}” bekor qilindi.",
                task["project_id"],
            )
        runtime.cancel_task(task_id)
        return {"status": "cancelled"}

    @app.post("/api/tasks/{task_id}/pause")
    async def pause_task(task_id: str):
        with db.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            task = conn.execute(
                "SELECT status,project_id FROM tasks WHERE id=?", (task_id,)
            ).fetchone()
            if not task:
                raise HTTPException(404, "Vazifa topilmadi")
            if task["status"] not in ("new", "running", "paused"):
                raise HTTPException(409, "Bu vazifani pauzaga qo‘yib bo‘lmaydi")
            conn.execute(
                "UPDATE tasks SET status='paused',updated_at=? WHERE id=?",
                (time.time(), task_id),
            )
            conn.execute(
                "UPDATE jobs SET status='paused',error_code='owner_pause',updated_at=? "
                f"WHERE source_kind IN {TASK_KINDS_SQL} AND reference_id=? AND status IN ('queued','running')",
                (time.time(), task_id),
            )
            db.event(
                conn,
                "task_paused",
                "Egasi vazifani pauzaga qo‘ydi.",
                task["project_id"],
            )
        # A submitted paid request may still be billed. Its result is discarded.
        return {"status": "paused"}

    @app.post("/api/limits")
    def update_limits(payload: LimitsInput):
        db.save_setting("limits", payload.model_dump())
        with db.connect() as conn:
            db.event(conn, "limits_updated", "AI chaqiruv limitlari yangilandi.")
            if payload.paid_calls_enabled:
                conn.execute(
                    "UPDATE jobs SET status='queued',error_code=NULL,updated_at=? WHERE status='paused' AND error_code='calls_paused'",
                    (time.time(),),
                )
        return {"saved": True}

    @app.post("/api/tasks/{task_id}/run")
    async def retry_task(task_id: str):
        with db.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            task = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not task:
                raise HTTPException(404, "Vazifa topilmadi")
            if task["status"] not in ("new", "paused", "error"):
                raise HTTPException(409, "Bu vazifani hozir qayta boshlash mumkin emas")
            job = conn.execute(
                f"SELECT id,agent_id FROM jobs WHERE source_kind IN {TASK_KINDS_SQL} AND reference_id=? "
                "AND status IN ('queued','paused','failed') ORDER BY updated_at DESC LIMIT 1",
                (task_id,),
            ).fetchone()
            if not runtime.enabled(job["agent_id"] if job else task["agent_id"]):
                raise HTTPException(
                    409, "Agent provayderi ulanmagan yoki chaqiruvlar o‘chiq"
                )
            if job and job["id"] in runtime.active:
                raise HTTPException(409, "Avvalgi so‘rov hali tugamadi. Biroz kuting.")
            if job:
                conn.execute(
                    "UPDATE jobs SET status='queued',error_code=NULL,updated_at=? WHERE id=?",
                    (time.time(), job["id"]),
                )
            else:
                team = conn.execute(
                    "SELECT 1 FROM team_reviews WHERE task_id=?", (task_id,)
                ).fetchone()
                runtime.queue(
                    conn,
                    task["project_id"],
                    task["agent_id"],
                    "team_plan" if team else "task",
                    task_id,
                )
            conn.execute(
                "UPDATE tasks SET status='new',updated_at=? WHERE id=?",
                (time.time(), task_id),
            )
        return {"queued": True}

    @app.patch("/api/agents/{agent_id}")
    def update_agent(agent_id: str, payload: AgentInput):
        if payload.provider_id and not runtime.providers.configuration(
            payload.provider_id
        ).get("encrypted_key"):
            raise HTTPException(422, "Avval provayderni sozlang")
        with db.connect() as conn:
            result = conn.execute(
                "UPDATE agents SET model=?,persona=?,enabled=? WHERE id=?",
                (payload.model, payload.persona, int(payload.enabled), agent_id),
            )
            if not result.rowcount:
                raise HTTPException(404, "Agent topilmadi")
            if payload.provider_id is not None:
                conn.execute(
                    "INSERT INTO settings VALUES ('agent_providers','{}') ON CONFLICT(key) DO NOTHING"
                )
                conn.execute(
                    "UPDATE settings SET value=json_set(value,?,?) WHERE key='agent_providers'",
                    (f"$.{agent_id}", payload.provider_id or "deepseek"),
                )
            if "monthly_call_limit" in payload.model_fields_set:
                conn.execute(
                    "INSERT INTO settings VALUES ('agent_call_limits','{}') ON CONFLICT(key) DO NOTHING"
                )
                conn.execute(
                    "UPDATE settings SET value=json_set(value,?,?) WHERE key='agent_call_limits'",
                    (f"$.{agent_id}", payload.monthly_call_limit),
                )
            db.event(conn, "agent_updated", f"{agent_id} sozlamalari saqlandi.")
        return {"saved": True}

    @app.post("/api/provider")
    def save_default_provider(payload: ProviderInput):
        return save_provider(payload, "deepseek")

    @app.put("/api/providers/{provider_id}")
    def save_provider(payload: ProviderInput, provider_id: str):
        if provider_id == "new" or not PROVIDER_ID.fullmatch(provider_id):
            raise HTTPException(422, "Provayder ID noto‘g‘ri")
        if not payload.model.strip():
            raise HTTPException(422, "Model ID bo‘sh bo‘lishi mumkin emas")
        old = runtime.providers.configuration(provider_id)
        endpoint = old.get("base_url")
        if provider_id != "deepseek":
            try:
                endpoint = validate_endpoint(payload.base_url.strip())
            except ValueError as error:
                raise HTTPException(422, str(error)) from None
            if old and old.get("base_url") != endpoint and not payload.api_key.strip():
                raise HTTPException(422, "Manzil o‘zgarsa yangi API kalitini kiriting")
        encrypted = (
            provider_cipher.encrypt(payload.api_key.strip().encode()).decode()
            if payload.api_key.strip()
            else old.get("encrypted_key")
        )
        if not encrypted:
            raise HTTPException(422, "API kalitini kiriting")
        db.save_setting(
            "provider" if provider_id == "deepseek" else f"provider:{provider_id}",
            {
                "id": provider_id,
                "encrypted_key": encrypted,
                "model": payload.model.strip(),
                "name": "DeepSeek"
                if provider_id == "deepseek"
                else payload.name.strip() or provider_id,
                "adapter": "deepseek"
                if provider_id == "deepseek"
                else "openai-compatible",
                "base_url": endpoint,
            },
        )
        with db.connect() as conn:
            db.event(
                conn,
                "provider_saved",
                f"{provider_id} konfiguratsiyasi shifrlanib saqlandi.",
            )
        return {
            "saved": True,
            "connected": False,
            "message": "Konfiguratsiya saqlandi; tarmoq tekshiruvi bajarilmadi.",
        }

    @app.post("/api/provider/test")
    async def test_default_provider():
        return await test_provider("deepseek")

    @app.post("/api/providers/{provider_id}/test")
    async def test_provider(provider_id: str):
        provider = runtime.providers.configuration(provider_id)
        if not provider.get("encrypted_key"):
            raise HTTPException(409, "Avval API kalitini saqlang")
        started = time.monotonic()
        try:
            connection = runtime.providers.connection(provider, provider["model"])
            models = await connection.models()
        except httpx.HTTPStatusError as error:
            raise HTTPException(
                502, f"Provayder HTTP {error.response.status_code}"
            ) from None
        except (httpx.HTTPError, InvalidToken, ValueError, KeyError, TypeError):
            raise HTTPException(502, "Provayder katalogiga ulanib bo‘lmadi") from None
        return {
            "reachable": True,
            "model": provider["model"],
            "model_available": provider["model"] in models,
            "latency_ms": round((time.monotonic() - started) * 1000),
        }

    @app.get("/")
    def index():
        index_file = ROOT / "web/dist/index.html"
        if not index_file.exists():
            raise HTTPException(503, "Frontend build kerak: cd web && npm run build")
        return FileResponse(index_file)

    assets = ROOT / "web/dist/assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/favicon.svg")
    def favicon():
        return FileResponse(ROOT / "web/public/favicon.svg")

    return app
