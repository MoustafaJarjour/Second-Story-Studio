"""Session and retry checks with a fake API client; no paid requests."""

import unittest
from unittest.mock import Mock

import gradio as gr

from agent_interaction import BusinessAgent
from gradio_interface import make_chat_handler, reset_session
from test_agent_interaction import DESCRIPTORS, FakeClient, model_response, tool_request


class GradioSessionTests(unittest.TestCase):
    def handler(self, responses):
        client = FakeClient(responses)
        dispatcher = Mock(return_value={"success": True, "message": "Recorded."})
        handler = make_chat_handler(lambda: BusinessAgent(
            client, "Business prompt", DESCRIPTORS, dispatcher=dispatcher,
        ))
        return handler, client, dispatcher

    def test_each_session_has_its_own_history_and_pending_lead(self):
        respond, client, _ = self.handler([
            model_response("Please share your name and email."),
            model_response("Hello, other customer."),
            model_response("Thanks, Sam."),
        ])
        first_message = "Contact me about my chair."
        reply, first = respond(first_message, [], None)
        self.assertTrue(first["turns"][0]["pending_lead"])
        _, second = respond("Hello", [], None)
        self.assertFalse(second["turns"][0]["pending_lead"])
        self.assertNotIn(first_message, [m["content"] for m in client.requests[1]["messages"]])
        history = [{"role": "user", "content": first_message}, {"role": "assistant", "content": reply}]
        _, continued = respond("Sam, sam@example.com", history, first)
        self.assertIn(first_message, [m["content"] for m in client.requests[2]["messages"]])
        self.assertEqual(len(first["turns"]), 1)  # Incoming state was not mutated.
        self.assertEqual(len(continued["turns"]), 2)

    def test_retry_keeps_success_receipt_without_repeating_log(self):
        call = tool_request("record_feedback", {"question": "Warranty?"})
        respond, client, dispatcher = self.handler([
            model_response(calls=[call]), model_response("Recorded."),
            model_response(calls=[call]), model_response("Recorded again in this reply."),
        ])
        _, state = respond("What is your warranty?", [], None)
        self.assertTrue(any(m["role"] == "tool" for m in state["turns"][0]["history"]))
        _, retried = respond("What is your warranty?", [], state)
        dispatcher.assert_called_once()
        self.assertEqual(len(retried["turns"]), 1)
        self.assertEqual(client.requests[2]["messages"][-1]["role"], "user")

    def test_undo_restores_matching_checkpoint(self):
        respond, client, _ = self.handler([
            model_response("First reply."), model_response("Removed reply."), model_response("New reply."),
        ])
        _, state = respond("First question", [], None)
        first_visible = [{"role": "user", "content": "First question"}, {"role": "assistant", "content": "First reply."}]
        _, state = respond("Removed question", first_visible, state)
        _, state = respond("Replacement question", first_visible, state)
        contents = [m["content"] for m in client.requests[-1]["messages"]]
        self.assertIn("First question", contents)
        self.assertNotIn("Removed question", contents)
        self.assertEqual(len(state["turns"]), 2)

    def test_reset_and_empty_input(self):
        self.assertEqual(reset_session(), ([], [], None, ""))
        respond, client, _ = self.handler([])
        with self.assertRaises(gr.Error):
            respond("   ", [], None)
        self.assertEqual(client.requests, [])


if __name__ == "__main__":
    unittest.main()
