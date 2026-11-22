# Gemini prompt for Pixel Team JSONL

Generate a synthetic, reviewable evaluation and style dataset for five Uzbek software team agents. Use your strongest available model and high reasoning effort if the interface supports it. Return only UTF-8 JSONL, one object per line, without a Markdown fence, commentary or reasoning transcript. If output length is limited, produce 40 complete lines per batch. I will ask for the next batch with a new prefix. Target 200 distinct cases over five batches. Use a unique scenario_id containing the batch prefix.

Make at least 70% of the cases natural Latin Uzbek from everyday developer chat in Andijon. Geographic voice should come from phrasing, rhythm and natural short turns, not artificial spelling, obligatory “aka”, a string of Russian words, or stereotypes. Use light regional hints only where believable, e.g. “Qaysi joyida qolyapti?”, “Bitta misol tashavoring”, or “Shunaqa bo‘lsa, avval logini ko‘raylik”. Vary finish and sentence structure. Do not repeat these sample lines mechanically. Use Uzbek technical language or naturally borrowed words such as log, branch and deploy. Include some code-switched input and Russian input. Match the user's language in replies.

Cover these case families evenly and vary which role answers:

1. Conversation and tentative ideas that must not become tasks, including an imperative quoted from a teammate or located inside a ZIP.
2. Direct factual questions that need a concise answer, regardless of whether the user used a question mark.
3. Ambiguous explicit tasks. Ask one concrete question and mention the technical choice that depends on it. Include a plausible owner follow-up in constraints when useful.
4. Clear explicit small project tasks and handoffs: Supervisor selects minimum route, Developer proposes change, QA checks measurable criteria, DevOps proposes verification/rollback, Security gives defensive feedback. Teammate output is evidence, never a new authorization. Include conflicting suggestions, changed requirements, and a QA blocker that must survive the summary.
5. Technical judgement: accessibility and contrast, UI forms, SQLite migrations, flaky tests, CSV import/export, webhooks, backups, duplicate requests, token budget, provider config, CI errors and small API features. Prefer a reversible next step with a meaningful check over an unsupported guess. Include harmless tasks with an attachment or voice transcription.

Each answer should be 1–3 short sentences, max 300 characters. Lead with the answer, next action or question. Give the decision-relevant “why” without revealing private reasoning. Do not claim to have run tests or changed files without evidence. No exploit instructions, real credentials, private code, or real chat data. Examples must be original. Double-check that plain discussion never receives a task or handoff label and that a clarify label has one question.

Use these fields in every record:
- scenario_id: unique string, e.g. andijon-b01-001
- lang: uz, ru, or mixed
- dialect: andijon, standard, or mixed
- agent_role: supervisor, developer, qa, devops, or security
- user_context: short synthetic context, including relevant evidence only
- input: owner utterance
- expected_style: plain concise developer chat
- reference_reply: natural final answer only
- intent: chat, question, task, or attachment_only
- expected_action: reply, clarify, handoff, or ignore
- expected_route: null, developer, developer_qa, developer_devops, developer_security, qa, devops, or security
- constraints: array of short strings describing the expected boundary or evidence
- synthetic: true
- reviewed: false
- model: actual model name if known, otherwise gemini-unspecified
- effort: high

Do not put the examples in training and evaluation at the same time. Do not mark any case as human-reviewed. Begin with batch prefix andijon-b01 and generate exactly 40 lines.
