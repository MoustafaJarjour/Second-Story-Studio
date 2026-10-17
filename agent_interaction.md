# Step 6 - Agent Interaction

## Key setup

The private `.env` belongs beside the notebook, with `OPENAI_API_KEY` and `OPENAI_MODEL`. The supplied model defaults to `gpt-4.1-mini`. Keep the key in that local file; `.env.example` is the empty sharing template, and `.gitignore` excludes the real file. Install `requirements.txt` before running the notebook.

`create_openai_client` loads the key privately with `python-dotenv` and creates the OpenAI client. It sends requests to the official OpenAI API endpoint. Standard API billing is separate from ChatGPT Plus subscription usage. Client creation does not itself make a paid request.

## Interaction loop

Create one `BusinessAgent` per customer session. `chat(message)` classifies the message, invokes the matching router handler, and adds its application-derived guidance to the system prompt. It passes full conversation history and three function definitions to `client.chat.completions.create`.

If the model returns text, the agent returns it. If the model requests a function, the dispatcher validates and executes it, and the agent appends a tool result with the matching call ID before requesting the next model response. Tools use automatic selection; logging is not forced by hard-coded calls. Unanswered-question tool requests re-route to feedback/unanswered handling before execution.

History includes user messages, assistant requests, tool receipts, and final replies. Successful lead records clear pending lead collection. Successful identical tool arguments are deduplicated within the session; failed calls can be retried. A fixed number of tool rounds bounds each turn.

`last_route`, `last_tool_events`, `last_success`, and sanitized error fields provide demo evidence. Raw API exceptions, request headers, and credentials are not printed. API failures preserve any tool results already obtained.

## Verification

All 40 offline checks pass, including nine interaction checks using a fake client. After credits were added, all three real API scenarios passed: published business Q&A, lead collection across two turns, and separate logging of an unanswered question and a customer suggestion. Successful tool receipts were checked against the actual JSONL records. See `live_agent_demo.json` for the observed replies and tool arguments. These are demonstration checks, not a guarantee for every possible conversation.

`run_live_demo.py` exercises a known question, lead collection across two turns, and a mixed unknown question/customer suggestion. It writes only synthetic customer records to `live_demo_logs/` and stops on the first API failure.

## Official references

- [Function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [GPT-4.1 Mini endpoints and tool support](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
- [Subscription and API pricing](https://learn.chatgpt.com/docs/pricing)
- [API error codes](https://developers.openai.com/api/docs/guides/error-codes)

The notebook shows saved live results. Its fresh-request flag remains off by default to avoid spending credits whenever all cells are rerun. Set it to True deliberately to make another API request.

Lead guidance now records a complete request as soon as name, email, and brief interest are present anywhere in the conversation. Unknown policies remain unanswered questions even when the profile says their terms are unpublished; separate suggestions use the customer-feedback tool.
