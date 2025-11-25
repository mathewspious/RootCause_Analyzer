from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from typing import Optional


def block_keyword_guardrail(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    Inspect the user content for text password.
    If found block the llm call and respond with predefined text
    """
    agent_name = callback_context.agent_name
    print(f"Callback: block_keyword_guradrail running for agent: {agent_name}")

    # Extracting the text from the last user message in the request history
    last_user_message = ""
    if llm_request.contents:
        for content in reversed(llm_request.contents):
            if content.role == "user" and content.parts:
                if content.parts[0].text:
                    last_user_message = content.parts[0].text
                    break

    print(f"Callback: Inspecting last user message: '{last_user_message}'")

    keyword_to_block = "password"

    if keyword_to_block in last_user_message.lower():
        print(f"detected sensitive text")
        callback_context.state["guardrail_block_keyword_triggered"] = True

        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text=f"The request contains sensitive words, This cannot be processed"
                    )
                ],
            )
        )
    else:
        print("request Validated")
        return None
