"""Focused checks for Step 3. Run with: python -m unittest -v test_router."""

import unittest
from router import GENERAL, LEAD, FEEDBACK, route_message, route_and_dispatch


class RouterTests(unittest.TestCase):
    def test_general_questions_do_not_collect_contact_details(self):
        for text in [
            "What does a consultation cost?", "Can you turn a shirt into a cushion cover?",
            "How much will my particular chair cost?", "How do I book a workshop?",
            "Do I have to book a consultation?", "How can I leave feedback?",
            "Your mission is interesting.", "I love your mission.", "Thanks, that was helpful!",
        ]:
            with self.subTest(text=text):
                plan = route_and_dispatch(text)
                self.assertEqual(plan["intent"], GENERAL)
                self.assertEqual(plan["candidate_tools"], ())

    def test_explicit_lead_requests(self):
        for text in [
            "Contact me about my old chair.", "I'd like to book a consultation.",
            "I want a consultation.", "Can I book a workshop?", "Please sign me up.",
            "I\u2019d like a quote for my chair.",
            "I would like to get a quote for my chair.",
        ]:
            with self.subTest(text=text):
                result = route_message(text)
                self.assertEqual(result.intent, LEAD)
                self.assertTrue(result.lead_active)

    def test_feedback_uses_its_own_tool(self):
        for text in [
            "Please add Sunday workshops.", "Please record that I loved the workshop.",
            "I have a complaint about the workshop.", "Your staff was rude.",
        ]:
            with self.subTest(text=text):
                plan = route_and_dispatch(text)
                self.assertEqual(plan["intent"], FEEDBACK)
                self.assertEqual(plan["candidate_tools"], ("record_customer_feedback",))

    def test_unknown_requires_an_explicit_knowledge_check(self):
        text = "Do you offer a five-year warranty?"
        self.assertEqual(route_message(text).intent, GENERAL)
        plan = route_and_dispatch(text, answer_available=False)
        self.assertEqual(plan["intent"], FEEDBACK)
        self.assertEqual(plan["candidate_tools"], ("record_feedback",))

    def test_active_lead_contact_reply(self):
        text = "Sam, sam@example.com"
        self.assertEqual(route_message(text).intent, GENERAL)
        self.assertEqual(route_message(text, pending_lead=True).intent, LEAD)
        self.assertEqual(route_message("Sam", pending_lead=True).intent, LEAD)

    def test_active_lead_can_ask_a_general_question(self):
        result = route_message("What are your opening hours?", pending_lead=True)
        self.assertEqual(result.intent, GENERAL)
        self.assertTrue(result.lead_active)
        self.assertFalse(result.collect_lead)

    def test_active_lead_does_not_treat_thanks_as_contact_details(self):
        result = route_message("Thanks!", pending_lead=True)
        self.assertEqual(result.intent, GENERAL)
        self.assertTrue(result.lead_active)

    def test_contact_decline_ends_collection(self):
        for text in [
            "Don't contact me.", "I am not interested in booking.",
            "I'd rather not share my email.", "No, thanks.",
            "No need to contact me.", "I don't want to be contacted.", "Please stop contacting me.",
        ]:
            with self.subTest(text=text):
                result = route_message(text, pending_lead=True)
                self.assertEqual(result.intent, GENERAL)
                self.assertFalse(result.lead_active)

    def test_scoped_negation_preserves_a_different_request(self):
        text = "I'm not interested in furniture, but I'd like to book a workshop."
        self.assertEqual(route_message(text).intent, LEAD)
        self.assertEqual(route_message("Don't contact me. Actually, I'd like to book a consultation.").intent, LEAD)
        self.assertEqual(route_message("I'd like to book a consultation. Actually, don't contact me.").intent, GENERAL)

    def test_mixed_lead_and_feedback_preserves_both_actions(self):
        plan = route_and_dispatch("I want a consultation, but please add Sunday workshops.")
        self.assertEqual(plan["intent"], LEAD)
        self.assertEqual(plan["secondary_intents"], (FEEDBACK,))
        self.assertEqual(plan["candidate_tools"], ("record_customer_interest", "record_customer_feedback"))

    def test_booking_information_does_not_hide_a_followup_request(self):
        plan = route_and_dispatch("How do I book a workshop, and please contact me about my chair?")
        self.assertEqual(plan["intent"], LEAD)
        self.assertTrue(plan["lead_active"])

    def test_project_details_are_not_customer_feedback(self):
        for text in [
            "Please add my email to the request: sam@example.com.",
            "Please include my mother's story in the project notes.",
        ]:
            with self.subTest(text=text):
                self.assertEqual(route_and_dispatch(text)["candidate_tools"], ())
                plan = route_and_dispatch(text, pending_lead=True)
                self.assertEqual(plan["intent"], LEAD)
                self.assertEqual(plan["candidate_tools"], ("record_customer_interest",))

    def test_mixed_unknown_and_feedback_preserves_distinct_tools(self):
        plan = route_and_dispatch("Do you offer a five-year warranty? Also, please add Sunday workshops.", answer_available=False)
        self.assertEqual(plan["intent"], FEEDBACK)
        self.assertEqual(plan["candidate_tools"], ("record_feedback", "record_customer_feedback"))

    def test_mixed_unknown_and_lead_preserves_both_actions(self):
        plan = route_and_dispatch("Do you offer a five-year warranty? Please contact me.", answer_available=False)
        self.assertEqual(plan["intent"], FEEDBACK)
        self.assertEqual(plan["secondary_intents"], (LEAD,))
        self.assertEqual(plan["candidate_tools"], ("record_customer_interest", "record_feedback"))

    def test_feedback_logging_can_be_declined(self):
        plan = route_and_dispatch("Don't record my feedback that I loved the workshop.")
        self.assertEqual(plan["candidate_tools"], ())

    def test_real_handler_dispatch(self):
        calls = []
        def handler(message, decision):
            calls.append((message, decision.intent))
            return "handler executed"
        result = route_and_dispatch("Contact me.", handlers={LEAD: handler})
        self.assertEqual(result, "handler executed")
        self.assertEqual(calls, [("Contact me.", LEAD)])

    def test_invalid_inputs(self):
        for message in ["", "   ", None]:
            with self.subTest(message=message), self.assertRaises(ValueError):
                route_message(message)
        with self.assertRaises(TypeError):
            route_message("Hello", pending_lead="yes")
        with self.assertRaises(TypeError):
            route_message("Hello", answer_available="unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
