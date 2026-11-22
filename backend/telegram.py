"""Owner-only Telegram bridge. SQLite owns the inbox, replies and delivery state."""

import asyncio
import base64
import hashlib
import io
import json
import os
import re
import stat
import time
import zipfile
from pathlib import PurePosixPath
from zoneinfo import ZoneInfo
from datetime import datetime

import httpx

ROLES = ("supervisor", "developer", "qa", "devops", "security")
MENTION = re.compile(
    r"^@(" + "|".join(ROLES) + r")(?:\+(" + "|".join(ROLES) + r"))?\b", re.I
)
BOTS = re.compile(r"\d{5,}:[A-Za-z0-9_-]{20,}")
FILES = {
    "zip": "application/zip",
    "txt": "text/plain",
    "json": "application/json",
    "md": "text/plain",
    "photo": "image/jpeg",
    "voice": "audio/ogg",
}
MAX_FILE = 5 * 1024 * 1024
MAX_STORED = 100 * 1024 * 1024
AUDIO_MODEL = "gemini-3.5-transcribe"


def safe_zip(content):
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        members = archive.infolist()
        if len(members) > 1000 or sum(m.file_size for m in members) > 50 * 1024 * 1024:
            return False
        seen = set()
        for item in members:
            name = item.orig_filename
            path = PurePosixPath(name)
            mode = stat.S_IFMT(item.external_attr >> 16)
            normalized = str(path).casefold()
            if (
                not name
                or normalized == "."
                or path.is_absolute()
                or ".." in path.parts
                or any(c in name for c in "\\:\x00")
                or normalized in seen
                or mode not in {0, stat.S_IFREG, stat.S_IFDIR}
                or item.flag_bits & 1
                or item.file_size > 150 * max(item.compress_size, 1)
            ):
                return False
            seen.add(normalized)
        return bool(members)


def classify(text, attached=False):
    """High-confidence signals only. Unclear work is always a text turn."""
    if not text:
        return "attachment_only" if attached else "irrelevant"
    if re.fullmatch(
        r"(salom|assalomu alaykum|привет|спасибо|rahmat|hi)[.! ]*", text, re.I
    ):
        return "social"
    if re.match(
        r"^(?:@\S+\s+)?(?:/task\s+|qil(?:ing)?\b|tuzat\b|создай\b|исправь\b)",
        text,
        re.I,
    ):
        return "task"
    if text.endswith("?"):
        return "question"
    return "unclear"


def publish(conn, db, agent, chat_id, reply_to, text):
    conn.execute(
        "INSERT INTO telegram_outbox VALUES (?,?,?,?,?,'queued',?,NULL)",
        (db.id(), agent, chat_id, reply_to, text, time.time()),
    )


