# Run a separate Pixel Team for each partner

Each installation is single-owner. Use one Compose project, domain, data volume,
owner password and set of provider keys for each team. A partner can run it on
their own server with no dependency on your instance or credentials.

1. Clone the repository on the team's server.
2. Create a private .env (mode 0600) containing APP_ENV=production,
   APP_PUBLIC_URL=https://your-studio.example, and PIXEL_ADMIN_PASSWORD_HASH.
   Produce the scrypt hash with backend.security.hash_password from a local
   Python session after installing requirements. Enter the password via getpass.
3. Run docker compose up --build -d. Loopback port 8091 is the default.
   Set PIXEL_HOST_PORT to a free port if running more than one studio on a host.
4. Proxy the selected hostname using HTTPS to that loopback port, with the
   original Host header. Verify /health/ready and sign in.
5. Add the team’s own provider from Settings. Configure Telegram and voice only
   for that team's private group and owner, as described in the README.

Back up the team's volume with SQLite's backup API, preserving both databases
and the provider encryption key. Protect the environment file with the same
access restrictions as the credential backups.

## Give agents read-only project context

Create a project in Studio and get its id from /api/studio while signed in.
Prepare a short, sanitized Markdown brief on the partner's server at
project-briefs/<project-id>.md. Include relevant architecture, selected snippets
and confirmed decisions. Exclude secrets and data the assigned AI provider may
not receive. The app reads up to 8 KiB per brief. It also keeps each project's
editable notes and chat separately in its own SQLite database.

For Compose, create the project-briefs directory and make its files readable
to container UID 10001 without granting write access. Launch with:

    docker compose -f compose.yaml -f compose.project-briefs.yaml up --build -d

For systemd, set PIXEL_PROJECT_BRIEFS_DIR to a directory readable by the service
and keep that directory outside the writable data volume. Briefs apply on the
next job. Text supplied by the brief is quoted as project data.

Git/SSH credentials, Docker sockets and writable host directories should stay
outside Studio. An operator publishes selected project context. Agents return
proposals for owner review.
