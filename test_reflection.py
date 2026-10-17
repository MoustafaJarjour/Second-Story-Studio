"""Reflection, audit-log, and deployment-secret checks without API requests."""

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from openai import OpenAIError

from agent_interaction import BusinessAgent, create_openai_client
from reflection import make_reflector, reflect_reply
from test_agent_interaction import DESCRIPTORS, FakeClient, model_response, tool_request


def review_response(reply, issues=None):
    return model_response(json.dumps({"final_reply": reply, "issues": issues or []}))


class ReflectionTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory(prefix="reflection-test-", dir=Path.cwd())
        self.addCleanup(self.folder.cleanup)
        self.log_dir = Path(self.folder.name)
        self.messages = [{"role": "system", "content": "Consultations cost USD 25 for 20 minutes."},
                         {"role": "user", "content": "How much is a consultation?"}]

    def test_revision_is_logged_with_original_and_final(self):
        client = FakeClient([review_response("USD 25 for 20 minutes.", ["unsupported_fact"])])
        result = reflect_reply(client, "gpt-4.1-mini", self.messages, "USD 80 for one hour.", log_dir=self.log_dir)
        self.assertEqual(result["status"], "revised")
        self.assertTrue(result["log_success"])
        saved = json.loads((self.log_dir / "reflections.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(saved["original_draft"], "USD 80 for one hour.")
        self.assertEqual(saved["revised_reply"], "USD 25 for 20 minutes.")
        self.assertNotIn("tools", client.requests[0])
        self.assertEqual(len(self.messages), 2)  # Input conversation is not mutated.

    def test_correct_draft_is_approved_without_forced_rewrite(self):
        draft = "USD 25 for 20 minutes."
        result = reflect_reply(FakeClient([review_response(draft)]), "gpt-4.1-mini", self.messages, draft, log_dir=self.log_dir)
        self.assertEqual(result["status"], "approved")
        self.assertFalse(result["changed"])

    def test_failed_review_does_not_release_unchecked_draft(self):
        result = reflect_reply(FakeClient([OpenAIError("private diagnostic sentinel")]), "gpt-4.1-mini", self.messages, "Unsupported guarantee.", log_dir=self.log_dir)
        self.assertFalse(result["success"])
        self.assertNotEqual(result["revised_reply"], "Unsupported guarantee.")
        self.assertNotIn("private diagnostic", json.dumps(result))
        self.assertEqual(result["error_type"], "OpenAIError")

    def test_malformed_truncated_and_tool_responses_are_rejected(self):
        truncated = review_response("Incomplete")
        truncated.choices[0].finish_reason = "length"
        responses = [model_response("not JSON"), review_response(" "), truncated,
                     model_response(calls=[tool_request("record_feedback", {"question": "Q?"})])]
        for response in responses:
            with self.subTest(response=response):
                result = reflect_reply(FakeClient([response]), "gpt-4.1-mini", self.messages, "Draft", log_dir=self.log_dir)
                self.assertFalse(result["success"])

    def test_log_write_failure_is_reported(self):
        blocked = self.log_dir / "a_file"
        blocked.write_text("file, not directory", encoding="utf-8")
        result = reflect_reply(FakeClient([review_response("Checked.")]), "gpt-4.1-mini", self.messages, "Draft", log_dir=blocked)
        self.assertTrue(result["success"])
        self.assertFalse(result["log_success"])

    def test_only_final_reply_enters_memory_and_tools_are_not_repeated(self):
        call = tool_request("record_customer_interest", {"email": "ada@example.com", "name": "Ada", "message": "Cushion"})
        client = FakeClient([model_response(calls=[call]), model_response("Your appointment is confirmed."),
                             review_response("Your interest was recorded; an appointment is not yet confirmed.", ["unsupported_action_claim"])])
        dispatcher = Mock(return_value={"success": True, "message": "Customer interest recorded."})
        reviewer = make_reflector(client, "gpt-4.1-mini", log_dir=self.log_dir)
        agent = BusinessAgent(client, "Business prompt", DESCRIPTORS, dispatcher=dispatcher, reflector=reviewer)
        final = agent.chat("Please contact me about a cushion: Ada, ada@example.com.")
        self.assertTrue(agent.last_success)
        self.assertEqual(agent.history[-1]["content"], final)
        self.assertNotIn("Your appointment is confirmed.", [m["content"] for m in agent.history])
        self.assertTrue(any(m["role"] == "tool" for m in client.requests[-1]["messages"]))
        dispatcher.assert_called_once()
        self.assertFalse(agent.pending_lead)

    def test_integration_records_reflection_failure(self):
        client = FakeClient([model_response("Draft"), OpenAIError("failed")])
        agent = BusinessAgent(client, "Prompt", DESCRIPTORS, reflector=make_reflector(client, "gpt-4.1-mini", log_dir=self.log_dir))
        agent.chat("Hello")
        self.assertEqual(agent.last_error, "ReflectionFailed")
        self.assertFalse(agent.last_success)
        self.assertEqual(agent.last_reflection["status"], "failed")

    def test_space_environment_secret_works_without_env_file(self):
        missing = self.log_dir / "missing.env"
        with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-deployment-key", "OPENAI_MODEL": "gpt-4.1-mini"}), patch("agent_interaction.OpenAI") as constructor:
            _, model = create_openai_client(missing)
            self.assertEqual(model, "gpt-4.1-mini")
            self.assertEqual(constructor.call_args.kwargs["api_key"], "fake-deployment-key")


if __name__ == "__main__":
    unittest.main()
