# Gradio Interface - Verified Results

The local app was opened and exercised in the browser at http://127.0.0.1:7860. It uses Gradio 6.30.0 ChatInterface and the existing OpenAI agent. All 44 offline tests passed.

| Browser check | Observed result |
| --- | --- |
| Consultation shortcut and Send | Shortcut filled the input; sending returned USD 25 for 20 minutes. |
| Lead across two messages | After a shirt-to-cushion request, synthetic name/email details completed the lead. The JSONL record retained the earlier project context. |
| Unpublished warranty plus Sunday-workshop suggestion | An unanswered-question record and a separate customer-feedback record were written. Neither included unrelated contact details. |
| New conversation | Visible messages cleared. A subsequent name question returned that no name had been given in the new conversation. |

The interface was reset again and left open with an empty chat. `gradio_ui_check.json` records these checks. Browser test customer data is synthetic. Existing API billing supports the real requests made by this demonstration.

Four added offline tests exercise session isolation, full tool-history retention, exact-call deduplication during retry, undo checkpoints, reset, and rejection of empty input. They use fake model replies and do not call the API. Normal page sessions have separate memory; previously saved logging records remain when a chat is cleared.

Run `python app.py` after installing requirements, or use Step 7 in the notebook. The app is local with share=False. Keep the process running while chatting; stop it with Ctrl+C. See gradio_interface.md for details.
