"""Focused checks for Step 4. All records use temporary folders."""

from datetime import datetime, timezone
import json
import inspect
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import business_tools as tool_module


class ToolTests(unittest.TestCase):
    def setUp(self):
        # Keep temporary records inside the writable working directory.
        self.temp = TemporaryDirectory(prefix="tool-test-", dir=Path.cwd())
        self.assertEqual(Path(self.temp.name).resolve().parent, Path.cwd().resolve())
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "logs"
        self.log_patch = patch.object(tool_module, "LOG_DIR", self.directory)
        self.log_patch.start()
        self.addCleanup(self.log_patch.stop)

    def assert_result(self, result, success):
        self.assertEqual(set(result), {"success", "message"})
        self.assertIs(type(result["success"]), bool)
        self.assertIsInstance(result["message"], str)
        self.assertTrue(result["message"])
        self.assertEqual(result["success"], success)

    def records(self, filename):
        return [json.loads(line) for line in (self.directory / filename).read_text(encoding="utf-8").splitlines()]

    def test_each_tool_writes_its_own_record_type(self):
        cases = [
            ("record_customer_interest", {"email": "sam@example.com", "name": "Sam", "message": "Chair redesign"}, "leads.jsonl", "customer_interest"),
            ("record_feedback", {"question": "Do you offer a five-year warranty?"}, "unanswered_questions.jsonl", "unanswered_question"),
            ("record_customer_feedback", {"feedback": "Please add Sunday workshops."}, "customer_feedback.jsonl", "customer_feedback"),
        ]
        for name, arguments, filename, record_type in cases:
            with self.subTest(tool=name):
                result = tool_module.TOOL_FUNCTIONS[name](**arguments)
                self.assert_result(result, True)
                records = self.records(filename)
                self.assertEqual(len(records), 1)
                record = records[0]
                self.assertEqual(record["record_type"], record_type)
                for key, value in arguments.items():
                    self.assertEqual(record[key], value)
                self.assertEqual(datetime.fromisoformat(record["timestamp_utc"]).utcoffset(), timezone.utc.utcoffset(None))

    def test_append_preserves_previous_records(self):
        for question in ["First question?", "Second question?", "First question?"]:
            self.assert_result(tool_module.record_feedback(question), True)
        self.assertEqual([r["question"] for r in self.records("unanswered_questions.jsonl")], ["First question?", "Second question?", "First question?"])

    def test_unicode_newlines_and_quotes_round_trip_as_one_record(self):
        feedback = '  Please preserve my mother\u2019s pattern.\n\u0645\u0631\u062d\u0628\u0627 "Second Story"  '
        self.assert_result(tool_module.record_customer_feedback(feedback), True)
        records = self.records("customer_feedback.jsonl")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["feedback"], feedback.strip())

    def test_required_fields_must_be_nonempty_strings(self):
        cases = [
            ("record_customer_interest", {"email": "sam@example.com", "name": "Sam", "message": "Chair redesign"}),
            ("record_feedback", {"question": "Warranty question?"}),
            ("record_customer_feedback", {"feedback": "Add Sunday workshops."}),
        ]
        for name, valid in cases:
            for field in valid:
                for invalid in ["", " \n ", None, 123, True, []]:
                    arguments = dict(valid, **{field: invalid})
                    with self.subTest(tool=name, field=field, invalid=invalid):
                        self.assert_result(tool_module.TOOL_FUNCTIONS[name](**arguments), False)
        self.assertFalse(self.directory.exists())

    def test_email_plausibility_and_preservation(self):
        for email in ["sam", "sam@", "sam@example", "sam @example.com", "sam@@example.com"]:
            with self.subTest(email=email):
                self.assert_result(tool_module.record_customer_interest(email, "Sam", "Chair"), False)
        self.assertFalse(self.directory.exists())
        self.assert_result(tool_module.record_customer_interest("  Sam+chair@Example.com  ", " Sam ", " Chair "), True)
        record = self.records("leads.jsonl")[0]
        self.assertEqual(record["email"], "Sam+chair@Example.com")
        self.assertEqual(record["name"], "Sam")

    def test_write_failure_returns_failure(self):
        blocked = Path(self.temp.name) / "existing_file"
        blocked.write_text("keep this content", encoding="utf-8")
        with patch.object(tool_module, "LOG_DIR", blocked):
            self.assert_result(tool_module.record_feedback("Warranty?"), False)
        self.assertEqual(blocked.read_text(encoding="utf-8"), "keep this content")

    def test_dispatch_accepts_dictionary_and_json_arguments(self):
        self.assert_result(tool_module.dispatch_tool_call("record_feedback", {"question": "First?"}), True)
        self.assert_result(tool_module.dispatch_tool_call("record_feedback", '{"question": "Second?"}'), True)
        self.assertEqual([r["question"] for r in self.records("unanswered_questions.jsonl")], ["First?", "Second?"])

    def test_dispatch_rejects_invalid_calls_without_writing(self):
        cases = [
            ("unknown_tool", {"question": "Question?"}),
            (None, {}),
            ("record_feedback", "not JSON"),
            ("record_feedback", "[]"),
            ("record_feedback", None),
            ("record_feedback", {}),
            ("record_feedback", {"feedback": "Wrong field"}),
            ("record_feedback", {"question": "Question?", "extra": "Unexpected"}),
        ]
        for name, arguments in cases:
            with self.subTest(name=name, arguments=arguments):
                self.assert_result(tool_module.dispatch_tool_call(name, arguments), False)
        self.assertFalse(self.directory.exists())

    def test_documented_schemas_match_function_signatures(self):
        schemas = getattr(tool_module, "tool_schemas", None)
        if schemas is None:
            path = Path(tool_module.__file__).with_name("tool_schemas.json")
            schemas = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual({t["name"] for t in schemas["tools"]}, set(tool_module.TOOL_FUNCTIONS))
        for schema in schemas["tools"]:
            name = schema["name"]
            with self.subTest(tool=name):
                parameters = tuple(inspect.signature(tool_module.TOOL_FUNCTIONS[name]).parameters)
                self.assertEqual(parameters, tuple(schema["inputSchema"]["properties"]))
                self.assertEqual(set(parameters), set(schema["inputSchema"]["required"]))
                self.assertEqual(parameters, tool_module.TOOL_ARGUMENTS[name])
                self.assertEqual(set(schema["outputSchema"]["properties"]), {"success", "message"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
