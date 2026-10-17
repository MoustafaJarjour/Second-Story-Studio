"""Step 3: a small, deterministic English-language router.

The handlers return action plans. Logging tools are defined in business_tools.py;
model-driven execution and replies are added in later assignment steps. No API
calls or customer records are made by this router.
"""

from dataclasses import dataclass
import re


GENERAL = "general_question"
LEAD = "lead_collection"
FEEDBACK = "feedback_or_unanswered"


def _patterns(*expressions):
    return tuple(re.compile(expression, re.IGNORECASE) for expression in expressions)


LEAD_PATTERNS = _patterns(
    r"\b(?:contact|email|call|reach)\s+me\b",
    r"\b(?:get|put)\s+(?:me\s+)?in touch\b",
    r"\b(?:i'd like|i would like|i want|i wish|can i|could i|please)\s+"
    r"(?:to\s+)?(?:book|schedule|reserve|arrange|request|join|sign up)\b",
    r"\b(?:i'd like|i would like|i want|please arrange|please schedule)\s+"
    r"(?:to get\s+)?(?:a|an|the)\s+(?:consultation|quote|quotation|follow-up|follow up|appointment)\b",
    r"(?:^|[.!?;]\s*|\b(?:also|and|then)\s+)(?:please\s+)?(?:book|schedule|reserve)\s+(?:me|a|an|my)\b",
    r"\b(?:can|could|would) you\s+(?:please\s+)?(?:book|schedule|reserve)\b",
    r"\bsign\s+me\s+up\b",
    r"\bi(?:'m| am) interested in\s+(?:booking|joining|a consultation|a quote)\b",
)

LEAD_DECLINE_PATTERNS = _patterns(
    r"\b(?:do not|don't|dont|never)\s+(?:contact|email|call|reach|book|schedule)\b",
    r"\b(?:not interested in|don't want|do not want|no longer want)\s+"
    r"(?:to\s+)?(?:a\s+)?(?:book\w*|consultation|follow-up|follow up|appointment|contact)\b",
    r"\b(?:cancel|stop)\s+(?:(?:my|the)\s+)?(?:follow-up|follow up|contact request|booking|appointment)\b",
    r"\b(?:don't want to|do not want to|don't|do not|won't|will not|prefer not to|rather not)\s+"
    r"(?:share|give|provide)\s+(?:my\s+)?(?:email|name|contact details|details)\b",
    r"\b(?:no need|don't want|do not want)\s+(?:you\s+)?to\s+(?:be\s+)?(?:contact(?:ed)?|email(?:ed)?|call(?:ed)?)\b",
    r"\bstop\s+(?:contacting|emailing|calling)\b",
)

LEAD_INFORMATION_PATTERNS = _patterns(
    r"\bhow\s+(?:do|can|could|should)\s+(?:i|we)\s+(?:book|schedule|reserve|request|arrange)\b",
    r"\b(?:do|would|will)\s+(?:i|we)\s+(?:have|need)\s+to\s+(?:book|schedule|reserve|request|arrange)\b",
)

FEEDBACK_PATTERNS = _patterns(
    r"\b(?:i have|i want to (?:give|share|leave))\s+(?:some\s+|a\s+)?(?:feedback|complaint|suggestion)\b",
    r"\bmy\s+(?:feedback|complaint|suggestion)\s*(?:is\b|:)",
    r"\b(?:record|log|pass on)\b.*\b(?:feedback|complaint|suggestion|loved|enjoyed|disliked)\b",
    r"\b(?:tell|let)\s+(?:the|your)\s+team\b.*\b(?:loved|enjoyed|feedback|complaint|suggestion)\b",
    r"\b(?:please|you should|i suggest|i wish you would)\s+(?:add|offer|consider|introduce|include)\b",
    r"\b(?:i(?:'m| am)\s+(?:unhappy|dissatisfied)|not happy|disappointed)\s+(?:with|about|by)\b",
    r"\b(?:your|the)\s+(?:service|workshop|team|staff)\s+(?:was|is|were|are)\s+(?:poor|bad|rude|late|boring)\b",
    r"\b(?:your|the)\s+(?:team|staff)\s+(?:damaged|broke|lost)\b",
)

FEEDBACK_DECLINE_PATTERNS = _patterns(
    r"\b(?:do not|don't|dont)\s+(?:record|log|share|pass on)\b.*\b(?:feedback|complaint|suggestion)\b",
)

LEAD_DETAIL_PATTERNS = _patterns(
    r"\b(?:please\s+)?(?:add|include|record|log|update|use)\s+(?:my|our|this|the)\s+"
    r"(?:email|name|contact details|details|story|notes)\b",
    r"\b(?:please\s+)?(?:add|include|record|log|update|use)\s+(?:my|our)\s+"
    r"[^.!?;,]{0,45}\b(?:story|project notes)\b",
)

QUESTION_PATTERN = re.compile(
    r"^(?:what|where|when|why|how|who|which|do|does|is|are|can|could|would|will)\b"
    r"|\b(?:tell me about|list your|explain your)\b", re.IGNORECASE
)
SMALLTALK_PATTERN = re.compile(
    r"^(?:hi|hello|hey|thanks|thank you|thanks[, ]+that was helpful|that was helpful|okay|ok)[.! ]*$",
    re.IGNORECASE,
)


