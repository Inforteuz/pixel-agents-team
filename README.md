# Pixel Team

Pixel Team is a private AI team studio with a pixel office, project chat,
and an optional five-bot Telegram bridge. Version 0.4 adds owner-only Telegram
routing, voice transcription, project memory, and per-agent usage.

Use the team review checkbox on a new web task for a bounded proposal review.
The Supervisor asks for missing requirements, or routes through up to two
relevant specialists and gives a summary. The board shows clarification
requests and accepts the owner's answer. The five role guides are versioned
in backend/skills. Team review uses the assigned providers’ JSON response mode.

An independent local web studio inspired by the top-down pixel office in
[Pixel Agents](https://github.com/pixel-agents-hq/pixel-agents). This application
does not import Ant Colony code, UI, runtime data, tools or provider drivers.
The security module carries forward the owner-access code authored in this chat.
All office furniture and characters are original Canvas pixel drawings; no
Pixel Agents sprite sheet, furniture pack or illustration is copied.

## Run locally

Python 3.11+ and Node.js 20.19+ or 22.12+ are required.

```bash
cd pixel-agents-team
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-dev.lock
cd web
npm ci
npm run build
cd ..
.venv/bin/python run.py
```

Open <http://127.0.0.1:8090>. The first launch generates a random local owner
password, saves its scrypt hash in private `.env`, and writes the password to
`data/local-password.txt` with mode 0600. Read that local file to sign in; do not
publish it. Sessions persist and can be revoked by signing out. Do not share the
password or add `.env` or `data/` to git. There is no default password.

To deliberately replace the owner password, stop the server, generate a new
scrypt hash with `backend.security.hash_password` in a local interactive Python
session, replace `PIXEL_ADMIN_PASSWORD_HASH` in private `.env`, and restart.
Changing the hash invalidates old sessions. Do not place raw passwords in argv.

## What works now

- Original top-down office: five characters, idle walks, selection labels,
  hand-drawn desks, bookshelves, lounge, kitchen and a sleeping cat.
- Office controls: pause/resume, grid, zoom and fullscreen where supported.
  Reduced-motion browser preference defaults the scene to paused.
- Five logical AI roles: Supervisor, Developer, QA Engineer, DevOps, Security.
  Agent model, persona, call limits, and enabled settings persist.
- Independent projects, per-project chat and task lists in SQLite with WAL,
  foreign keys and a versioned migration. Restart preserves messages and tasks.
- Task creation, assignment, pause, retry, cancellation, and explicit owner completion.
- Owner login, HttpOnly/SameSite cookies, CSRF/origin/Host checks, durable login
  throttling and sanitized audit events. No command execution or deployment API.
- DeepSeek remains the default. Add an OpenAI-compatible HTTPS provider in
  Settings, then assign a provider and optional model override per agent.
  Each credential is encrypted separately. The model-catalog test makes
  no completion request. Extra provider origins may be enabled by the operator
  via the space-separated PIXEL_PROVIDER_ORIGINS setting.
- Agent answers use rendered GFM Markdown and explicit no-chain-of-thought,
  concise-response rules. Reasoning wrappers are discarded before persistence.
- Agents receive the configured public URL, environment, server host/IP and a strict
  text-only capability boundary. They still cannot inspect or operate that server.
- Responsive layout with a mobile chat drawer and agent details.

## Telegram and voice

Create five bots with BotFather and add them to a private group or supergroup. The
Supervisor is the only polling bot. It needs privacy mode disabled by the owner
for regular group messages and voice notes. Leave privacy mode enabled for the
other four. Use dedicated bot tokens and remove any webhook from the Supervisor
before starting the poller.

Set these variables in the private service environment, never in the repository:

    TELEGRAM_ALLOWED_CHAT_ID=
    OWNER_TELEGRAM_USER_ID=
    TELEGRAM_PROJECT_ID=default
    TELEGRAM_QUIET_HOURS=1
    TELEGRAM_SOCIAL=0
    BOT_SUPERVISOR_TOKEN=
    BOT_DEVELOPER_TOKEN=
    BOT_QA_TOKEN=
    BOT_DEVOPS_TOKEN=
    BOT_SECURITY_TOKEN=
    PIXEL_TRANSCRIPTION_KEY=

Voice is optional. When configured, the group owner's OGG audio (up to 2 minutes,
12 calls per 24 hours) is sent to Gemini for transcription. The transcript is
saved as ordinary chat. The audio bytes are not retained by Pixel Team.
The Studio switch for paid AI calls also disables transcription. Use a key
authorized for audio, separate from the offline dataset generation.

Text can target a role with an alias such as @qa. Use @developer+qa for one
proposal followed by one QA reply. /task creates a task proposal, /pause pauses
the project's work, and /urgent bypasses quiet hours. Telegram file uploads are
available to the owner in Settings. ZIPs are size/path validated and stored
without extraction or execution.

Chat sends up to four recent excerpts plus the full current request, a short
style example and optional project notes to the assigned provider. Settings show
reported cache hits and per-agent usage. Paid calls and output are bounded.
See [dataset](dataset) for the synthetic Uzbek, Russian and mixed examples.

See [self hosting](docs/SELF_HOSTING.md) for separate partner installations and
read-only project context on each server.

## Current scope

Tasks produce text proposals for owner review. Automated execution, vision,
PR feedback to Telegram, and GitHub-driven or agent-driven deployment are
outside this release. CI runs independently on GitHub. No deployment job is
defined there.

## Develop and verify

For frontend hot reload, start the API on 8090, then run `npm run dev` in `web`.
Set local `APP_PUBLIC_URL` to the Vite origin while using the dev proxy so mutation
Origin checks match. Restore `http://127.0.0.1:8090` for the built frontend.

```bash
.venv/bin/python -m pytest tests -q
cd web
npm run build
```

`web/package-lock.json` and both hash-locked Python requirement files are checked
in. Browser acceptance checks were performed using the built frontend with local
API storage. No external accounts or API credentials are needed to verify it.

## Private data and deployment

Default data lives under `data/`; `PIXEL_DATA_DIR` can place it outside
an immutable release. Preserve both SQLite databases, their WAL state via a
consistent backup, and `provider.key`. The encryption key must be protected
separately from exported database backups. The startup script binds only loopback.

The current slice is deployed behind HTTPS as a dedicated unprivileged systemd
service with bounded memory/CPU, encrypted provider configuration, backup/restore
and rollback. The login and configuration encryption remain access controls, not a
sandbox. External code execution, GitHub automation and production deploy
actions are still deliberately unimplemented.
