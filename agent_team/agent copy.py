import os
import asyncio
from google.adk.agents.llm_agent import Agent
from google.adk.agents import SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
from tools.itsm import check_changes, check_ticket, create_ticket, search_tickets_by_ci
from tools.transactions import list_transaction_ids_by_device, get_transaction_details
from tools.logs import query_transaction_logs
from tools.goodbye import say_goodbye
from tools.greetings import say_hello
from callbacks.before_model import block_keyword_guardrail
from callbacks.before_tool import block_tool_guardrail
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
    description="A helpful assistant for itsm activities like check ticket status, check changes, create ticket.",
    instruction="""
You are an IT Service Management (ITSM) assistant. 
You can help users with tasks such as checking ticket status, checking changes for configuration items, and creating new tickets. 
Use the provided tools to perform these actions accurately and efficiently.""",
    tools=[check_changes, check_ticket, create_ticket, search_tickets_by_ci],
    output_key="last_itsm_response",
)

transaction_agent = Agent(
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    name="transaction_agent",
    description="Agent with access to tools to get the transaction details",
    instruction="""
You are an assistant that helps users retrieve transaction details.
You can list transaction IDs for a given device and get full transaction details using the provided tools.""",
    tools=[list_transaction_ids_by_device, get_transaction_details],
    output_key="last_transaction_response",
    before_tool_callback=block_tool_guardrail,
)

greeting_agent = Agent(
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    name="greetings_agent",
    instruction="""You are a greetings agent. Your ONLY task is to provide a friendly greeting
                Use the 'say_hello' toool to generate the greeting
                if user provided their name, make sure to pass it to the tool
                Donot engage in any other conversation or task""",
    description="Handles simple greeting and say hello using the 'say-hello' tool",
    tools=[say_hello],
)

farewell_agent = Agent(
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    name="farewell_agent",
    instruction="""You are a farewell agent. Your only task is top say a polite goodbye"
                Use the 'say_goodbye' tool when user indicates that they are leaving
                Donot perform any other actions""",
    description="Handles simple farewells and goodbye using the 'say_goodbye' tool",
    tools=[say_goodbye],
)

logs_agent =Agent(
    model=Gemini(model='gemini-2.5-flash', retry_options=retry_config),
    name="logs_agent",
    instruction="""You are a logs agent, Your ionly task is to call the tool to fetch the transaction details
    Use `query_transaction_logs` tool to fetch the transaction details for a particular device
    Donot perform any other tasks
""",
    description="Handles request to fetch the logs for a device. Use `query_transaction_logs` tool to fetch the device logs",
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
    description="The main coordinator agent. Delegates requests related to health check, summary, transaction details, transaction by device, incident status checking, incident creation, change checking and greeting/goodbye to specialized agents.",
    instruction="""You are the main co-ordinator agent. you have access to multiple specilized agents
                1. 'greeting_agent' : Use this agent to say hello to the user when a conversation starts
                2. 'farewell_agent' : Use this agent to say bye to the user when he indicates that he is leaving
                3. 'itsm_agent' : use this agent for ITSM related activities like check ticket status, check changes, create ticket
                4. 'transaction_agent' : use this agent to any questions related to transaction and transaction status
                5. `logs_agent`: use this agent for any query to pull the device transaction logs
                Your responsibility is to analyse the user query and delegate the question to the appropriate sepcilized agent. 
                You should polity ignore any questions other than you are asked for""",
    sub_agents=[greeting_agent, farewell_agent,itsm_agent, transaction_agent,logs_agent],
    output_key="last_response",
    before_model_callback=block_keyword_guardrail,
    before_tool_callback=block_tool_guardrail
)

## Initial state
initial_state = {}

                # 3. 'itsm_agent' : use this agent for ITSM related activities like check ticket status, check changes, create ticket
                # 4. 'transaction_agent' : use this agent to any questions related to transaction and transaction status
                # 5. `logs_agent`: use this agent for any query to pull the device transaction logs
## Create a specific session service for the agents
async def _create_session():
    return await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID, state=initial_state
    )


session = asyncio.run(_create_session())
# Pass the session *service* to Runner (not a single session object).
# Runner expects a SessionService implementation with a `get_session` method.
runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)


async def run_agent(query: str, runner, user_id, session_id):
    """Sends a query to the agent and print final response"""
    print(f"User query: {query}")

    # Prepare the users's query to the agent and prints the final reponse
    content = types.Content(role="user", parts=[types.Part(text=query)])
    print(f"Content: {content}")
    final_response_text = "Agent did not produce a final response."

    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
        # print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
            elif event.actions and event.actions.escalate:
                final_response_text = (
                    f"Agent escalated: {event.error_message or 'No Specific Message'}"
                )

            break
    print(f"Agent Response: {final_response_text}")


async def run_conversation():
    print("Starting conversation with agent...")
    print("Type 'exit' to end the conversation.\n")

    while True:
        # Get user input
        user_message = input("You: ").strip()

        # Check if user wants to exit
        if user_message.lower() == "exit":
            print("Ending conversation.")
            break

        # Skip empty input
        if not user_message:
            print("Please enter a message.\n")
            continue

        # Run the agent with user input
        try:
            await run_agent(
                user_message, runner=runner, user_id=USER_ID, session_id=SESSION_ID
            )
        except Exception as e:
            print(f"Error processing message: {e}\n")

    final_session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    if final_session:
        print(
            f"Final Preference: {final_session.state.get('last_itsm_response', 'last_itsm_response Not Set')}"
        )
        print(
            f"Final Preference: {final_session.state.get('last_transaction_response', 'last_transaction_response Not Set')}"
        )
        print(
            f"Final Preference: {final_session.state.get('last_response', 'last_response Not Set')}"
        )


if __name__ == "__main__":
    try:
        asyncio.run(run_conversation())
    except Exception as e:
        print(f"An error occurred: {e}")
