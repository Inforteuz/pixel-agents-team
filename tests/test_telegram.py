import asyncio
import io
import json
import time
import zipfile

import httpx

from backend.app import create_app
from backend.telegram import safe_zip


def archive(name):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as zipped:
        zipped.writestr(name, "example")
    return output.getvalue()


def test_zip_metadata_rejects_paths_outside_project():
    assert safe_zip(archive("src/app.py"))
    assert not safe_zip(archive("../../outside"))
    assert not safe_zip(archive("C:/outside"))


def test_telegram_duplicate_disallowed_and_voice_handoff(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHAT_ID", "-10030")
    monkeypatch.setenv("OWNER_TELEGRAM_USER_ID", "123")
    monkeypatch.setenv("TELEGRAM_QUIET_HOURS", "0")
    monkeypatch.setenv("PIXEL_TRANSCRIPTION_KEY", "synthetic")
    seen = []

    def upstream(request):
        method = request.url.path.rsplit("/", 1)[-1]
        seen.append(method)
        if method == "getFile":
            return httpx.Response(
                200, json={"ok": True, "result": {"file_path": "voice/test.oga"}}
            )
        if method == "test.oga":
            return httpx.Response(200, content=b"OggS synthetic mock")
        if method.endswith(":generateContent"):
            assert (
                json.loads(request.content)["contents"][0]["parts"][1]["inlineData"][
                    "mimeType"
                ]
                == "audio/ogg"
            )
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "finishReason": "STOP",
                            "content": {
                                "parts": [
                                    {"text": "discard", "thought": True},
                                    {"text": "@qa Logni ko‘rib bering?"},
                                ]
                            },
                        }
                    ]
                },
            )
        raise AssertionError(method)

    app = create_app(tmp_path, telegram_transport=httpx.MockTransport(upstream))
    bridge = app.state.telegram
    app.state.db.save_setting("provider", {"encrypted_key": "synthetic"})
    owner = {"id": 123, "is_bot": False}
    chat = {"id": -10030, "type": "supergroup"}
    base = {"message_id": 5, "chat": chat, "from": owner, "date": int(time.time())}
    bridge.accept_updates(
        [
            {
                "update_id": 1,
                "message": {**base, "from": {"id": 999}, "text": "/task bypass"},
            },
            {
                "update_id": 2,
                "message": {
                    **base,
                    "from": {**owner, "is_bot": True},
                    "text": "/task bypass",
                },
            },
            {
                "update_id": 3,
                "message": {**base, "voice": {"file_id": "mock", "duration": 5}},
            },
            {
                "update_id": 3,
                "message": {**base, "voice": {"file_id": "mock", "duration": 5}},
            },
        ]
    )

    async def process():
        async with httpx.AsyncClient(transport=bridge.transport) as client:
            await bridge.handle(
                client, bridge.pending("telegram_inbox", "queued", "processing")
            )

    asyncio.run(process())
    assert bridge.pending("telegram_inbox", "queued", "processing") is None
    state = app.state.db.snapshot("default")
    assert [row["text"] for row in state["messages"]] == ["@qa Logni ko‘rib bering?"]
    assert state["tasks"] == []
    assert [row["agent_id"] for row in state["jobs"]] == ["qa"]
    assert len(seen) == 3


def test_internal_peer_reply_has_no_telegram_ingress_dependency(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHAT_ID", "-10030")
    monkeypatch.setenv("OWNER_TELEGRAM_USER_ID", "123")
    monkeypatch.setenv("TELEGRAM_QUIET_HOURS", "0")

    def llm(request):
        prompts = json.loads(request.content)["messages"]
        response = (
            "QA tekshiruvini taklif qilaman."
            if "Developer" in prompts[0]["content"]
            else "Birinchi navbatda xato holatini test qiling."
        )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"finish_reason": "stop", "message": {"content": response}}
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 8},
            },
        )

    app = create_app(tmp_path, llm_transport=httpx.MockTransport(llm))
    db, runtime, bridge = app.state.db, app.state.runtime, app.state.telegram
    db.save_setting(
        "provider",
        {"encrypted_key": runtime.cipher.encrypt(b"test").decode(), "model": "mock"},
    )
    bridge.accept_updates(
        [
            {
                "update_id": 9,
                "message": {
                    "from": {"id": 123},
                    "chat": {"id": -10030, "type": "supergroup"},
                    "message_id": 4,
                    "date": int(time.time()),
                    "text": "@developer+qa Xatoni qanday tekshiramiz?",
                },
            }
        ]
    )

    async def process():
        async with httpx.AsyncClient() as client:
            await bridge.handle(
                client, bridge.pending("telegram_inbox", "queued", "processing")
            )
        await runtime.execute(runtime.next_job())
        await runtime.execute(runtime.next_job())

    asyncio.run(process())
    with db.connect() as conn:
        replies = conn.execute(
            "SELECT agent_id FROM telegram_outbox ORDER BY created_at"
        ).fetchall()
        assert [row["agent_id"] for row in replies] == ["developer", "qa"]
    assert runtime.next_job() is None


def test_telegram_conversation_and_quotes_do_not_create_tasks():
    from backend.telegram import classify

    for utterance in (
        "qil deb aytdi",
        "tuzatish kerakmi?",
        "stop",
        "«/task inventar» degan buyruq",
        "исправь — так написано",
    ):
        assert classify(utterance) != "task"
    assert classify("/task inventar eksportini taklif qiling?") == "task"
    assert classify("@qa /task Filtrni tekshirish") == "task"


def test_private_basic_group_owner_start_and_explicit_task(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHAT_ID", "-700")
    monkeypatch.setenv("OWNER_TELEGRAM_USER_ID", "123")
    monkeypatch.setenv("TELEGRAM_QUIET_HOURS", "0")
    app = create_app(tmp_path)
    bridge = app.state.telegram
    bridge.supervisor_username = "test_supervisor"
    app.state.db.save_setting("provider", {"encrypted_key": "synthetic"})
    base = {
        "chat": {"id": -700, "type": "group"},
        "from": {"id": 123},
        "date": int(time.time()),
    }
    inputs = ("/start@test_supervisor", "qil deb yozibdi", "/task Inventar ro‘yxati")
    bridge.accept_updates(
        [
            {"update_id": i, "message": {**base, "message_id": i, "text": message}}
            for i, message in enumerate(inputs, 1)
        ]
    )

    async def run():
        async with httpx.AsyncClient() as client:
            for _ in inputs:
                await bridge.handle(
                    client, bridge.pending("telegram_inbox", "queued", "processing")
                )

    asyncio.run(run())
    with app.state.db.connect() as conn:
        actions = [
            (r["source_kind"], r["agent_id"])
            for r in conn.execute(
                "SELECT source_kind,agent_id FROM jobs ORDER BY rowid"
            )
        ]
        assert actions == [("message", "supervisor"), ("team_plan", "supervisor")]
        assert conn.execute("SELECT count(*) FROM tasks").fetchone()[0] == 1
        assert (
            conn.execute("SELECT agent_id FROM telegram_outbox").fetchone()[0]
            == "supervisor"
        )