class TelegramBridge:
    def __init__(self, db, runtime, transport=None):
        self.db, self.runtime, self.transport = db, runtime, transport
        self.tokens = {
            role: os.getenv(f"BOT_{role.upper()}_TOKEN", "") for role in ROLES
        }
        self.key = os.getenv("PIXEL_TRANSCRIPTION_KEY", "")
        self.project = os.getenv("TELEGRAM_PROJECT_ID", "default")
        self.social = os.getenv("TELEGRAM_SOCIAL", "0") == "1"
        self.quiet = os.getenv("TELEGRAM_QUIET_HOURS", "1") == "1"
        self.chat_id = self.integer("TELEGRAM_ALLOWED_CHAT_ID")
        self.owner_id = self.integer("OWNER_TELEGRAM_USER_ID")
        self.tasks = []
        self.connected = False

    @staticmethod
    def integer(name):
        try:
            return int(os.getenv(name, ""))
        except ValueError:
            return 0

    @property
    def configured(self):
        return (
            self.chat_id < 0
            and self.owner_id > 0
            and len({token.partition(":")[0] for token in self.tokens.values()}) == 5
            and all(BOTS.fullmatch(t) for t in self.tokens.values())
        )

    async def start(self):
        if not self.configured:
            return
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE telegram_inbox SET status='unknown',payload='{}' WHERE status='processing'"
            )
            conn.execute(
                "UPDATE telegram_outbox SET status='unknown' WHERE status='sending'"
            )
        self.tasks = [
            asyncio.create_task(self.poll()),
            asyncio.create_task(self.process()),
        ]

    async def stop(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()

    def state(self):
        return {
            "configured": self.configured,
            "connected": self.connected,
            "voice": bool(self.configured and self.key),
            "bots": sum(bool(BOTS.fullmatch(t)) for t in self.tokens.values()),
        }

    @property
    def bot_id(self):
        return self.tokens["supervisor"].partition(":")[0]

    @property
    def offset_key(self):
        return f"telegram_offset:{self.bot_id}"

    async def bot(self, client, role, method, payload):
        result = await client.post(
            f"https://api.telegram.org/bot{self.tokens[role]}/{method}",
            json=payload,
        )
        result.raise_for_status()
        response = result.json()
        if not response["ok"]:
            raise ValueError("telegram_api")
        return response["result"]

    def allowed(self, msg):
        sender = msg.get("from", {})
        chat = msg.get("chat", {})
        return (
            not sender.get("is_bot")
            and sender.get("id") == self.owner_id
            and chat.get("id") == self.chat_id
            and chat.get("type") == "supergroup"
            and not msg.get("sender_chat")
            and time.time() - msg.get("date", 0) <= 86400
        )

    def accept_updates(self, updates):
        with self.db.connect() as conn:
            for update in updates:
                msg = update.get("message", {})
                if not self.allowed(msg):
                    continue
                if not any(k in msg for k in ("text", "voice", "photo", "document")):
                    continue
                conn.execute(
                    "INSERT OR IGNORE INTO telegram_inbox(bot_id,update_id,payload,status,created_at) "
                    "VALUES (?,?,?,'queued',?)",
                    (self.bot_id, update["update_id"], json.dumps(msg), time.time()),
                )
            if updates:
                conn.execute(
                    "INSERT INTO settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (self.offset_key, str(max(u["update_id"] for u in updates) + 1)),
                )

    async def poll(self):
        async with httpx.AsyncClient(timeout=30, transport=self.transport) as client:
            while True:
                try:
                    if not self.connected:
                        group = await self.bot(
                            client, "supervisor", "getChat", {"chat_id": self.chat_id}
                        )
                        if (
                            group["type"] != "supergroup"
                            or group.get("username")
                            or group.get("active_usernames")
                        ):
                            raise ValueError("private_group_required")
                    updates = await self.bot(
                        client,
                        "supervisor",
                        "getUpdates",
                        {
                            "offset": self.db.setting(self.offset_key, 0),
                            "timeout": 20,
                            "allowed_updates": ["message"],
                            "limit": 30,
                        },
                    )
                    self.accept_updates(updates)
                    self.connected = True
                    if not updates:
                        await asyncio.sleep(0.2)
                except (httpx.HTTPError, ValueError, KeyError, TypeError):
                    self.connected = False
                    await asyncio.sleep(5)

    def pending(self, table, queued, processing):
        # Table and state parameters come solely from process().
        with self.db.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                f"SELECT * FROM {table} WHERE status=? ORDER BY created_at LIMIT 1",
                (queued,),
            ).fetchone()
            if row:
                conn.execute(
                    f"UPDATE {table} SET status=? WHERE id=?", (processing, row["id"])
                )
            return row

    async def process(self):
        async with httpx.AsyncClient(timeout=30, transport=self.transport) as client:
            while True:
                if not self.connected:
                    await asyncio.sleep(0.4)
                    continue
                update = self.pending("telegram_inbox", "queued", "processing")
                if update:
                    try:
                        await self.handle(client, update)
                    except (
                        httpx.HTTPError,
                        ValueError,
                        KeyError,
                        TypeError,
                        IndexError,
                        zipfile.BadZipFile,
                    ):
                        with self.db.connect() as conn:
                            conn.execute(
                                "UPDATE telegram_inbox SET status='failed',payload='{}' WHERE id=?",
                                (update["id"],),
                            )
                            msg = json.loads(update["payload"])
                            publish(
                                conn,
                                self.db,
                                "supervisor",
                                self.chat_id,
                                msg["message_id"],
                                "Xabar yoki faylni o‘qiy olmadim. Qayta jo‘nating.",
                            )
                outgoing = self.pending("telegram_outbox", "queued", "sending")
                if outgoing:
                    if outgoing["chat_id"] == self.chat_id:
                        await self.deliver(client, outgoing)
                    else:
                        with self.db.connect() as conn:
                            conn.execute(
                                "UPDATE telegram_outbox SET status='unknown' WHERE id=?",
                                (outgoing["id"],),
                            )
                if not update and not outgoing:
                    await asyncio.sleep(0.4)

    async def deliver(self, client, row):
        try:
            msg = await self.bot(
                client,
                row["agent_id"],
                "sendMessage",
                {
                    "chat_id": row["chat_id"],
                    "text": row["text"][:3900],
                    "reply_parameters": {
                        "message_id": row["reply_to"],
                        "allow_sending_without_reply": True,
                    },
                    "link_preview_options": {"is_disabled": True},
                },
            )
            status, message_id = "sent", msg["message_id"]
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            # Retrying a timed-out send can duplicate a delivered message.
            status, message_id = "unknown", None
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE telegram_outbox SET status=?,telegram_message_id=? WHERE id=?",
                (status, message_id, row["id"]),
            )

    async def download(self, client, item):
        if item.get("file_size", 0) > MAX_FILE:
            raise ValueError("attachment_size")
        result = await self.bot(
            client, "supervisor", "getFile", {"file_id": item["file_id"]}
        )
        path = result["file_path"]
        if not re.fullmatch(r"[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+", path) or path.split("/")[
            -1
        ] in {".", ".."}:
            raise ValueError("attachment_path")
        data = bytearray()
        async with client.stream(
            "GET",
            f"https://api.telegram.org/file/bot{self.tokens['supervisor']}/{path}",
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                data.extend(chunk)
                if len(data) > MAX_FILE:
                    raise ValueError("attachment_size")
        return bytes(data)

    async def transcribe(self, client, item):
        if not self.key or not self.runtime.limits()["paid_calls_enabled"]:
            return (
                "",
                "Ovozli xabar uchun transkripsiya sozlanmagan yoki pulli AI o‘chirilgan.",
            )
        if not 0 < item.get("duration", 0) <= 120:
            return "", "Ovozli xabar 2 daqiqadan oshmasin."
        with self.db.connect() as conn:
            conn.execute(
                "DELETE FROM voice_usage WHERE created_at<=?", (time.time() - 86400,)
            )
            if (
                conn.execute(
                    "SELECT COUNT(*) FROM voice_usage WHERE created_at>?",
                    (time.time() - 86400,),
                ).fetchone()[0]
                >= 12
            ):
                return "", "Ovozli xabar limiti tugadi. Matn yozing."
            conn.execute("INSERT INTO voice_usage VALUES (?)", (time.time(),))
        data = await self.download(client, item)
        if not data.startswith(b"OggS"):
            raise ValueError("audio_format")
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{AUDIO_MODEL}:generateContent",
            headers={"x-goog-api-key": self.key},
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": "Transcribe only the spoken words verbatim. Uzbek in Latin script, preserve Russian where spoken. Return text only."
                            },
                            {
                                "inlineData": {
                                    "mimeType": "audio/ogg",
                                    "data": base64.b64encode(data).decode(),
                                }
                            },
                        ]
                    }
                ],
                "generationConfig": {"maxOutputTokens": 1500},
            },
        )
        response.raise_for_status()
        candidate = response.json()["candidates"][0]
        if candidate.get("finishReason") != "STOP":
            raise ValueError("audio_incomplete")
        text = "".join(
            p.get("text", "")
            for p in candidate["content"]["parts"]
            if not p.get("thought")
        ).strip()
        if not text or len(text) > 6000:
            raise ValueError("audio_transcript")
        return text, ""

    async def handle(self, client, update):
        msg = json.loads(update["payload"])
        if update["bot_id"] != self.bot_id or not self.allowed(msg):
            with self.db.connect() as conn:
                conn.execute(
                    "UPDATE telegram_inbox SET status='ignored',payload='{}' WHERE id=?",
                    (update["id"],),
                )
            return
        source_id = msg["message_id"]
        text = (msg.get("text") or msg.get("caption") or "").strip()[:6000]
        note = ""
        attachment = None
        hour = datetime.now(ZoneInfo("Asia/Tashkent")).hour
        silent = self.quiet and (hour >= 23 or hour < 8)
        if "voice" in msg:
            text, note = await self.transcribe(client, msg["voice"])
        elif msg.get("photo") or msg.get("document"):
            item = msg["photo"][-1] if msg.get("photo") else msg["document"]
            name = (
                (item.get("file_name") or "telegram.jpg")
                .replace("\\", "/")
                .split("/")[-1][:160]
            )
            kind = "photo" if msg.get("photo") else name.rsplit(".", 1)[-1].lower()
            if kind not in FILES or kind in {"voice", "photo"} and not msg.get("photo"):
                raise ValueError("attachment_type")
            data = await self.download(client, item)
            if kind == "zip" and not safe_zip(data):
                raise ValueError("unsafe_zip")
            attachment = (
                kind,
                name,
                FILES[kind],
                item["file_id"],
                self.owner_id,
                hashlib.sha256(data).hexdigest(),
                data,
            )
        urgent = "voice" not in msg and text.startswith("/urgent ")
        if urgent:
            text = text.removeprefix("/urgent ").strip()
        intent = classify(text, bool(attachment))
        # Voice always enters chat. Only typed task requests create board items.
        explicit_task = "voice" not in msg and intent == "task"
        pause = "voice" not in msg and text.casefold() in {
            "/pause",
            "/stop",
            "stop",
            "pauza",
            "стоп",
            "пауза",
        }
        with self.db.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if not conn.execute(
                "SELECT 1 FROM projects WHERE id=?", (self.project,)
            ).fetchone():
                raise ValueError("project")
            if attachment:
                stored = conn.execute(
                    "SELECT COALESCE(SUM(length(content)),0) FROM telegram_attachments"
                ).fetchone()[0]
                if stored + len(attachment[-1]) > MAX_STORED:
                    raise ValueError("attachment_storage")
                conn.execute(
                    "INSERT INTO telegram_attachments VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (update["id"], self.project, *attachment, time.time()),
                )
                self.db.event(
                    conn,
                    "attachment_saved",
                    f"Telegram fayli: {attachment[1]}",
                    self.project,
                )
            display = text + (f"\n[TG fayl: {attachment[1]}]" if attachment else "")
            message_id = self.db.id()
            if display:
                conn.execute(
                    "INSERT INTO messages VALUES (?,?,?,?,?)",
                    (message_id, self.project, "owner", display, time.time()),
                )
            if pause:
                conn.execute(
                    "UPDATE tasks SET status='paused',updated_at=? WHERE project_id=? AND status IN ('new','running')",
                    (time.time(), self.project),
                )
                conn.execute(
                    "UPDATE jobs SET status='paused',error_code='owner_pause' WHERE project_id=? AND status IN ('queued','running')",
                    (self.project,),
                )
                note = "Faol va navbatdagi ishlar pauzaga qo‘yildi."
            if intent == "attachment_only" and not silent:
                note = "Fayl saqlandi. Bu bilan nima qilay?"
            if note:
                publish(conn, self.db, "supervisor", self.chat_id, source_id, note)
            eligible = (
                text
                and not note
                and (not silent or urgent)
                and (intent != "social" or self.social)
            )
            if eligible:
                match = MENTION.match(text)
                agent = (
                    match[1].lower()
                    if match
                    else ("developer" if explicit_task else "supervisor")
                )
                peer = match[2].lower() if match and match[2] else None
                if peer == agent or "voice" in msg:
                    peer = None
                reference, kind = message_id, "message"
                if explicit_task:
                    task_text = re.sub(r"^(?:@\S+\s+)?/task\s+", "", text, flags=re.I)
                    reference, kind = self.db.id(), "task"
                    now = time.time()
                    conn.execute(
                        "INSERT INTO tasks VALUES (?,?,?,?,?,'new',?,?)",
                        (
                            reference,
                            self.project,
                            task_text[:180],
                            task_text,
                            agent,
                            now,
                            now,
                        ),
                    )
                enabled = conn.execute(
                    "SELECT enabled FROM agents WHERE id=?", (agent,)
                ).fetchone()
                if not enabled or not enabled["enabled"]:
                    publish(
                        conn,
                        self.db,
                        "supervisor",
                        self.chat_id,
                        source_id,
                        "Bu agent pauzada. Boshqa agentni tanlang.",
                    )
                elif self.runtime.queue(conn, self.project, agent, kind, reference):
                    job = conn.execute(
                        "SELECT id FROM jobs WHERE source_kind=? AND reference_id=?",
                        (kind, reference),
                    ).fetchone()
                    conn.execute(
                        "INSERT INTO telegram_routes VALUES (?,?,?,?,NULL)",
                        (job["id"], self.chat_id, source_id, peer),
                    )
                else:
                    publish(
                        conn,
                        self.db,
                        "supervisor",
                        self.chat_id,
                        source_id,
                        "Xabar saqlandi. Pulli AI hozir o‘chiq yoki sozlanmagan.",
                    )
            conn.execute(
                "UPDATE telegram_inbox SET status='done',payload='{}' WHERE id=?",
                (update["id"],),
            )
