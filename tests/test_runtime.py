import asyncio
import json
import time
from contextlib import contextmanager

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.llm_runtime import clean_response_text
from backend.security import hash_password

PASSWORD = "runtime-test-password-93812"


@pytest.fixture(scope="module")
def password_hash():
    return hash_password(PASSWORD)


@contextmanager
def running(tmp_path, password_hash, handler, limits=None):
    app = create_app(
        tmp_path, password_hash, llm_transport=httpx.MockTransport(handler)
    )
    key = (
        Fernet((tmp_path / "provider.key").read_bytes())
        .encrypt(b"synthetic-provider-key")
        .decode()
    )
    app.state.db.save_setting("provider", {"encrypted_key": key, "model": "test-model"})
    if limits:
        app.state.db.save_setting("limits", limits)
    with TestClient(app, base_url="http://127.0.0.1:8090") as client:
        result = client.post("/api/auth/login", json={"password": PASSWORD})
        client.headers["X-CSRF-Token"] = result.json()["csrf_token"]
        yield client, app


def wait_for(client, predicate):
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        data = client.get("/api/studio").json()
        if predicate(data):
            return data
        time.sleep(0.03)
    raise AssertionError("Runtime did not reach expected state")


def response():
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": "Sinov javobi"}}],
            "usage": {
                "prompt_tokens": 13,
                "completion_tokens": 7,
                "prompt_cache_hit_tokens": 3,
            },
        },
    )


def test_actual_role_reply_and_measured_usage(tmp_path, password_hash):
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        return response()

    with running(tmp_path, password_hash, handler) as (client, app):
        sent = client.post(
            "/api/messages",
            json={"project_id": "default", "text": "@qa Test rejasini ayting"},
        )
        assert sent.json()["queued"] is True
        data = wait_for(
            client, lambda s: any(m["sender"] == "qa" for m in s["messages"])
        )
        assert data["messages"][-1]["text"] == "Sinov javobi"
        system = calls[0]["messages"][0]["content"]
        assert "QA Engineer" in system
        assert "Respond in final form only" in system
        assert "Public URL: http://127.0.0.1:8090" in system
        assert calls[0]["max_tokens"] == 192
        assert calls[0]["thinking"] == {"type": "disabled"}
        assert data["usage"]["cached_tokens"] == 3
        assert data["usage"]["calls"] == 1 and data["usage"]["tokens"] == 20
        assert data["usage"]["cost"] is None
        assert data["jobs"][0]["status"] == "done"
        assert [step["step"] for step in reversed(data["job_steps"])] == [
            "queued",
            "context",
            "request",
            "response",
            "saved",
        ]


def test_monthly_call_stop_prevents_second_remote_request(tmp_path, password_hash):
    calls = []

    def handler(request):
        calls.append(1)
        return response()

    with running(tmp_path, password_hash, handler, {"monthly_call_limit": 1}) as (
        client,
        app,
    ):
        for text in ["First", "Second"]:
            client.post("/api/messages", json={"project_id": "default", "text": text})
        data = wait_for(
            client, lambda s: any(j["error_code"] == "budget_limit" for j in s["jobs"])
        )
        assert (
            len(calls) == 1
            and len([m for m in data["messages"] if m["sender"] == "owner"]) == 2
        )
        assert data["usage"]["calls"] == 1


def test_token_reservation_stops_before_network(tmp_path, password_hash):
    calls = []

    def handler(request):
        calls.append(1)
        return response()

    with running(tmp_path, password_hash, handler, {"monthly_token_limit": 1000}) as (
        client,
        app,
    ):
        client.post(
            "/api/messages",
            json={"project_id": "default", "text": "Long reasoning request"},
        )
        data = wait_for(
            client, lambda s: any(j["status"] == "paused" for j in s["jobs"])
        )
        assert calls == [] and data["usage"]["calls"] == 0


