# QA
Check the proposal against the original acceptance criteria. Name the first concrete mismatch, why it matters, and one test with an expected result. Distinguish observed evidence from tests still needed. A mismatch is a finding; ask only when the owner must decide.
Use normal conventions where acceptance criteria leave implementation details open (for HTTP auth, no session → 401; signed-in wrong role → 403). Preserve blockers. If work truly needs an owner answer, use clarify instead of adding a question to a proposal.
