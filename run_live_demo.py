"""Run small live scenarios after OpenAI API billing is available.

Uses synthetic customer data and separate live_demo_logs. It stops on the first
API error rather than repeatedly making failing requests.
"""

import json
from pathlib import Path

import business_tools
from agent_interaction import BusinessAgent, create_openai_client


def run_live_demo(project_dir=None):
    root = Path(project_dir) if project_dir is not None else Path(__file__).resolve().parent
    client, model = create_openai_client(root / ".env")
    client = client.with_options(max_retries=0)
    descriptors = json.loads((root / "tool_schemas.json").read_text(encoding="utf-8"))
    prompt = (root / "system_prompt.txt").read_text(encoding="utf-8").strip()
    report = {"success": False, "scenarios": [], "data": "Synthetic demonstration customers only."}
    previous_log_dir = business_tools.LOG_DIR
    business_tools.LOG_DIR = root / "live_demo_logs"
    scenarios = [
        ("General question", ["What does a Second Story Consultation cost, and how long is it?"], set()),
        ("Lead with conversation memory", [
            "I'd like someone to contact me about redesigning an old chair while keeping its original wood carving.",
            "My name is Sam Demo and my email is sam@example.com.",
        ], {"record_customer_interest"}),
        ("Unanswered question and customer feedback", [
            "Do you offer a five-year warranty? Also, please add Sunday workshops.",
        ], {"record_feedback", "record_customer_feedback"}),
    ]
    try:
        for label, turns, expected_tools in scenarios:
            agent = BusinessAgent(client, prompt, descriptors, model)
            scenario = {"name": label, "turns": [], "success": False}
            report["scenarios"].append(scenario)
            seen_tools = set()
            for text in turns:
                reply = agent.chat(text)
                scenario["turns"].append({"user": text, "reply": reply, "route": agent.last_route["intent"], "tool_events": agent.last_tool_events, "success": agent.last_success, "error_type": agent.last_error, "error_code": agent.last_error_code})
                seen_tools.update(event["name"] for event in agent.last_tool_events if event["result"].get("success") is True)
                if any(event["result"].get("success") is not True for event in agent.last_tool_events):
                    scenario["note"] = "A model-selected tool did not complete successfully."
                    return report
                if not agent.last_success:
                    return report
            scenario["success"] = expected_tools == seen_tools
            if not scenario["success"]:
                scenario["note"] = "The successful model-selected tool calls did not match the expected actions."
                return report
        report["success"] = True
        return report
    finally:
        business_tools.LOG_DIR = previous_log_dir
        client.close()
        (root / "live_agent_demo.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    result = run_live_demo()
    print("Live demonstration succeeded:", result["success"])
    for scenario in result["scenarios"]:
        print(scenario["name"], "->", "passed" if scenario["success"] else "not completed")
