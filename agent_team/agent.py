import os
import asyncio
from google.adk.agents.llm_agent import Agent
from google.adk.agents import SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
from .tools.itsm import check_changes, check_ticket, create_ticket, search_tickets_by_ci
from .tools.transactions import list_transaction_ids_by_device, get_transaction_details
from .tools.logs import query_transaction_logs
from .tools.goodbye import say_goodbye
from .tools.greetings import say_hello
from .callbacks.before_model import block_keyword_guardrail
from .callbacks.before_tool import block_tool_guardrail
from dotenv import load_dotenv
import warnings

warnings.filterwarnings("ignore")

## Code to read .env file to set environment variables
load_dotenv()

APP_NAME = os.getenv("APP_NAME", "RootCause_Analyzer")
USER_ID = os.getenv("USER_ID", "user_1234")
SESSION_ID = os.getenv("SESSION_ID", "session_1234")

session_service = InMemorySessionService()

retry_config = types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
)

## Define agents
itsm_agent = Agent(
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    name="itsm_agent",
    description="Handles ITSM operations including ticket status checks, change verification, ticket creation, and CI-based ticket searches.",
    instruction="""You are an IT Service Management (ITSM) assistant.
You have access to the following tools only:
- check_ticket: Check the status of existing tickets
- check_changes: Verify changes for configuration items
- create_ticket: Create new support tickets
- search_tickets_by_ci: Search for tickets related to specific configuration items

Only use these tools to help users with ITSM-related requests. If a request is outside the scope of these tools, inform the user that you cannot perform that action.""",
    tools=[check_changes, check_ticket, create_ticket, search_tickets_by_ci],
    output_key="last_itsm_response",
)

transaction_agent = Agent(
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    name="transaction_agent",
    description="Retrieves transaction-related information for devices.",
    instruction="""You are a transaction retrieval assistant.
You have access to the following tools only:
- list_transaction_ids_by_device: Retrieve transaction IDs associated with a specific device
- get_transaction_details: Retrieve detailed information about a specific transaction

Only use these tools to help users retrieve transaction data. If a request is outside the scope of these tools, inform the user that you cannot perform that action.""",
    tools=[list_transaction_ids_by_device, get_transaction_details],
    output_key="last_transaction_response",
    before_tool_callback=block_tool_guardrail,
)

greeting_agent = Agent(
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    name="greetings_agent",
    instruction="""You are a greeting assistant. Your sole responsibility is to greet the user.
You have access to only one tool:
- say_hello: Generate a friendly greeting

Use the 'say_hello' tool to create an appropriate greeting. If the user provides their name, pass it to the tool.
Do not engage in any other conversations or tasks.""",
    description="Generates friendly greetings for users.",
    tools=[say_hello],
)

farewell_agent = Agent(
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    name="farewell_agent",
    instruction="""You are a farewell assistant. Your sole responsibility is to say goodbye.
You have access to only one tool:
- say_goodbye: Generate a polite goodbye message

Use the 'say_goodbye' tool when the user indicates they are leaving or ending the conversation.
Do not perform any other actions.""",
    description="Generates polite goodbye messages for users.",
    tools=[say_goodbye],
)

logs_agent = Agent(
    model=Gemini(model='gemini-2.5-flash', retry_options=retry_config),
    name="logs_agent",
    instruction="""You are a logs retrieval assistant. Your sole responsibility is to fetch transaction logs for devices.
You have access to only one tool:
- query_transaction_logs: Retrieve transaction logs for a specific device

Use the 'query_transaction_logs' tool when the user requests device logs or transaction history.
Do not perform any other actions.""",
    description="Retrieves transaction logs for devices.",
    tools=[query_transaction_logs]
)

# health_check_agent =SequentialAgent(
#     name="health_check_agent",
#     sub_agents=[itsm_agent, transaction_agent, logs_agent],
#     description="executes a high level system health check/ summary check based on a device. Thin includes ITSM system, transaction Database and logs system"
# )
root_agent = Agent(
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    name="rca_agent",
    description="Main coordinator agent that routes requests to specialized agents for ITSM, transactions, logs, greetings, and farewells.",
    instruction="""You are the main coordinator agent. Your role is to analyze user queries and delegate them to the appropriate specialized agent.

Available specialized agents:
1. 'greeting_agent': Use this agent when the user starts a conversation or greets you
2. 'farewell_agent': Use this agent when the user indicates they are leaving or ending the conversation
3. 'itsm_agent': Use this agent for ITSM-related activities (ticket checks, change verification, ticket creation, CI searches)
4. 'transaction_agent': Use this agent for queries about transactions and transaction details
5. 'logs_agent': Use this agent when the user requests device transaction logs

Analyze each user query carefully and delegate to the most appropriate agent based on their request.
If a request does not match any agent's capabilities, politely inform the user that you cannot assist with that request.
Do not attempt to fulfill requests outside the scope of the available agents.""",
    sub_agents=[greeting_agent, farewell_agent, itsm_agent, transaction_agent, logs_agent],
    output_key="last_response",
    before_model_callback=block_keyword_guardrail,
    before_tool_callback=block_tool_guardrail
)

## Initial state
initial_state = {}

## Create a specific session service for the agents
# async def _create_session():
#     return await session_service.create_session(
#         app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID, state=initial_state
#     )

def _create_session():
    return  session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID, state=initial_state
    )

session = _create_session()
# Pass the session *service* to Runner (not a single session object).
# Runner expects a SessionService implementation with a `get_session` method.
runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)


# async def run_agent(query: str, runner, user_id, session_id):
#     """Sends a query to the agent and print final response"""
#     print(f"User query: {query}")

#     # Prepare the users's query to the agent and prints the final reponse
#     content = types.Content(role="user", parts=[types.Part(text=query)])
#     print(f"Content: {content}")
#     final_response_text = "Agent did not produce a final response."

#     async for event in runner.run_async(
#         user_id=user_id, session_id=session_id, new_message=content
#     ):
#         # print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")
#         if event.is_final_response():
#             if event.content and event.content.parts:
#                 final_response_text = event.content.parts[0].text
#             elif event.actions and event.actions.escalate:
#                 final_response_text = (
#                     f"Agent escalated: {event.error_message or 'No Specific Message'}"
#                 )

#             break
#     print(f"Agent Response: {final_response_text}")


# async def run_conversation():
#     print("Starting conversation with agent...")
#     print("Type 'exit' to end the conversation.\n")

#     while True:
#         # Get user input
#         user_message = input("You: ").strip()

#         # Check if user wants to exit
#         if user_message.lower() == "exit":
#             print("Ending conversation.")
#             break

#         # Skip empty input
#         if not user_message:
#             print("Please enter a message.\n")
#             continue

#         # Run the agent with user input
#         try:
#             await run_agent(
#                 user_message, runner=runner, user_id=USER_ID, session_id=SESSION_ID
#             )
#         except Exception as e:
#             print(f"Error processing message: {e}\n")

#     # final_session = await session_service.get_session(
#     #     app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
#     # )
#     # if final_session:
#     #     print(
#     #         f"Final Preference: {final_session.state.get('last_itsm_response', 'last_itsm_response Not Set')}"
#     #     )
#     #     print(
#     #         f"Final Preference: {final_session.state.get('last_transaction_response', 'last_transaction_response Not Set')}"
#     #     )
#     #     print(
#     #         f"Final Preference: {final_session.state.get('last_response', 'last_response Not Set')}"
#     #     )


# if __name__ == "__main__":
#     try:
#         asyncio.run(run_conversation())
#     except Exception as e:
#         print(f"An error occurred: {e}")