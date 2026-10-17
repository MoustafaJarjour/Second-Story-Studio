# Step 5 - System Prompt and Chat Setup

`chat_setup.py` defines three helpers, also embedded in the notebook:

1. `load_business_knowledge(me_dir="me")` reads `business_summary.txt` and extracts text from `about_business.pdf`. Missing files or empty extracted knowledge raise a clear error.
2. `build_system_prompt(persona, instructions, business_summary, pdf_text)` combines the four components into one labeled prompt and distinguishes reference facts from operating instructions.
3. `build_chat_messages(system_prompt, history, user_message)` creates a fresh request list in the order system prompt, prior user/assistant turns, latest user message. It keeps stored history unchanged and prevents history from introducing another system/developer message.

## Notebook setup

Keep the `me/` folder in the notebook's working directory and install the packages listed in `requirements.txt` if needed. The notebook defines `business_knowledge`, `business_summary`, `pdf_text`, `system_prompt`, and an initially empty `chat_history` for each session. The demo uses a separate synthetic history.

`system_prompt.txt` is a generated snapshot for review. Regenerate it after changing the persona, instructions, or business documents. The full text of both small knowledge files is included, so no embedding database or search service is needed here.

## API connection

This step prepares chat turns. Step 6 now implements the OpenAI request and tool-call loop in `agent_interaction.py`. The history helper supports assistant tool requests and tool results as well as ordinary text, while rejecting system/developer messages from stored history. The real key is loaded from `.env`; live verification is pending API billing/credits. A prompt instruction to call a tool does not replace registering and executing it through model interaction.

The role dictionaries are passed to the OpenAI Chat Completions request by the Step 6 adapter. Five focused setup checks and an executed setup demo are included in the notebook and `test_chat_setup.py`. These verify setup mechanics, not model behavior.

See [official OpenAI prompt-engineering guidance](https://developers.openai.com/api/docs/guides/prompt-engineering) for structured instructions and reference context.
