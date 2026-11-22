"""Check JSONL structure and flag samples for human review."""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

RED_FLAGS = re.compile(
    r"docker system prune|chmod\s+777|--no-verify|verify\s*=\s*false|"
    r"(?:skip|o‘tkazib yubor).{0,40}(?:test|check)|"
    r"(?:men\s+)?(?:tekshirib bo‘ldim|tekshirib bo'ldik|deploy qildim)|"
    r"(?:AQ\.[A-Za-z0-9_-]{35,}|sk-[A-Za-z0-9_-]{20,})",
    re.IGNORECASE,
)
REQUIRED = {
    "scenario_id",
    "lang",
    "agent_role",
    "user_context",
    "input",
    "expected_style",
    "reference_reply",
    "constraints",
    "synthetic",
    "reviewed",
    "model",
    "effort",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()
    with args.dataset.open(encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream]
    assert len(rows) >= 200, "Expected at least 200 cases"
    assert len({row["scenario_id"] for row in rows}) == len(rows), "Duplicate ID"
    assert len({row["input"].casefold() for row in rows}) == len(rows), (
        "Duplicate input"
    )
    for row in rows:
        assert REQUIRED <= row.keys(), f"Missing fields in {row['scenario_id']}"
        assert row["synthetic"] is True and row["effort"] == "high"
        assert (
            row["lang"] in {"uz", "ru", "mixed"} and len(row["reference_reply"]) <= 420
        )
    print(f"{len(rows)} synthetic cases")
    for key in ("agent_role", "lang", "model"):
        print(dict(Counter(item[key] for item in rows)))
    flagged = [
        item["scenario_id"]
        for item in rows
        if RED_FLAGS.search(item["reference_reply"])
    ]
    print(f"Manual review flags ({len(flagged)}): {', '.join(flagged)}")


if __name__ == "__main__":
    main()
