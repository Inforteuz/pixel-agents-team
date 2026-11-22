"""Single-owner web access. Sessions, throttling and audit survive a restart.

This is an access boundary, not an execution sandbox. No network request can
disable it or turn the legacy terminal/deployment endpoints back on.
"""

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

COOKIE = "pixel_session"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
PUBLIC_PATHS = {
    "/",
    "/login",
    "/favicon.svg",
    "/api/auth/login",
    "/api/auth/status",
    "/health/live",
    "/health/ready",
}


def hash_password(password: str) -> str:
    if not 12 <= len(password) <= 1024:
        raise ValueError("Administrator password must contain 12 to 1024 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=32768, r=8, p=1, maxmem=64 * 1024 * 1024
    )
    return f"scrypt${salt.hex()}${digest.hex()}"


def valid_password_hash(value: str) -> bool:
    try:
        algorithm, salt, digest = value.split("$")
        return (
            algorithm == "scrypt"
            and len(bytes.fromhex(salt)) == 16
            and len(bytes.fromhex(digest)) == 64
        )
    except (ValueError, TypeError):
        return False


def verify_password(password: str, encoded: str) -> bool:
    if not valid_password_hash(encoded):
        return False
    _, salt, expected = encoded.split("$")
    actual = hashlib.scrypt(
        password.encode(),
        salt=bytes.fromhex(salt),
        n=32768,
        r=8,
        p=1,
        maxmem=64 * 1024 * 1024,
    )
    return hmac.compare_digest(actual.hex(), expected)


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class SecuritySettings:
    password_hash: str
    public_url: str = ""
    production: bool = False
    session_seconds: int = 43200

    def __post_init__(self):
        if self.password_hash and not valid_password_hash(self.password_hash):
            raise ValueError(
                "Invalid PIXEL_ADMIN_PASSWORD_HASH; run python -m backend.admin"
            )
        parsed = urlsplit(self.public_url)
        if self.public_url and (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError(
                "APP_PUBLIC_URL must be an http(s) origin without credentials or path"
            )
        if self.public_url:
            # Validate ports at startup and normalize the canonical origin.
            parsed.port
            object.__setattr__(self, "public_url", self.public_url.rstrip("/"))
        if self.production and (parsed.scheme != "https" or not self.password_hash):
            raise ValueError(
                "Production requires HTTPS APP_PUBLIC_URL and PIXEL_ADMIN_PASSWORD_HASH"
            )
        if not 300 <= self.session_seconds <= 86400:
            raise ValueError("PIXEL_SESSION_SECONDS must be between 300 and 86400")

    @classmethod
    def from_env(cls):
        return cls(
            password_hash=os.getenv("PIXEL_ADMIN_PASSWORD_HASH", "").strip(),
            public_url=os.getenv("APP_PUBLIC_URL", "").rstrip("/"),
            production=os.getenv("APP_ENV", "development") == "production",
            session_seconds=int(os.getenv("PIXEL_SESSION_SECONDS", "43200")),
        )

    @property
    def secure_cookie(self) -> bool:
        return self.production or self.public_url.startswith("https://")

    @property
    def revision(self) -> str:
        # Changing the administrator password revokes all old sessions.
        return fingerprint(self.password_hash)


class AuthStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Restrict the database before sqlite creates journals beside it.
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        self.path.chmod(0o600)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token_hash TEXT PRIMARY KEY, csrf TEXT NOT NULL,
                    expires_at REAL NOT NULL, revision TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_attempts (
                    id INTEGER PRIMARY KEY, client TEXT NOT NULL, created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS auth_attempt_time ON auth_attempts(created_at);
                CREATE TABLE IF NOT EXISTS admin_audit (
                    id INTEGER PRIMARY KEY, created_at REAL NOT NULL,
                    actor TEXT NOT NULL, action TEXT NOT NULL, method TEXT NOT NULL,
                    route TEXT NOT NULL, status INTEGER NOT NULL
                );
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def reserve_login_attempt(self, client: str) -> bool:
        now = time.time()
        with self.connect() as db:
            # Atomic reservation also bounds concurrent password hashing work.
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM auth_attempts WHERE created_at < ?", (now - 900,))
            counts = db.execute(
                "SELECT COUNT(*) AS total, SUM(client = ?) AS own FROM auth_attempts",
                (client,),
            ).fetchone()
            if counts["total"] >= 50 or (counts["own"] or 0) >= 5:
                return False
            db.execute(
                "INSERT INTO auth_attempts(client, created_at) VALUES (?, ?)",
                (client, now),
            )
            return True

    def create_session(self, settings: SecuritySettings):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute(
                "DELETE FROM auth_sessions WHERE expires_at <= ?", (time.time(),)
            )
            db.execute(
                "INSERT INTO auth_sessions VALUES (?, ?, ?, ?)",
                (
                    fingerprint(token),
                    csrf,
                    time.time() + settings.session_seconds,
                    settings.revision,
                ),
            )
        return token, csrf

    def session(self, token: str, settings: SecuritySettings):
        if not token or len(token) > 128 or not settings.password_hash:
            return None
        with self.connect() as db:
            row = db.execute(
                "SELECT csrf, expires_at FROM auth_sessions "
                "WHERE token_hash = ? AND revision = ? AND expires_at > ?",
                (fingerprint(token), settings.revision, time.time()),
            ).fetchone()
        return dict(row) if row else None

    def revoke(self, token: str):
        with self.connect() as db:
            db.execute(
                "DELETE FROM auth_sessions WHERE token_hash = ?", (fingerprint(token),)
            )

    def audit(self, actor: str, action: str, method: str, route: str, status: int):
        # Deliberately exclude request bodies, query strings, credentials and IPs.
        with self.connect() as db:
            db.execute(
                "INSERT INTO admin_audit VALUES (NULL, ?, ?, ?, ?, ?, ?)",
                (time.time(), actor, action, method, route, status),
            )


class OwnerAccessMiddleware:
    def __init__(self, app: ASGIApp, settings: SecuritySettings, store: AuthStore):
        self.app, self.settings, self.store = app, settings, store

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        path, method = request.url.path, request.method
        session = await run_in_threadpool(
            self.store.session,
            request.cookies.get(COOKIE, ""),
            self.settings,
        )
        scope.setdefault("state", {})["owner_session"] = session

        async def secure_send(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Referrer-Policy"] = "no-referrer"
                headers["Cache-Control"] = "no-store"
                headers["Permissions-Policy"] = (
                    "camera=(), microphone=(), geolocation=()"
                )
                headers["Content-Security-Policy"] = (
                    "default-src 'self'; script-src 'self'; "
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                    "font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; "
                    "connect-src 'self'; frame-ancestors 'none'; object-src 'none'; "
                    "base-uri 'self'; form-action 'self'"
                )
                if self.settings.secure_cookie:
                    headers["Strict-Transport-Security"] = "max-age=31536000"
                if method not in SAFE_METHODS:
                    route = getattr(scope.get("route"), "path", "unmatched")
                    await run_in_threadpool(
                        self.store.audit,
                        "owner" if session else "anonymous",
                        "http_mutation",
                        method,
                        route,
                        message["status"],
                    )
            await send(message)

        async def deny(status, detail):
            await JSONResponse({"detail": detail}, status_code=status)(
                scope, receive, secure_send
            )

        # Check the configured origin, never arbitrary X-Forwarded-* headers.
        origin = request.headers.get("origin")
        expected = self.settings.public_url or str(request.base_url).rstrip("/")
        if method not in SAFE_METHODS and (
            (origin is not None and origin != expected)
            or request.headers.get("sec-fetch-site") == "cross-site"
        ):
            await deny(403, "Cross-origin requests are forbidden")
            return
        if path not in PUBLIC_PATHS and not path.startswith("/assets/"):
            if not session:
                if method == "GET" and path == "/":
                    await RedirectResponse("/login", status_code=303)(
                        scope, receive, secure_send
                    )
                else:
                    await deny(401, "Administrator sign-in required")
                return
            if method not in SAFE_METHODS and not hmac.compare_digest(
                request.headers.get("x-csrf-token", "").encode(),
                session["csrf"].encode(),
            ):
                await deny(403, "CSRF token is missing or invalid")
                return
        # Legacy publication requires a future explicit approvals workflow.
        if path.startswith("/api/terminal") or (
            path.startswith("/api/deploy") and method not in SAFE_METHODS
        ):
            await deny(403, "This operation is disabled by the server policy")
            return
        await self.app(scope, receive, secure_send)


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


def auth_router(
    settings: SecuritySettings, store: AuthStore, static_dir: Path
) -> APIRouter:
    router = APIRouter()

    @router.get("/login", include_in_schema=False)
    def login_page():
        return FileResponse(static_dir / "index.html")

    @router.get("/api/auth/status")
    def status(request: Request):
        session = request.state.owner_session
        return {
            "configured": bool(settings.password_hash),
            "authenticated": bool(session),
            "csrf_token": session["csrf"] if session else None,
        }

    @router.post("/api/auth/login")
    def login(payload: LoginRequest, request: Request):
        if not settings.password_hash:
            return JSONResponse(
                {"detail": "Configure the administrator password locally first"}, 503
            )
        # The TCP peer is authoritative. Proxy trust is configured by run.py.
        client = request.client.host if request.client else "unknown"
        if not store.reserve_login_attempt(client):
            store.audit("anonymous", "login_throttled", "POST", "/api/auth/login", 429)
            return JSONResponse(
                {"detail": "Too many sign-in attempts; try again in 15 minutes"},
                429,
                headers={"Retry-After": "900"},
            )
        if not verify_password(payload.password, settings.password_hash):
            store.audit("anonymous", "login_failed", "POST", "/api/auth/login", 401)
            return JSONResponse({"detail": "Incorrect password"}, 401)
        # Rotate even when an already authenticated browser signs in again.
        store.revoke(request.cookies.get(COOKIE, ""))
        token, csrf = store.create_session(settings)
        store.audit("owner", "login_succeeded", "POST", "/api/auth/login", 200)
        response = JSONResponse({"authenticated": True, "csrf_token": csrf})
        response.set_cookie(
            COOKIE,
            token,
            httponly=True,
            secure=settings.secure_cookie,
            samesite="strict",
            max_age=settings.session_seconds,
            path="/",
        )
        return response

    @router.post("/api/auth/logout")
    def logout(request: Request):
        store.revoke(request.cookies.get(COOKIE, ""))
        response = JSONResponse({"authenticated": False})
        response.delete_cookie(
            COOKIE,
            path="/",
            secure=settings.secure_cookie,
            httponly=True,
            samesite="strict",
        )
        return response

    @router.get("/api/security/audit")
    def audit_log():
        with store.connect() as db:
            rows = db.execute(
                "SELECT * FROM admin_audit ORDER BY id DESC LIMIT 200"
            ).fetchall()
        return {"events": [dict(row) for row in rows]}

    @router.get("/health/live")
    def live():
        return {"status": "alive"}

    @router.get("/health/ready")
    def ready():
        try:
            with store.connect() as db:
                db.execute("SELECT 1 FROM auth_sessions LIMIT 1")
        except sqlite3.Error:
            return JSONResponse({"status": "not_ready"}, 503)
        return JSONResponse(
            {"status": "ready" if settings.password_hash else "not_ready"},
            200 if settings.password_hash else 503,
        )

    return router
