# Submission checklist

EECE 503P/798S — C3: Introduction to Agents  
Business: Second Story Studio · Agent: Tala · Student: Moustafa Jarjour

- **Repository:** https://github.com/MoustafaJarjour/Second-Story-Studio
- **Video:** [download demo/demo.mp4](https://github.com/MoustafaJarjour/Second-Story-Studio/raw/refs/heads/main/demo/demo.mp4), 4:54, with narration, captions, and embedded chapters
- **Public deployment:** https://huggingface.co/spaces/MoustafaJarjour/second-story-studio

| Assignment item | Submitted artifact / observed evidence | Video |
| --- | --- | --- |
| Business name, mission, services, team, unique value proposition | `me/business_summary.txt`, `me/summary.txt`, and two-page `me/about_business.pdf` | 00:00–00:52 |
| Main chatbot notebook | `business_agent.ipynb`, 22 code cells executed successfully with network/launch flags off | 00:25 and 04:18 |
| Clearly labelled persona and instructions | Separate notebook sections and `agent_identity.md` | 00:52 |
| Working three-intent router | `router.py`; actual route and handler names in `demo/evidence/events.json` | 01:18; live evidence from 01:46 |
| General question handling | Published consultation price and duration, no lead tool | 01:46 |
| Lead collection and short-term memory | Separate follow-up and contact turns; saved record retains the chair's carved back | 02:09 |
| `record_customer_interest(email, name, message)` | Real model-selected call, successful receipt, and `demo/evidence/leads.jsonl` | 02:09–03:01 |
| `record_feedback(question)` when the answer is unknown | Unpublished warranty question, successful receipt, and `demo/evidence/unanswered_questions.jsonl` | 02:36 |
| Short, documented MCP-style tool schemas | `tool_schemas.json`, `tools.md`; a third tool keeps ordinary feedback separate | 01:18 and 02:36 |
| System prompt uses persona, instructions, summary and PDF | `chat_setup.py`, notebook Step 5, and `system_prompt.txt` | 00:25–01:46 |
| OpenAI chat history and tool result loop | `agent_interaction.py` and notebook Step 6; real calls shown | 01:46–03:01 |
| Gradio ChatInterface | `gradio_interface.py` and `app.py`; real standalone chat demonstrated | 01:46 onward |
| API key in private `.env`, excluded from upload | `.env.example`, `.gitignore`; local run validated privately | 00:25 and 04:18 |
| Runs successfully | 52 passing offline tests; 22 notebook code cells; actual local and hosted model replies | 04:18, plus live demonstrations |
| Reflection bonus with draft and revised logs | `reflection.py`; all normal turns reviewed; clearly labelled controlled wrong draft corrected by the real model; `demo/evidence/reflections.jsonl` | 03:01 |
| Hugging Face deployment bonus | Running on ZERO, public Space, actual hosted workshop reply | 03:52 |
| Session reset (additional evidence) | New conversation does not know the previous fictional customer's name | 03:32 |

## Evidence integrity

All demonstrated customer data is fictional. The logs contain the model's actual arguments and tool results; tools were not manually forced. The reflection fixture is deliberately wrong and labelled as such. Local audit screens were captured after the corresponding interactions. The browser recording has condensed processing pauses and offline synthetic narration; on-screen replies and records are unchanged. English captions and exact narration are included in `demo/demo.en.vtt` and `demo/narration.json`.

Normal application logs and the real `.env` are excluded. Only assessment-specific synthetic data is submitted under `demo/evidence/`. A saved lead is a file record, not an email or confirmed booking. The Space's runtime disk is ephemeral. Lightweight reflection and the demonstration establish observed functionality, not perfect model behavior on every possible prompt or a guaranteed grade.

See `demo/video_plan.md` for the scenario plan, `demo/chapters.json` for precise chapter timing, and `demo/evidence/` for test, notebook, deployment, and video verification.
