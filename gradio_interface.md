# Step 7 - Gradio Interface

The assignment asks for a Gradio `ChatInterface` to demo the bot. `build_interface` creates that component inside a small `Blocks` layout, with Tala's business identity, a message box, topic shortcuts, and a New conversation button.

## How one message travels

`Customer -> ChatInterface -> respond(message, history, session) -> BusinessAgent.chat(message) -> reply`

The existing agent performs routing and model/tool interaction. Gradio supplies the visible chat history. A separate `gr.State` holds the full agent history, including tool requests and receipts, pending lead collection, and successful-call receipts. The API client and key are not stored in this state or returned to the browser.

Each page session receives its own state. The callback restores the relevant completed turn before handling the next message. Retry and undo can shorten visible history, so the callback restores the matching checkpoint while retaining successful logging receipts; removing a chat bubble does not delete a saved record. Exact identical tool calls are deduplicated, as in Step 6. Paraphrased calls still depend on the agent instructions to avoid duplicates.

New conversation clears visible messages, the ChatInterface history, pending lead state, and successful-call memory. It does not delete previously logged records. Refreshing starts a fresh chat. Browser history saving and Gradio feedback flagging are off; the agent's three business logging tools remain active. Quick topic buttons only fill the input; sending a message makes the API request.

## Run locally

From this project's folder, install the packages and launch the app:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:7860`. Leave the terminal running. Stop it with Ctrl+C.

The existing private `.env` remains beside `app.py`. The app loads `.env`, the prompt, and tool schemas relative to its own folder. Successful customer records are written to `logs/` in that same folder. Starting the app does not itself make an API request. The app listens only on the local computer and uses `share=False`.

For the notebook, run the earlier setup cells, then the Step 7 interface implementation and launch cell. Set `RUN_GRADIO = True` to launch it. Stop an existing app before launching another on port 7860. The notebook includes the interface code directly.

## Demo sequence

1. Ask the consultation price and duration; expect USD 25 for 20 minutes.
2. Ask for follow-up about an object; then provide a synthetic name and email. The agent should remember the earlier project description and record the lead.
3. Ask an unpublished policy question and suggest a workshop change. The two items should use their separate tools.
4. Start a new conversation and ask whether Tala knows your name. Details from the earlier conversation should be absent.

`test_gradio_interface.py` checks session isolation, complete tool-history retention, retry deduplication, undo, reset, and empty input using a fake client. It makes no paid requests.

## References

- [Gradio ChatInterface guide](https://gradio.app/guides/creating-a-chatbot-fast)
- [Gradio session state](https://gradio.app/guides/interface-state)
- [Official OpenAI function-calling documentation](https://developers.openai.com/api/docs/guides/function-calling)
