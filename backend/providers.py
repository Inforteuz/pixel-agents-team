"""Provider selection, secret storage and OpenAI-compatible transport."""

import os
import re
from urllib.parse import urlsplit

import httpx

DEEPSEEK = {
    "id": "deepseek",
    "name": "DeepSeek",
    "adapter": "deepseek",
    "base_url": "https://api.deepseek.com",
}
BUILTIN_ORIGINS = {
    "https://api.openai.com",
    "https://openrouter.ai",
    "https://api.groq.com",
    "https://api.mistral.ai",
    "https://generativelanguage.googleapis.com",
}
PROVIDER_ID = re.compile(r"[a-z][a-z0-9-]{0,31}")


def validate_endpoint(value):
    endpoint = value.rstrip("/")
    parsed = urlsplit(endpoint)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    allowed = BUILTIN_ORIGINS | set(os.getenv("PIXEL_PROVIDER_ORIGINS", "").split())
    if (
        origin not in allowed
        or parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.query
        or parsed.fragment
        or not re.fullmatch(r"(?:/[a-zA-Z0-9_-]+)*", parsed.path)
    ):
        raise ValueError(
            "HTTPS Base URL ruxsat etilgan provayder manzili bo‘lishi kerak"
        )
    return endpoint


class Providers:
    def __init__(self, db, cipher, transport=None):
        self.db, self.cipher, self.transport = db, cipher, transport

    def configuration(self, provider_id):
        if provider_id == "deepseek":
            return {**self.db.setting("provider", {}), **DEEPSEEK}
        return self.db.setting(f"provider:{provider_id}", {})

    def public(self):
        with self.db.connect() as conn:
            ids = [
                row[0].split(":", 1)[1]
                for row in conn.execute(
                    "SELECT key FROM settings WHERE key LIKE 'provider:%' ORDER BY key"
                )
            ]
        result = []
        for provider_id in ["deepseek", *ids]:
            config = self.configuration(provider_id)
            result.append(
                {
                    **{
                        key: config.get(key, "")
                        for key in ("id", "name", "adapter", "base_url", "model")
                    },
                    "configured": bool(config.get("encrypted_key")),
                }
            )
        return result

    def connection(self, config, model):
        if config.get("adapter") != "deepseek":
            validate_endpoint(config["base_url"])
        return OpenAICompatible(
            config["base_url"],
            self.cipher.decrypt(config["encrypted_key"].encode()).decode(),
            model,
            config["adapter"] == "deepseek",
            self.transport,
        )


class OpenAICompatible:
    def __init__(self, base_url, key, model, deepseek, transport):
        self.base_url, self.model = base_url, model
        self.headers = {"Authorization": "Bearer " + key}
        self.deepseek, self.transport = deepseek, transport

    async def complete(self, messages, max_tokens, *, json_object=False):
        body = {"model": self.model, "messages": messages, "stream": False}
        if json_object:
            body["response_format"] = {"type": "json_object"}
        if self.deepseek:
            body.update(max_tokens=max_tokens, thinking={"type": "disabled"})
        else:
            body[
                "max_completion_tokens"
                if urlsplit(self.base_url).hostname == "api.openai.com"
                else "max_tokens"
            ] = max_tokens
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(90, connect=10),
            transport=self.transport,
            trust_env=False,
        ) as client:
            return await client.post(
                f"{self.base_url}/chat/completions", headers=self.headers, json=body
            )

    async def models(self):
        async with httpx.AsyncClient(
            timeout=10, transport=self.transport, trust_env=False
        ) as client:
            result = await client.get(f"{self.base_url}/models", headers=self.headers)
        result.raise_for_status()
        return {item["id"] for item in result.json()["data"]}

    @staticmethod
    def cached_tokens(usage):
        details = usage.get("prompt_tokens_details") or {}
        return int(
            usage.get("prompt_cache_hit_tokens") or details.get("cached_tokens") or 0
        )
