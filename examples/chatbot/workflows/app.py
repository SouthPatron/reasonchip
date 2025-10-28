import typing
import os
import logging

from openai import OpenAI

from reasonchip import EngineContext

# Setup logging
log = logging.getLogger("chatbot.app")

_history: typing.Dict[str, typing.List[typing.Dict[str, str]]] = {}


async def entry(
    context: EngineContext,
    user_id: str,
    message: str,
) -> typing.Any:

    log.info(f"Received message from user '{user_id}': {message}")

    # Retrieve or initialize the conversation history
    history: typing.List[typing.Dict[str, str]] = _history.setdefault(
        user_id, []
    )

    # Append the new user message
    history.append({"role": "user", "content": message})

    # Call OpenAI Chat Completion
    try:
        client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            organization=os.environ.get("OPENAI_ORG_ID"),
        )

        response = client.responses.create(
            model="gpt-4.1-nano",
            instructions="Talk like a pirate.",
            user=user_id,
            input=[x for x in history],
        )

        reply = response.output_text

        history.append({"role": "assistant", "content": reply})

        history = history[-20:]  # Keep only the last 20 messages

        print(f"Reply to user '{user_id}': {reply}")

    except Exception as e:
        log.exception("OpenAI request failed")
        return f"[error]: {e}"

    return reply
