# Uzbek / Andijon developer chat

225 synthetic scenarios, 45 per role: 175 Uzbek, 25 Russian, 25 mixed.
All three supplied keys were used against Google's Gemini API. The accepted
batches were generated with Gemini 3.5 Flash (117) and 3.6 Flash (108) using
HIGH thinking. The API advertised 3.7 and 3.8 Flash but generation returned
timeouts or HTTP 503. Per-record provenance states which model supplied the draft.

The checker validates shape and flags common problematic advice. Three sampled
replies were manually corrected and labeled. Remaining examples need human
review for accuracy and regional voice. Fifty scenarios are tagged for
evaluation, and the others are draft training candidates. This is a public
dataset, so the evaluation split is not suitable as a blind benchmark.

The runtime only ships a short curated role example per agent. The generated
replies remain available for offline evaluation and review.

Run structural checks without credentials:

    python dataset/check.py dataset/uz-andijan.jsonl

To regenerate, pass three keys via stdin:

    python dataset/generate.py path/to/output.jsonl

The generator resumes successful batches. Pass --fallback to run missing
batches on 3.5 or 3.6 Flash. Use only synthetic prompts.
