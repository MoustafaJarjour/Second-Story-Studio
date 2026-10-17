"""Offline protocol checks. The fake model never calls the OpenAI API."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import agent_interaction as interaction
from chat_setup import build_chat_messages
from openai import OpenAIError

PROJECT_DIR = Path(__file__).resolve().parent
DESCRIPTORS = json.loads((PROJECT_DIR / "tool_schemas.json").read_text(encoding="utf-8"))


def tool_request(name, arguments, call_id="call_1"):
    return SimpleNamespace(id=call_id, type="function", function=SimpleNamespace(name=name, arguments=json.dumps(arguments)))


def model_response(text=None, calls=None):
    message = SimpleNamespace(content=text, tool_calls=calls, refusal=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason="tool_calls" if calls else "stop")])


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **request):
        self.requests.append(deepcopy(request))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


class AgentInteractionTests(unittest.TestCase):
    def make_agent(self, responses, dispatcher=None, **options):
        client = FakeClient(responses)
        dispatcher = dispatcher or Mock(return_value={"success": True, "message": "Recorded."})
        agent = interaction.BusinessAgent(client, "Trusted business prompt", DESCRIPTORS, dispatcher=dispatcher, **options)
        return agent, client, dispatcher

    def test_text_reply_and_session_memory(self):
        agent, client, dispatcher = self.make_agent([model_response("USD 25."), model_response("It is credited toward an approved project.")])
        self.assertEqual(agent.chat("What does the consultation cost?"), "USD 25.")
        agent.chat("Is the fee credited?")
        self.assertEqual(len(agent.history), 4)
        self.assertIn("USD 25.", [m["content"] for m in client.requests[1]["messages"]])
        self.assertEqual(client.requests[0]["messages"][0]["role"], "system")
        self.assertEqual(len(client.requests[0]["tools"]), 3)
        dispatcher.assert_not_called()

    def test_unknown_tool_result_is_returned_to_model(self):
        call = tool_request("record_feedback", {"question": "Five-year warranty?"})
        agent, client, dispatcher = self.make_agent([model_response(calls=[call]), model_response("I don't have confirmed warranty terms; your question was recorded.")])
        agent.chat("Do you offer a five-year warranty?")
        dispatcher.assert_called_once_with("record_feedback", call.function.arguments)
        receipt = client.requests[1]["messages"][-1]
        self.assertEqual(receipt["role"], "tool")
        self.assertEqual(receipt["tool_call_id"], "call_1")
        self.assertTrue(json.loads(receipt["content"])["success"])
        self.assertEqual(agent.last_route["intent"], "feedback_or_unanswered")
        self.assertEqual([m["role"] for m in agent.history], ["user", "assistant", "tool", "assistant"])

    def test_multiple_distinct_tool_calls_receive_separate_receipts(self):
        calls = [tool_request("record_feedback", {"question": "Warranty?"}, "q"), tool_request("record_customer_feedback", {"feedback": "Add Sundays."}, "f")]
        agent, client, dispatcher = self.make_agent([model_response(calls=calls), model_response("Both items were recorded.")])
        agent.chat("Do you offer a warranty? Please add Sunday workshops.")
        self.assertEqual(dispatcher.call_count, 2)
        receipts = [m for m in client.requests[1]["messages"] if m["role"] == "tool"]
        self.assertEqual([r["tool_call_id"] for r in receipts], ["q", "f"])

    def test_successful_lead_clears_pending_state_and_keeps_tool_history(self):
        call = tool_request("record_customer_interest", {"email": "sam@example.com", "name": "Sam", "message": "Chair redesign"})
        agent, _, _ = self.make_agent([model_response("What is your name and email?"), model_response(calls=[call]), model_response("Your interest was recorded.")])
        agent.chat("Contact me about my chair.")
        self.assertTrue(agent.pending_lead)
        agent.chat("Sam, sam@example.com")
        self.assertFalse(agent.pending_lead)
        self.assertTrue(agent.last_success)
        # The next request can include the full tool transcript without mutation.
        messages = build_chat_messages("Prompt", agent.history, "Thanks!")
        self.assertTrue(any(m["role"] == "tool" for m in messages))

    def test_failed_lead_is_not_marked_complete(self):
        call = tool_request("record_customer_interest", {"email": "sam@example.com", "name": "Sam", "message": "Chair"})
        dispatcher = Mock(return_value={"success": False, "message": "Unable to write log."})
        agent, client, _ = self.make_agent([model_response(calls=[call]), model_response("I couldn't record your interest.")], dispatcher)
        agent.chat("Contact me about my chair: Sam, sam@example.com.")
        self.assertTrue(agent.pending_lead)
        self.assertFalse(json.loads(client.requests[1]["messages"][-1]["content"])["success"])

    def test_successful_duplicate_request_does_not_execute_twice(self):
        first = tool_request("record_feedback", {"question": "Warranty?"}, "one")
        second = tool_request("record_feedback", {"question": " Warranty? "}, "two")
        agent, _, dispatcher = self.make_agent([model_response(calls=[first]), model_response(calls=[second]), model_response("Recorded.")])
        agent.chat("Do you offer a warranty?")
        self.assertEqual(dispatcher.call_count, 1)
        self.assertTrue(agent.last_tool_events[1]["deduplicated"])

    def test_tool_limit_stops_execution(self):
        first = tool_request("record_feedback", {"question": "First?"}, "one")
        second = tool_request("record_feedback", {"question": "Second?"}, "two")
        agent, client, dispatcher = self.make_agent([model_response(calls=[first]), model_response(calls=[second])], max_tool_rounds=1)
        agent.chat("A question?")
        self.assertEqual(dispatcher.call_count, 1)
        self.assertEqual(client.requests[-1]["tool_choice"], "none")
        self.assertEqual(agent.last_error, "ToolCallLimit")
        self.assertFalse(agent.last_success)

    def test_api_failure_preserves_completed_tool_receipts(self):
        call = tool_request("record_feedback", {"question": "Warranty?"})
        agent, _, _ = self.make_agent([model_response(calls=[call]), OpenAIError("private diagnostic sentinel")])
        reply = agent.chat("Do you offer a warranty?")
        self.assertNotIn("private diagnostic", reply)
        self.assertEqual(agent.last_error, "OpenAIError")
        self.assertTrue(any(m["role"] == "tool" for m in agent.history))
        self.assertFalse(agent.last_success)

    def test_env_loader_handles_blank_key_and_reads_without_printing(self):
        with TemporaryDirectory(prefix="agent-env-test-", dir=Path.cwd()) as folder:
            self.assertEqual(Path(folder).resolve().parent, Path.cwd().resolve())
            path = Path(folder) / ".env"
            path.write_text("OPENAI_API_KEY=\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                interaction.create_openai_client(path)
            path.write_text("OPENAI_API_KEY=fake-key-for-unit-test\nOPENAI_MODEL=gpt-4.1-mini\n", encoding="utf-8-sig")
            with patch.object(interaction, "OpenAI") as constructor:
                _, model = interaction.create_openai_client(path)
                self.assertEqual(model, "gpt-4.1-mini")
                self.assertEqual(constructor.call_args.kwargs["api_key"], "fake-key-for-unit-test")


if __name__ == "__main__":
    unittest.main(verbosity=2)