def test_paid_calls_switch_stops_new_work(tmp_path, password_hash):
    calls = []

    def handler(request):
        calls.append(1)
        return response()

    with running(tmp_path, password_hash, handler, {"paid_calls_enabled": False}) as (
        client,
        app,
    ):
        result = client.post(
            "/api/messages", json={"project_id": "default", "text": "Saved note"}
        )
        assert result.json()["queued"] is False
        data = client.get("/api/studio").json()
        assert (
            data["integrations"]["executor"] is False
            and data["messages"][0]["text"] == "Saved note"
        )
        assert calls == []


def test_provider_failure_is_not_retried_or_leaked(tmp_path, password_hash):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(429, json={"error": "private-upstream-body-do-not-leak"})

    with running(tmp_path, password_hash, handler) as (client, app):
        client.post("/api/messages", json={"project_id": "default", "text": "Hello"})
        data = wait_for(
            client, lambda s: any(j["status"] == "failed" for j in s["jobs"])
        )
        time.sleep(0.45)
        assert len(calls) == 1
        assert "private-upstream-body-do-not-leak" not in json.dumps(data)
        assert data["jobs"][0]["error_code"] == "http_429"


def test_common_reasoning_wrappers_are_not_saved_as_chat():
    raw = (
        "<thinking>private chain</thinking>\n"
        "Thinking Process:\nprivate deliberation\n"
        "Final Answer:\n**Aniq javob**"
    )
    assert clean_response_text(raw) == "**Aniq javob**"
    assert (
        clean_response_text("Qisqa javob.\n\n### Tahlil\nIchki mulohaza")
        == "Qisqa javob."
    )
    assert clean_response_text("Analysis:\nprivate reasoning") == ""


def test_reasoning_without_final_answer_is_rejected(tmp_path, password_hash):
    def handler(request):
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "<thinking>only</thinking>"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            },
        )

    with running(tmp_path, password_hash, handler) as (client, app):
        client.post("/api/messages", json={"project_id": "default", "text": "Hello"})
        data = wait_for(
            client, lambda s: any(j["status"] == "failed" for j in s["jobs"])
        )
        assert data["jobs"][0]["error_code"] == "reasoning_only_response"
        assert not any(
            message["sender"] == "supervisor" for message in data["messages"]
        )


def test_task_proposal_goes_to_review_never_claimed_done(tmp_path, password_hash):
    with running(tmp_path, password_hash, lambda r: response()) as (client, app):
        client.post(
            "/api/tasks",
            json={
                "project_id": "default",
                "title": "Implement login",
                "agent_id": "developer",
            },
        )
        data = wait_for(client, lambda s: s["tasks"][0]["status"] == "review")
        assert data["messages"][-1]["sender"] == "developer"
        assert data["tasks"][0]["status"] != "done"


def test_cancel_stops_active_task_without_late_reply(tmp_path, password_hash):
    async def delayed(request):
        await asyncio.sleep(10)
        return response()

    with running(tmp_path, password_hash, delayed) as (client, app):
        task = client.post(
            "/api/tasks", json={"project_id": "default", "title": "Cancel me"}
        ).json()["id"]
        wait_for(
            client,
            lambda s: s["tasks"][0]["status"] == "running" and s["usage"]["calls"] == 1,
        )
        assert client.post(f"/api/tasks/{task}/cancel").status_code == 200
        data = wait_for(client, lambda s: s["jobs"][0]["status"] == "cancelled")
        assert data["tasks"][0]["status"] == "cancelled"
        assert data["messages"] == []


def test_project_context_does_not_include_other_project(tmp_path, password_hash):
    prompts = []

    def handler(request):
        prompts.append(json.loads(request.content)["messages"])
        return response()

    with running(tmp_path, password_hash, handler) as (client, app):
        other = client.post("/api/projects", json={"name": "Other"}).json()["id"]
        client.post(
            "/api/messages",
            json={"project_id": other, "text": "UNIQUE_OTHER_PROJECT_DATA"},
        )
        client.post(
            "/api/messages", json={"project_id": "default", "text": "Default request"}
        )
        wait_for(client, lambda s: any(j["status"] == "done" for j in s["jobs"]))
        assert "UNIQUE_OTHER_PROJECT_DATA" not in json.dumps(prompts[-1])