def _normalise(message):
    if not isinstance(message, str) or not message.strip():
        raise ValueError("message must be a non-empty string")
    return re.sub(r"\s+", " ", message.replace("\u2019", "'").replace("\u2018", "'")).strip()


def _matches(patterns, text):
    return [match for pattern in patterns for match in pattern.finditer(text)]


def _positive_matches(positive, negative):
    # A positive phrase inside "don't contact me" must not start a lead.
    return [match for match in positive if not any(
        match.start() < denial.end() and denial.start() < match.end()
        for denial in negative
    )]


@dataclass(frozen=True)
class RouteDecision:
    intent: str
    reason: str
    lead_active: bool
    collect_lead: bool = False
    customer_feedback: bool = False
    unanswered_question: bool = False
    secondary_intents: tuple = ()


def route_message(message, *, pending_lead=False, answer_available=None):
    """Classify one turn and preserve any secondary action.

    pending_lead is application state, cleared after a successful lead record or
    a customer decline. answer_available=False is supplied only after the answer
    logic determines that a business question cannot be answered. None means
    knowledge has not been checked yet; the router never guesses knowledge gaps.
    """
    text = _normalise(message)
    if not isinstance(pending_lead, bool):
        raise TypeError("pending_lead must be a boolean")
    if answer_available is not None and not isinstance(answer_available, bool):
        raise TypeError("answer_available must be a boolean or None")

    declines = _matches(LEAD_DECLINE_PATTERNS, text)
    lead_matches = _positive_matches(
        _matches(LEAD_PATTERNS, text), declines + _matches(LEAD_INFORMATION_PATTERNS, text)
    )
    if pending_lead and re.fullmatch(r"no[, ]+(?:thanks|thank you)[.! ]*", text, re.IGNORECASE):
        declines.append(re.match(r".*", text))
    last_lead = max((m.start() for m in lead_matches), default=-1)
    last_decline = max((m.start() for m in declines), default=-1)
    new_lead = last_lead > last_decline
    declined = last_decline > last_lead
    lead_active = new_lead or (pending_lead and not declined)

    feedback_matches = _positive_matches(
        _matches(FEEDBACK_PATTERNS, text),
        _matches(FEEDBACK_DECLINE_PATTERNS, text) + _matches(LEAD_DETAIL_PATTERNS, text)
    )
    feedback = bool(feedback_matches)
    is_question = "?" in text or bool(QUESTION_PATTERN.search(text))
    is_smalltalk = bool(SMALLTALK_PATTERN.fullmatch(text))
    # A new factual question can be answered while lead collection stays pending.
    continuation = pending_lead and not declined and not is_question and not feedback and not is_smalltalk
    collect_lead = new_lead or continuation
    unknown = answer_available is False

    if unknown:
        intent, reason = FEEDBACK, "The answer logic reported an unanswered business question."
    elif collect_lead:
        intent = LEAD
        reason = "Explicit follow-up or booking interest." if new_lead else "Reply during active lead collection."
    elif feedback:
        intent, reason = FEEDBACK, "Concrete feedback or an explicit request to record feedback."
    else:
        intent, reason = GENERAL, "General question or conversational reply."
        if declined:
            reason = "Contact or follow-up declined; lead collection ended."

    secondary = []
    if collect_lead and intent != LEAD:
        secondary.append(LEAD)
    if feedback and intent != FEEDBACK:
        secondary.append(FEEDBACK)
    return RouteDecision(intent, reason, lead_active, collect_lead, feedback, unknown, tuple(secondary))


def _plan(message, decision, handler):
    actions = ["answer_any_answerable_business_questions"]
    tools = []
    if decision.collect_lead:
        actions.append("record_complete_interest_or_ask_only_for_missing_details")
        tools.append("record_customer_interest")
    if decision.unanswered_question:
        actions.append("acknowledge_and_record_unanswered_question")
        tools.append("record_feedback")
    if decision.customer_feedback:
        actions.append("acknowledge_and_record_customer_feedback")
        tools.append("record_customer_feedback")
    return {
        "intent": decision.intent,
        "secondary_intents": decision.secondary_intents,
        "handler": handler,
        "reason": decision.reason,
        "message": message,
        "lead_active": decision.lead_active,
        "actions": tuple(actions),
        "candidate_tools": tuple(tools),
    }


def handle_general_question(message, decision):
    return _plan(message, decision, "handle_general_question")


def handle_lead_collection(message, decision):
    return _plan(message, decision, "handle_lead_collection")


def handle_feedback_or_unanswered(message, decision):
    return _plan(message, decision, "handle_feedback_or_unanswered")


HANDLERS = {
    GENERAL: handle_general_question,
    LEAD: handle_lead_collection,
    FEEDBACK: handle_feedback_or_unanswered,
}


def route_and_dispatch(message, *, pending_lead=False, answer_available=None, handlers=None):
    """Invoke the selected handler; later handlers can use the model and tools."""
    decision = route_message(message, pending_lead=pending_lead, answer_available=answer_available)
    registry = HANDLERS if handlers is None else handlers
    return registry[decision.intent](message, decision)
