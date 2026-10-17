# Demonstration plan and rubric coverage

The video is a browser-only screen recording of real interactions and evidence. It uses a local Gradio companion with the same agent code as the deployed Space, then shows the hosted app separately. All contacts are fictional. Waiting time may be condensed; narration uses an offline synthetic voice.

| Chapter | What to show | Requirement demonstrated |
| --- | --- | --- |
| Overview | Business purpose and agent flow | Coherent business assistant |
| Business files | Actual summary, PDF preview, notebook and setup files | Required artifacts and business knowledge |
| Identity | Separate persona and instruction excerpts | Clearly labelled identity components |
| Router and tools | Three intents, classifier/dispatch distinction, actual MCP-style schemas | Working router and documented tools |
| General question | Consultation price/duration and route evidence; no lead tool | Grounded answering and correct routing |
| Lead and memory | Request follow-up, then supply fictional name/email in a separate message | Short-term memory and record_customer_interest |
| Unknown question and suggestion | Ask unpublished warranty plus Sunday-workshop suggestion; inspect real records and successful receipts | record_feedback and separate record_customer_feedback |
| Reflection | Deliberately flawed test draft reviewed by the real model; original/final shown | Logged self-correction bonus |
| Reset | New conversation, then ask whether the prior name is known | Session reset and privacy |
| Hosted app | Actual Hugging Face app and a real answer | Deployment bonus |
| Checks and conclusion | Actual test output, deployment revision, reproducibility, private-key handling | Runs successfully and submission completeness |

## Exact fictional-customer sequence

1. What does a Second Story Consultation cost, and how long is it?
2. I'd like the team to contact me about redesigning an old chair while keeping its carved back.
3. My name is Dana Demo and my email is dana.demo@example.com.
4. Do you offer a five-year warranty? Also, please add Sunday workshops.
5. Inspect demo/evidence/leads.jsonl, unanswered_questions.jsonl, and customer_feedback.jsonl.
6. Run the labelled controlled reflection test. The supplied wrong draft is a test fixture; the correction is an actual model output.
7. Start a new conversation. Ask: Do you know my name from this conversation?
8. Show the public hosted app and ask a business question.

## Evidence and limits

The companion records actual routing plans, model-selected tool calls, tool success receipts, draft/final reflection pairs, and the revised customer reply. It does not force the tools to fire. It serves a fixed allowlist of public project files; neither .env nor arbitrary local paths are exposed. Runtime data in demo/evidence is synthetic and intentionally included for assessment. Normal customer logs remain ignored.

The recording demonstrates observed behavior; it does not guarantee every possible model reply or a particular grade. A recorded lead is not a booking or an email sent. The rubric checklist in the repository maps each requirement to source and evidence.