def test_interrupted_job_is_paused_not_replayed(tmp_path, password_hash):
    app = create_app(
        tmp_path,
        password_hash,
        llm_transport=httpx.MockTransport(
            lambda r: pytest.fail("Restart must not replay paid calls")
        ),
    )
    key = (
        Fernet((tmp_path / "provider.key").read_bytes()).encrypt(b"synthetic").decode()
    )
    app.state.db.save_setting("provider", {"encrypted_key": key, "model": "test"})
    with app.state.db.connect() as conn:
        conn.execute(
            "INSERT INTO jobs VALUES ('interrupted','default','qa','message','ref','running',NULL,?,?)",
            (time.time(), time.time()),
        )
        conn.execute(
            "INSERT INTO llm_usage(id,job_id,agent_id,model,status,budget_tokens,created_at) VALUES ('u','interrupted','qa','test','reserved',2000,?)",
            (time.time(),),
        )
    with TestClient(app, base_url="http://127.0.0.1:8090") as client:
        result = client.post("/api/auth/login", json={"password": PASSWORD})
        data = client.get("/api/studio").json()
        assert (
            data["jobs"][0]["status"] == "paused"
            and data["jobs"][0]["error_code"] == "interrupted"
        )
        assert data["usage"]["reserved_and_measured_tokens"] == 2000


@pytest.mark.parametrize("kind", ["message", "task"])
def test_colleague_history_cannot_impersonate_assigned_agent(
    tmp_path, password_hash, kind
):
    app = create_app(tmp_path, password_hash)
    db = app.state.db
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO messages VALUES (?,?,?,?,?)",
            ("qa-context", "default", "qa", "UNRELATED_QA_DIRECTIVE", time.time()),
        )
        conn.execute(
            "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?)",
            (
                "task",
                "default",
                "Actual task",
                "Actual task requirements",
                "developer",
                "new",
                time.time(),
                time.time(),
            ),
        )
    _, messages = app.state.runtime.context(
        {
            "agent_id": "developer",
            "project_id": "default",
            "source_kind": kind,
            "reference_id": "task",
            "created_at": time.time() + 1,
        }
    )
    assert not any(
        m["role"] == "assistant" and "UNRELATED_QA_DIRECTIVE" in m["content"]
        for m in messages
    )
    if kind == "task":
        assert "UNRELATED_QA_DIRECTIVE" not in json.dumps(messages)
        assert "Actual task requirements" in messages[-1]["content"]
    else:
        assert any("Context from colleague qa" in m["content"] for m in messages)


def test_custom_provider_is_selected_without_deepseek_payload_or_secret_leak(
    tmp_path, password_hash
):
    calls = []

    def handler(request):
        assert request.url.host == "openrouter.ai"
        assert request.headers["Authorization"] == "Bearer only-for-alternate"
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "other-model"}]})
        body = json.loads(request.content)
        assert body["model"] == "other-model" and "thinking" not in body
        calls.append(body)
        return response()

    with running(tmp_path, password_hash, handler) as (client, _):
        path = "/api/providers/alternate"
        config = {
            "name": "Alternative",
            "api_key": "only-for-alternate",
            "model": "other-model",
        }
        assert (
            client.put(
                path, json={**config, "base_url": "https://127.0.0.1/v1"}
            ).status_code
            == 422
        )
        assert (
            client.put(
                path, json={**config, "base_url": "https://openrouter.ai/api/v1"}
            ).status_code
            == 200
        )
        assert client.post(path + "/test").json()["model_available"] is True
        assert (
            client.patch(
                "/api/agents/qa", json={"provider_id": "alternate"}
            ).status_code
            == 200
        )
        assert client.post(
            "/api/messages", json={"project_id": "default", "text": "@qa Salom"}
        ).json()["queued"]
        snapshot = wait_for(
            client, lambda state: any(m["sender"] == "qa" for m in state["messages"])
        )
        assert len(calls) == 1
        assert "only-for-alternate" not in json.dumps(snapshot)
        assert {p["id"] for p in snapshot["providers"]} == {"alternate", "deepseek"}
