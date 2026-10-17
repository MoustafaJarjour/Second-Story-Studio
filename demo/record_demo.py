"""Local recording companion: real Gradio chat plus synthetic-only audit evidence.

Run from the repository root: python demo/record_demo.py
Uses .env by default; --env-file may point to a private local file elsewhere.
The companion never serves credentials or arbitrary filesystem paths.
"""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Lock
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import business_tools
from agent_interaction import BusinessAgent, create_openai_client
from gradio_interface import build_interface, interface_theme
from reflection import make_reflector, reflect_reply


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=str(ROOT / ".env"))
    args = parser.parse_args()
    evidence = ROOT / "demo" / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    business_tools.LOG_DIR = evidence
    client, model = create_openai_client(args.env_file)
    prompt = (ROOT / "system_prompt.txt").read_text(encoding="utf-8").strip()
    schemas = json.loads((ROOT / "tool_schemas.json").read_text(encoding="utf-8"))
    reviewer = make_reflector(client, model, log_dir=evidence)
    events_path = evidence / "events.json"
    events = json.loads(events_path.read_text(encoding="utf-8")) if events_path.is_file() else []
    lock = Lock()

    def append_event(event):
        with lock:
            events.append(event)
            (evidence / "events.json").write_text(json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    class RecordingAgent(BusinessAgent):
        def chat(self, message):
            reply = super().chat(message)
            append_event({
                "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "kind": "live_chat", "user": message, "reply": reply,
                "route": deepcopy(self.last_route), "tools": deepcopy(self.last_tool_events),
                "reflection": deepcopy(self.last_reflection), "success": self.last_success,
            })
            return reply

    demo = build_interface(lambda: RecordingAgent(client, prompt, schemas, model, reflector=reviewer))
    demo.launch(server_name="127.0.0.1", server_port=7862, share=False,
                prevent_thread_lock=True, theme=interface_theme(), show_error=False,
                blocked_paths=[str(ROOT / ".env"), str(evidence)])

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *unused):
            pass

        def send(self, data, content_type="application/json"):
            if isinstance(data, (dict, list)):
                data = json.dumps(data, ensure_ascii=False).encode("utf-8")
            elif isinstance(data, str):
                data = data.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            route = urlparse(self.path).path
            if route == "/":
                return self.send((ROOT / "demo" / "viewer.html").read_bytes(), "text/html; charset=utf-8")
            if route in ["/profile-1.png", "/profile-2.png"]:
                return self.send((ROOT / "demo" / "assets" / route.lstrip("/")).read_bytes(), "image/png")
            if route == "/business.pdf":
                return self.send((ROOT / "me" / "about_business.pdf").read_bytes(), "application/pdf")
            if route == "/state":
                data = {"events": deepcopy(events), "logs": {}}
                for name in ["leads", "unanswered_questions", "customer_feedback", "reflections"]:
                    path = evidence / (name + ".jsonl")
                    data["logs"][name] = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.is_file() else []
                return self.send(data)
            allowed = {
                "/summary": "me/business_summary.txt", "/identity": "agent_identity.md",
                "/tools": "tool_schemas.json", "/router": "router.py",
                "/reflection": "reflection.py", "/notebook": "business_agent.ipynb",
                "/tests": "demo/evidence/test_results.txt",
                "/deployment": "demo/evidence/deployment.json",
            }
            if route in allowed:
                path = ROOT / allowed[route]
                return self.send(path.read_text(encoding="utf-8") if path.is_file() else "Pending verification", "text/plain; charset=utf-8")
            self.send_error(404)

        def do_POST(self):
            if urlparse(self.path).path != "/controlled-review":
                return self.send_error(404)
            # Clearly labelled fixed, deliberately wrong draft; never a customer fact.
            draft = "The consultation costs USD 80 and lasts one hour. Your appointment is confirmed for tomorrow."
            messages = [{"role": "system", "content": prompt},
                        {"role": "user", "content": "What does a consultation cost, and how long is it?"}]
            result = reflect_reply(client, model, messages, draft, log_dir=evidence)
            append_event({"kind": "controlled_reflection_test", "draft_source": "Deliberately flawed test input", "reflection": result})
            return self.send(result)

    server = ThreadingHTTPServer(("127.0.0.1", 8891), Handler)
    print("Recording companion: http://127.0.0.1:8891", flush=True)
    try:
        server.serve_forever()
    finally:
        demo.close()
        client.close()


if __name__ == "__main__":
    main()
