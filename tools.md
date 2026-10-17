# Second Story Studio - Logging Tools

Step 4 implements three tools in `business_tools.py`, with the same definitions embedded in `business_agent.ipynb`.

| Function | Purpose | Required arguments |
| --- | --- | --- |
| `record_customer_interest(email, name, message)` | Save a customer lead. | Email, name, and project/service notes. |
| `record_feedback(question)` | Save an unanswered business question. | The unanswered question. |
| `record_customer_feedback(feedback)` | Save customer feedback. | A complaint, suggestion, or explicitly requested feedback. |

## Shared logging behavior

Each function delegates to `_write_record`. It validates nonempty string inputs, performs a basic email plausibility check for leads, and appends a UTF-8 JSON line. Each record contains `timestamp_utc`, `record_type`, and the supplied fields. Leading and trailing whitespace are trimmed; other wording and internal newlines are preserved.

`LOG_DIR` defaults to `Path("logs")`, relative to the notebook/application working directory. The files are `leads.jsonl`, `unanswered_questions.jsonl`, and `customer_feedback.jsonl`. Existing records are preserved. Normal logs and `.env` are excluded by `.gitignore`.

All functions return exactly two fields: `success` (boolean) and `message` (string). Invalid inputs or a file/encoding failure return `success=False`. Success is returned only after the file write completes.

## Tool-call dispatch

`dispatch_tool_call(name, arguments)` accepts either an argument dictionary or a JSON string. It rejects unknown function names, invalid JSON, non-object arguments, and missing or extra keys. It executes only functions in the fixed tool registry. The model tool-call loop will use this dispatcher in the later agent-interaction step.

The tool does not decide whether a question is unknown or whether a customer wants follow-up. The agent and router decide the trigger and provide the appropriate arguments. Conversation logic also prevents duplicate submissions; these functions do not deduplicate identical text across different customers or sessions.

## Schemas and verification

`tool_schemas.json` contains the MCP-style names, short descriptions, required inputs, and expected outputs. The notebook embeds identical descriptors. These are contracts for local functions, not a running MCP server.

The notebook has executed demonstrations and nine focused tool tests, including checks that the function signatures match their schemas. `test_tools.py` can also run independently. Tests use temporary folders, and demonstration calls use synthetic records in `demo_logs/`. See `tool_demo.md` for actual results and sample data.

Step 5 assembles the system prompt, and Step 6 implements OpenAI interaction using the private key in `.env`. Live model/tool verification is pending API billing/credits. The Gradio interface remains Step 7.
