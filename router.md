# Second Story Studio - Simple Router

The Step 3 router uses Python's standard library. It runs without an API key and selects exactly three intents: `general_question`, `lead_collection`, and `feedback_or_unanswered`.

## How it works

1. Normalize apostrophes and spacing in the incoming message.
2. Check explicit follow-up requests, scoped contact refusals, and concrete feedback phrases.
3. Use the current lead state for replies containing contact details or project notes.
4. Select the primary intent and preserve any secondary action for a mixed message.
5. Invoke the matching handler through the handler registry.

The handlers return action plans for the later agent. They do not execute the logging tools. The plan names candidate tools separately, preserving the distinction between `record_feedback(question)` for unknowns and `record_customer_feedback(feedback)` for customer feedback.

## Knowledge checks

A question starts on the general path unless it also contains explicit lead interest or feedback. The router cannot determine whether the supplied business knowledge answers an arbitrary question. After the answer logic reports an unanswered business question, call the dispatcher with `answer_available=False` to select the unanswered-question handler. Use `None` before checking knowledge and `True` after finding an answer.

The custom quotation process is a known business fact. A question about an individual project's price therefore does not automatically count as unknown: the agent can explain that an assessment and quote are required.

## Conversation state

Carry the `lead_active` value into the next call as `pending_lead`. Clear it after a successful lead record or when the customer declines contact. The logging tools are implemented in `business_tools.py`; the later model interaction will connect their results to conversation state. A factual question during collection goes to general handling while preserving the pending lead state. The router does not parse or store names or email addresses; the later agent handles field collection and the tools validate supplied values.

## Demonstration and verification

`business_agent.ipynb` includes the complete router, examples, and 17 executable checks. Its code cells have been executed and their observed outputs saved. `router_demo.md` summarizes actual routing results. `router.py` can also be imported by later application code, and `test_router.py` provides the same focused checks independently.

## Practical limit

This is a small rule-based classifier for explicit English requests. It does not provide general natural-language understanding, and unrecognized paraphrases default to general handling. The later agent should inspect the full message and apply its instructions, rather than treating a route label as proof of customer consent or answer availability.
