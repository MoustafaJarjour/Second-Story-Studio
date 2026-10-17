"""Step 6: OpenAI chat interaction with session memory and model-selected tools."""

from copy import deepcopy
import json
import os
from pathlib import Path

from dotenv import dotenv_values
from openai import OpenAI, OpenAIError

from business_tools import dispatch_tool_call
from chat_setup import build_chat_messages
from router import route_and_dispatch


def create_openai_client(env_path=".env"):
    """Read a local .env or deployment secret without printing the key."""
    path = Path(env_path)
    config = dotenv_values(path, encoding="utf-8-sig", interpolate=False) if path.is_file() else {}
    key = (os.environ.get("OPENAI_API_KEY", config.get("OPENAI_API_KEY")) or "").strip()
    if not key or key in {"your_openai_key_here", "paste_your_key_here"}:
        raise ValueError("Set OPENAI_API_KEY in .env or as a deployment secret.")
    model = (os.environ.get("OPENAI_MODEL", config.get("OPENAI_MODEL")) or "gpt-4.1-mini").strip()
    client = OpenAI(api_key=key, base_url="https://api.openai.com/v1", timeout=30.0, max_retries=1)
    return client, model


def make_openai_tools(descriptors):
    """Adapt the MCP-style contracts to Chat Completions function definitions."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": deepcopy(tool["inputSchema"]),
                "strict": True,
            },
        }
        for tool in descriptors["tools"]
    ]


class BusinessAgent:
    """Create one instance per chat session; the client may be shared."""

    def __init__(self, client, system_prompt, descriptors, model="gpt-4.1-mini", *, dispatcher=dispatch_tool_call, max_tool_rounds=4, reflector=None):
        if not isinstance(max_tool_rounds, int) or not 1 <= max_tool_rounds <= 8:
            raise ValueError("max_tool_rounds must be an integer from 1 to 8")
        self.client = client
        self.model = model
        self.system_prompt = system_prompt
        self.tools = make_openai_tools(descriptors)
        self.dispatcher = dispatcher
        self.max_tool_rounds = max_tool_rounds
        self.history = []
        self.pending_lead = False
        self.last_route = None
        self.last_tool_events = []
        self.last_error = None
        self.last_error_code = None
        self.last_success = False
        self.reflector = reflector
        self.last_reflection = None
        self._successful_calls = {}

    def _tool_result(self, name, arguments):
        try:
            parsed = json.loads(arguments)
        except (json.JSONDecodeError, TypeError):
            parsed = None
        fingerprint = None
        if isinstance(parsed, dict):
            normalized = {key: value.strip() if isinstance(value, str) else value for key, value in parsed.items()}
            fingerprint = (name, json.dumps(normalized, sort_keys=True, ensure_ascii=False))
        if fingerprint is not None and fingerprint in self._successful_calls:
            return deepcopy(self._successful_calls[fingerprint]), parsed, True
        result = self.dispatcher(name, arguments)
        if result.get("success") is True and fingerprint is not None:
            self._successful_calls[fingerprint] = deepcopy(result)
        return result, parsed, False

    def _finish(self, messages, reply, success):
        messages.append({"role": "assistant", "content": reply})
        # Retain user turns, assistant tool requests, tool receipts, and replies.
        self.history = deepcopy(messages[1:])
        self.last_success = success
        return reply

    def _review_and_finish(self, messages, draft):
        if self.reflector is None:
            return self._finish(messages, draft, True)
        self.last_reflection = self.reflector(messages, draft)
        if not self.last_reflection["success"]:
            self.last_error = "ReflectionFailed"
        # Only the final customer-facing text enters conversation memory.
        return self._finish(messages, self.last_reflection["revised_reply"], self.last_reflection["success"])

    def chat(self, user_message):
        """Route, ask the model, execute its requested tools, and return a reply."""
        self.last_route = route_and_dispatch(user_message, pending_lead=self.pending_lead)
        self.pending_lead = self.last_route["lead_active"]
        self.last_tool_events = []
        self.last_error = None
        self.last_error_code = None
        self.last_success = False
        self.last_reflection = None

        # Include only application-derived routing facts here, not raw user text.
        route_context = {
            "intent": self.last_route["intent"],
            "secondary_intents": self.last_route["secondary_intents"],
            "handler": self.last_route["handler"],
            "actions": self.last_route["actions"],
            "lead_active": self.pending_lead,
        }
        turn_prompt = self.system_prompt + "\n\n# Current handling guidance\n" + json.dumps(route_context)
        turn_prompt += "\nThe route is advisory. Inspect the full message and business knowledge. All three registered tools remain available for mixed requests and questions the knowledge cannot answer. Use tool results before claiming an action succeeded."
        turn_prompt += "\nBefore replying, complete these applicable actions: call record_feedback for a business question with no confirmed answer in the references; call record_customer_feedback for a concrete complaint or suggestion; call record_customer_interest when a requested follow-up has a customer-provided name, email, and brief interest anywhere in the conversation. Perform each distinct applicable action, then respond using its result. Do not ask for extra permission to record an unanswered question or an already-provided suggestion."
        turn_prompt += "\nA policy being unpublished means its answer is unknown, not that the policy or service does not exist. Saying 'not published' does not remove the requirement to call record_feedback for that question. Keep unknown questions out of record_customer_feedback. For example, an unanswered delivery-policy question plus a request for evening workshops requires two separate calls: record_feedback for delivery and record_customer_feedback for the workshop suggestion. Appointment opening hours do not establish workshop dates; workshop availability is confirmed by the team."
        if self.last_route["lead_active"]:
            turn_prompt += "\nCheck the full conversation for the customer's name, email, and brief project or service interest. If all are present and the customer wants follow-up, call record_customer_interest now. Further design or condition details are optional; ask only when a required field is missing."
            turn_prompt += "\nExample: a customer requests follow-up about turning a shirt into a cushion; you ask for their name and email; they provide both in the next message. The correct next action is record_customer_interest using the earlier shirt-to-cushion interest as message, not another question about the project."
        messages = build_chat_messages(turn_prompt, self.history, user_message)

        for round_index in range(self.max_tool_rounds + 1):
            at_limit = round_index == self.max_tool_rounds
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tools,
                    tool_choice="none" if at_limit else "auto",
                    parallel_tool_calls=False,
                    max_completion_tokens=700,
                    store=False,
                )
            except OpenAIError as error:
                self.last_error = type(error).__name__  # No key, headers, or raw exception text.
                code = getattr(error, "code", None)
                if code in {"invalid_api_key", "insufficient_quota", "rate_limit_exceeded", "model_not_found", "unsupported_parameter", "invalid_request_error", "credit_balance_exhausted", "organization_spend_limit_exceeded", "project_spend_limit_exceeded", "organization_usage_limit_exceeded", "slow_down"}:
                    self.last_error_code = code
                return self._finish(messages, "I couldn't complete my reply. Please try again.", False)

            if not completion.choices:
                self.last_error = "EmptyModelResponse"
                return self._finish(messages, "I couldn't complete my reply. Please try again.", False)
            choice = completion.choices[0]
            response = choice.message
            calls = response.tool_calls or []
            if not calls:
                reply = response.content or getattr(response, "refusal", None)
                if not reply or choice.finish_reason == "length":
                    self.last_error = "IncompleteModelReply"
                    return self._finish(messages, "I couldn't complete my reply. Please try again.", False)
                return self._review_and_finish(messages, reply)

            requests = [
                {"id": call.id, "type": "function", "function": {"name": call.function.name, "arguments": call.function.arguments}}
                for call in calls
            ]
            messages.append({"role": "assistant", "content": response.content, "tool_calls": requests})
            for call in calls:
                name, arguments = call.function.name, call.function.arguments
                if name == "record_feedback":
                    # The model's unknown-question request is the knowledge result.
                    # Re-route before performing the logging action.
                    self.last_route = route_and_dispatch(user_message, pending_lead=self.pending_lead, answer_available=False)
                if at_limit:
                    result, parsed, reused = {"success": False, "message": "Tool-call limit reached."}, None, False
                else:
                    result, parsed, reused = self._tool_result(name, arguments)
                self.last_tool_events.append({"name": name, "arguments": parsed, "result": deepcopy(result), "deduplicated": reused})
                messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, ensure_ascii=False)})
                if name == "record_customer_interest" and result.get("success") is True:
                    self.pending_lead = False

            if at_limit:
                self.last_error = "ToolCallLimit"
                return self._finish(messages, "I couldn't finish this request in this turn. Please try again.", False)

        raise RuntimeError("Unexpected end of interaction loop")
