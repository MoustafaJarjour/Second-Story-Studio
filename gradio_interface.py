"""Step 7: a ChatInterface with separate, server-side session memory."""

from copy import deepcopy

import gradio as gr


def make_chat_handler(agent_factory):
    """Keep tool history in State; the visible chat contains only customer replies."""
    def respond(message, history, session):
        if not isinstance(message, str) or not message.strip():
            raise gr.Error("Please enter a message.")

        # Gradio supplies history before the current message. Retry/undo can
        # shorten it, so restore the matching completed-turn checkpoint.
        previous_turns = sum(item["role"] == "user" for item in history)
        state = deepcopy(session) if session else {"turns": [], "successful_calls": {}}
        if previous_turns > len(state["turns"]):
            raise gr.Error("Please start a new conversation to reset this chat.")
        agent = agent_factory()
        if previous_turns:
            checkpoint = state["turns"][previous_turns - 1]
            agent.history = deepcopy(checkpoint["history"])
            agent.pending_lead = checkpoint["pending_lead"]
        # Logging cannot be undone by removing a bubble. Retain receipts during
        # retry/undo so an identical successful call is not written again.
        agent._successful_calls = deepcopy(state["successful_calls"])
        reply = agent.chat(message)
        state["turns"] = state["turns"][:previous_turns]
        state["turns"].append({
            "history": deepcopy(agent.history),
            "pending_lead": agent.pending_lead,
        })
        state["successful_calls"] = deepcopy(agent._successful_calls)
        return reply, state

    return respond


def reset_session():
    """Clear both customer-visible messages and private conversation memory."""
    return [], [], None, ""


def build_interface(agent_factory):
    """Build the interface without sending an API request or launching a server."""
    with gr.Blocks(analytics_enabled=False, title="Second Story Studio | Tala") as demo:
        gr.Markdown(
            "# Second Story Studio\n"
            "### Keep the story. Change the object.\n"
            "Meet **Tala**, your virtual concierge for meaningful furniture and textiles. "
            "Explore an idea, ask about our services, or request a conversation with the team."
        )
        session = gr.State(value=None, time_to_live=3600)
        chatbot = gr.Chatbot(
            label="Chat with Tala",
            height=420,
            layout="bubble",
            buttons=["copy"],
            placeholder="What would you like to preserve about your piece?",
        )
        chat = gr.ChatInterface(
            fn=make_chat_handler(agent_factory),
            chatbot=chatbot,
            textbox=gr.Textbox(placeholder="Tell Tala about your piece, or ask a question…", max_lines=5, submit_btn="Send", stop_btn=False),
            additional_inputs=[session],
            additional_outputs=[session],
            editable=False,
            save_history=False,
            flagging_mode="never",
            analytics_enabled=False,
            concurrency_limit=1,
            cache_examples=False,
        )
        with gr.Row():
            consultation = gr.Button("Consultation details", size="sm")
            project = gr.Button("Explore a project", size="sm")
            workshop = gr.Button("Workshops", size="sm")
        for button, prompt in [
            (consultation, "What does a Second Story Consultation cost, and how long is it?"),
            (project, "Can you turn an old shirt into a cushion?"),
            (workshop, "Tell me about your workshops."),
        ]:
            button.click(lambda text=prompt: text, outputs=chat.textbox, queue=False, api_visibility="private")
        new_chat = gr.Button("New conversation", variant="secondary")
        new_chat.click(
            reset_session,
            outputs=[chat.chatbot, chat.chatbot_state, session, chat.textbox],
            queue=False,
            api_visibility="private",
        )
        chatbot.change(
            lambda messages: gr.update(interactive=not messages or messages[-1]["role"] == "assistant"),
            inputs=chatbot, outputs=new_chat, queue=False, api_visibility="private",
        )
        chatbot.clear(lambda: None, outputs=session, queue=False, api_visibility="private")
        gr.Markdown(
            "*A fictional Beirut studio created for an assignment.* "
            "Share contact details only when you want team follow-up. "
            "Requests and feedback may be saved for review."
        )
    return demo


def interface_theme():
    return gr.themes.Soft(
        primary_hue="orange", secondary_hue="stone", neutral_hue="stone",
        font=["Arial", "sans-serif"], font_mono=["Consolas", "monospace"],
    )
