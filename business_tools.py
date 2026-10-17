"""Step 4: local logging tools and a dispatcher for later model tool calls."""

from datetime import datetime, timezone
import json
from pathlib import Path
import re


# Relative to the notebook/application working directory; change if needed.
LOG_DIR = Path("logs")

RECORD_CONFIG = {
    "customer_interest": ("leads.jsonl", "Customer interest recorded."),
    "unanswered_question": ("unanswered_questions.jsonl", "Unanswered question recorded."),
    "customer_feedback": ("customer_feedback.jsonl", "Customer feedback recorded."),
}


def _result(success, message):
    return {"success": success, "message": message}


def _write_record(record_type, fields):
    """Validate and append one UTF-8 JSON record; never overwrite prior records."""
    cleaned = {}
    for field, value in fields.items():
        if not isinstance(value, str) or not value.strip():
            return _result(False, f"{field} must be a non-empty string.")
        cleaned[field] = value.strip()

    if record_type == "customer_interest" and not re.fullmatch(
        r"[^\s@]+@[^\s@]+\.[^\s@]+", cleaned["email"]
    ):
        return _result(False, "email must be a plausible email address.")

    filename, confirmation = RECORD_CONFIG[record_type]
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "record_type": record_type,
        **cleaned,
    }
    line = json.dumps(record, ensure_ascii=False) + "\n"
    try:
        # Validate encoding before opening the log so invalid text is not appended.
        line.encode("utf-8")
        directory = Path(LOG_DIR)
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / filename).open("a", encoding="utf-8", newline="") as log:
            log.write(line)
    except (OSError, UnicodeError):
        return _result(False, "The record could not be logged.")

    return _result(True, confirmation)


def record_customer_interest(email, name, message):
    """Record customer interest after name, email, and notes are provided."""
    return _write_record("customer_interest", {
        "email": email, "name": name, "message": message,
    })


def record_feedback(question):
    """Record a business question the available knowledge cannot answer."""
    return _write_record("unanswered_question", {"question": question})


def record_customer_feedback(feedback):
    """Record a customer complaint, suggestion, or explicit feedback request."""
    return _write_record("customer_feedback", {"feedback": feedback})


TOOL_FUNCTIONS = {
    "record_customer_interest": record_customer_interest,
    "record_feedback": record_feedback,
    "record_customer_feedback": record_customer_feedback,
}

TOOL_ARGUMENTS = {
    "record_customer_interest": ("email", "name", "message"),
    "record_feedback": ("question",),
    "record_customer_feedback": ("feedback",),
}


def dispatch_tool_call(name, arguments):
    """Execute a whitelisted tool using a dictionary or JSON argument string."""
    if not isinstance(name, str) or name not in TOOL_FUNCTIONS:
        return _result(False, "Unknown tool name.")

    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return _result(False, "Tool arguments must be valid JSON.")
    if not isinstance(arguments, dict):
        return _result(False, "Tool arguments must be an object.")

    expected = TOOL_ARGUMENTS[name]
    if set(arguments) != set(expected):
        return _result(False, "Required arguments are exactly: " + ", ".join(expected) + ".")

    return TOOL_FUNCTIONS[name](**arguments)
