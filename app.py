"""Run from a terminal with: python app.py"""

import json
import os
from pathlib import Path

# ZeroGPU startup registration only; chat and reflection stay on OpenAI.
# This private function is never called or attached to a Gradio event.
if os.environ.get("SPACES_ZERO_GPU", "").lower() in {"1", "t", "true"}:
    import spaces

    # Keep all real Gradio callbacks on CPU, even if automatic wrapping is enabled.
    spaces.disable_gradio_auto_wrap()

    @spaces.GPU(duration=1)
    def _zerogpu_startup_marker():
        return None


import business_tools
from agent_interaction import BusinessAgent, create_openai_client
from gradio_interface import build_interface, interface_theme
from reflection import make_reflector


def create_app(project_dir=None, *, enable_reflection=True):
    root = Path(project_dir) if project_dir is not None else Path(__file__).resolve().parent
    prompt = (root / "system_prompt.txt").read_text(encoding="utf-8").strip()
    descriptors = json.loads((root / "tool_schemas.json").read_text(encoding="utf-8"))
    client, model = create_openai_client(root / ".env")
    business_tools.LOG_DIR = root / "logs"
    reviewer = make_reflector(client, model, log_dir=root / "logs") if enable_reflection else None
    try:
        demo = build_interface(lambda: BusinessAgent(client, prompt, descriptors, model, reflector=reviewer))
    except Exception:
        client.close()
        raise
    return demo, client


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent
    demo, api_client = create_app(project_root)
    try:
        demo.launch(
            server_name="0.0.0.0" if os.environ.get("SPACE_ID") else "127.0.0.1",
            server_port=7860, share=False,
            theme=interface_theme(),
            blocked_paths=[str(project_root / ".env"), str(project_root / "logs")],
            show_error=False,
        )
    finally:
        demo.close()
        api_client.close()
