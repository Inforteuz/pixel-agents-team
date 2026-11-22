"""Generate synthetic chat examples. Read three API keys on stdin, one per line."""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TOPICS = {
    "developer": (
        "debugging",
        "database migrations",
        "frontend state",
        "API contracts",
        "performance",
    ),
    "qa": (
        "regression",
        "reproducibility",
        "test reliability",
        "accessibility",
        "requirements",
    ),
    "devops": (
        "CI errors",
        "rollback",
        "backup restoration",
        "monitoring",
        "deployment approvals",
    ),
    "supervisor": (
        "friendly chat and spam",
        "file with no instructions",
        "conflicting demands",
        "prioritization",
        "handoff",
    ),
    "security": (
        "secret rotation",
        "permissions",
        "defensive code review",
        "dependency updates",
        "release blockers",
    ),
}
MODELS = (
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.8-flash",
)
BATCHES = [
    (MODELS[(i + j) % 4], role, cases, f"{role}-{j + 1}")
    for i, (role, topics) in enumerate(TOPICS.items())
    for j, cases in enumerate(topics)
]


def generate(batch, key):
    model, role, cases, batch_id = batch
    prompt = (
        f"Create 9 distinct synthetic user/assistant pairs for a professional {role}. "
        f"Scenarios: {cases}. Exact JSON array of objects with lang (uz, ru or mixed), prompt and answer strings. "
        "Use Latin Uzbek in most pairs, one Russian pair and one mixed ru/uz pair when natural. Use everyday developer chat, light natural Andijon "
        "speech where it fits. Avoid literary language, caricature, repeated filler, and "
        "forced dialect. Answers 1–3 short sentences; lead with the next best action, "
        "state uncertainty when needed and ask at most one relevant question. No chain of "
        "thought, exploits, actual credentials or claims of running tools. Vary situations. "
        "Use technical terms people actually say (log, diff, deploy, branch, test)."
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "thinkingConfig": {"thinkingLevel": "HIGH"},
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "lang": {"type": "STRING", "enum": ["uz", "ru", "mixed"]},
                        "prompt": {"type": "STRING"},
                        "answer": {"type": "STRING"},
                    },
                    "required": ["lang", "prompt", "answer"],
                },
            },
        },
    }
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
    )
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=75) as result:
                response = json.load(result)
            break
        except urllib.error.HTTPError as exc:
            if attempt or exc.code not in {429, 503}:
                raise
            time.sleep(3)
    candidate = response["candidates"][0]
    if candidate["finishReason"] != "STOP":
        raise ValueError(candidate["finishReason"])
    pairs = json.loads(
        "".join(
            p.get("text", "")
            for p in candidate["content"]["parts"]
            if not p.get("thought")
        )
    )
    return [
        {
            "scenario_id": f"{batch_id}-{i + 1:02}",
            "agent_role": role,
            "lang": p["lang"],
            "user_context": cases,
            "input": p["prompt"].strip(),
            "reference_reply": p["answer"].strip(),
            "expected_style": "qisqa, tabiiy, professional",
            "constraints": ["no made-up execution"],
            "synthetic": True,
            "reviewed": False,
            "model": model,
            "effort": "high",
            "batch": batch_id,
        }
        for i, p in enumerate(pairs)
        if 8 <= len(p["prompt"].strip()) <= 260
        and 12 <= len(p["answer"].strip()) <= 420
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--fallback", action="store_true")
    args = parser.parse_args()
    keys = [line.strip() for line in sys.stdin if line.strip()]
    if len(keys) != 3:
        parser.error("Provide exactly three keys on stdin")
    records = {}
    if args.output.exists():
        records = {
            r["input"].casefold(): r
            for r in map(json.loads, args.output.read_text().splitlines())
        }
    complete = {r["batch"] for r in records.values()}
    pending = [
        (i, batch) for i, batch in enumerate(BATCHES) if batch[3] not in complete
    ]
    if args.fallback:
        pending = [(i, (MODELS[i % 2], *batch[1:])) for i, batch in pending]
    from concurrent.futures import as_completed

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(generate, batch, keys[i % len(keys)]): batch
            for i, batch in pending
        }
        for future in as_completed(futures):
            model, role, _, batch_id = futures[future]
            try:
                pairs = future.result()
                for pair in pairs:
                    records.setdefault(pair["input"].casefold(), pair)
                temp = args.output.with_suffix(".tmp")
                temp.write_text(
                    "".join(
                        json.dumps(r, ensure_ascii=False) + "\n"
                        for r in sorted(
                            records.values(), key=lambda item: item["scenario_id"]
                        )
                    )
                )
                temp.replace(args.output)
                print(f"{batch_id}: {model}, {len(pairs)} examples", flush=True)
            except urllib.error.HTTPError as exc:
                print(
                    f"{batch_id}: {model}, upstream HTTP {exc.code}",
                    file=sys.stderr,
                    flush=True,
                )
            except (ValueError, KeyError, IndexError, OSError) as exc:
                print(
                    f"{batch_id}: {model}, {type(exc).__name__}",
                    file=sys.stderr,
                    flush=True,
                )
    return 0 if len(records) >= 200 else 1


if __name__ == "__main__":
    sys.exit(main())
