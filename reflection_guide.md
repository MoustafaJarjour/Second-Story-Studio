# Optional Bonus - Reflection Step

The normal agent produces a draft after its tool loop. Before returning that draft, a second, lightweight call checks it against the same persona, instructions, business references, conversation, and actual tool receipts. It returns a customer-ready final reply plus brief issue labels. This is a quality check, not a guarantee that every mistake will be caught.

`Customer -> router/model/tools -> draft -> reflection model -> final reply -> customer`

## What changed

`reflection.py` defines the reviewer prompt, structured result, and logging. `BusinessAgent._review_and_finish` runs it just before saving and returning a successful text reply. The customer sees only the final reply; conversation memory also keeps only that final text. Existing tool requests and receipts stay in memory.

The review checks unsupported prices or policies, missing lead details, false claims about actions, repeated questions, and persona/style. It uses the configured model, currently `gpt-4.1-mini`, for one additional call per successful drafted reply. It has no tools: the normal agent already handles those, and reviewing cannot repeat a logging action or undo an earlier one. If an action was missed, the editor must not claim it happened.

The review requests structured JSON with `final_reply` and `issues`. The application derives `changed` by comparing the actual strings. Correct drafts can be approved unchanged. A failed or invalid review returns a retry message instead of releasing the unchecked draft. API error messages and credentials are not logged. File-write failures are exposed through `agent.last_reflection["log_success"]`.

## Where to see the evidence

After a normal app conversation, open `logs/reflections.jsonl`. Each line contains:

- `original_draft`: what the first model was about to say.
- `revised_reply`: what the customer actually receives.
- `status`: approved, revised, or failed.
- `issues`: short labels, such as unsupported_fact.
- `changed`: whether the final text differs.
- UTC timestamp and sanitized error type, if relevant.

These are application records, not a transcript of hidden reasoning. Logs may include customer information in the replies, so they stay out of the deployment archive.

## Try it yourself

1. Open the local chat after restarting the app. Reflection is enabled by default in `app.py`.
2. Ask the consultation price. Open `logs/reflections.jsonl` and compare the last original/final pair. It is valid for both to match if the draft was correct.
3. Ask for team follow-up about an old shirt without giving your contact details. Check that the final reply asks for missing details without inventing a booking or response deadline.
4. Open `reflection_demo.md` for a readable demonstration of a correct draft and two visible corrections.

For the notebook, run the new Step 8 reviewer cell, then the saved-results cell. To launch the reflective version, set `RUN_REFLECTIVE_CHAT = True` in its final cell. The earlier Step 7 launch demonstrates the baseline version.

## Make self-correction visible in the assignment video

Show `reflection_demo.md`. Explain that the first example uses a normally generated draft. The other two examples deliberately supply flawed drafts to test the reviewer: USD 80/one hour instead of USD 25/20 minutes, and an unsupported confirmed appointment/tomorrow promise. Their reviews are actual model outputs, not fabricated corrections.

You can regenerate them with `python run_reflection_demo.py`. This makes paid API requests and writes synthetic examples to `reflection_demo_logs/reflections.jsonl`, plus readable `reflection_demo.md` and structured `reflection_demo.json`. Do not force a wrong price into the real business prompt just to obtain a natural mistake.

The eight new offline tests cover unchanged and revised replies, visible logs, review failures, malformed responses, failed writes, final-only memory, preserved tool receipts, and deployment secrets. All 52 project tests passed after integration.

Reference: [official OpenAI Chat Completions documentation](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).
