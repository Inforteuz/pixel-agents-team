# Team review and light theme verification

A regular chat turn does not open a task. Start a team review with the web
task checkbox or Telegram /task without a specific agent. An explicit
Telegram @qa /task request goes to QA alone. /pause and /stop are commands.
Each team stage receives the owner's request and any explicit clarification.
Earlier proposals are labeled as reference data. The backend accepts only
known routes and up to two specialists. Completion remains an owner action.

For the synthetic inventory CSV exercise, DeepSeek was tested in a separate
temporary database. The Supervisor asked who could export before assigning
work. Once the owner clarified admin-only access, Developer proposed a filtered
UTF-8 CSV and QA covered pagination independence, special characters, empty
results and authorization before the Supervisor summarized the proposal.
The first live structured response failed validation before JSON mode was added.
In the first complete attempt, the model assumed BOM support and asked about
401/403 unnecessarily. The revised guides removed the BOM assumption and QA
used 401 for unauthenticated and 403 for signed-in non-admin. Some replies
remained longer than desired. Plans and test criteria were reviewed, but the
exercise did not execute a CSV feature or its tests.

Light theme automated color-contrast checks were run in Chromium against
login, office, focused chat, team, settings, task dialog, task board and mobile
focused chat. Team identity text, login metadata and the task dialog note
required follow-up corrections. Contrast checks reported no violations on
those eight audited states. The browser test also exercised answering a
clarification and seeing the task proceed without horizontal overflow at 390px.
