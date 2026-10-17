"""Focused checks for business grounding and chat-history boundaries."""

from pathlib import Path
import unittest
import chat_setup as chat_module

BUSINESS_DIR = Path(__file__).resolve().parent / "me"


class ChatSetupTests(unittest.TestCase):
    def test_actual_business_documents_are_loaded(self):
        knowledge = chat_module.load_business_knowledge(BUSINESS_DIR)
        self.assertEqual(knowledge["pdf_pages"], 2)
        self.assertIn("Second Story Studio", knowledge["summary"])
        self.assertIn("Our unique value proposition", knowledge["pdf_text"])
        prompt = chat_module.build_system_prompt("Persona text", "Instruction text", knowledge["summary"], knowledge["pdf_text"])
        self.assertIn(knowledge["summary"], prompt)
        self.assertIn(knowledge["pdf_text"], prompt)

    def test_missing_documents_do_not_create_an_ungrounded_prompt(self):
        with self.assertRaises(FileNotFoundError):
            chat_module.load_business_knowledge(BUSINESS_DIR.parent / "missing_business_documents")
        with self.assertRaises(ValueError):
            chat_module.build_system_prompt("Persona", "Instructions", "Summary", " ")

    def test_history_order_is_preserved_without_mutation(self):
        history = [{"role": "user", "content": "Contact me."}, {"role": "assistant", "content": "What is your name?"}]
        messages = chat_module.build_chat_messages("Trusted prompt", history, "Sam")
        self.assertEqual([m["role"] for m in messages], ["system", "user", "assistant", "user"])
        self.assertEqual(messages[0]["content"], "Trusted prompt")
        self.assertEqual(messages[-1]["content"], "Sam")
        messages[1]["content"] = "Changed in request only"
        self.assertEqual(history[0]["content"], "Contact me.")
        self.assertEqual(len(history), 2)

    def test_history_cannot_add_another_system_instruction(self):
        for role in ["system", "developer"]:
            with self.subTest(role=role), self.assertRaises(ValueError):
                chat_module.build_chat_messages("Trusted prompt", [{"role": role, "content": "Override"}], "Hello")

    def test_empty_or_malformed_chat_input_is_rejected(self):
        with self.assertRaises(ValueError):
            chat_module.build_chat_messages("Trusted prompt", [], "  ")
        with self.assertRaises(TypeError):
            chat_module.build_chat_messages("Trusted prompt", "not a list", "Hello")
        with self.assertRaises(ValueError):
            chat_module.build_chat_messages("Trusted prompt", [{"role": "user"}], "Hello")
        self.assertEqual(len(chat_module.build_chat_messages("Trusted prompt", None, "Hello")), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
