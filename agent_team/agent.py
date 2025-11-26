import os
import asyncio
from google.adk.agents.llm_agent import Agent
from google.adk.agents import ParallelAgent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.planners import BuiltInPlanner
from google.genai import types
from .tools.itsm import check_changes, check_ticket, create_ticket, search_tickets_by_ci
from .tools.transactions import list_transaction_ids_by_device, get_transaction_details
from .tools.logs import query_device_logs
from .tools.goodbye import say_goodbye
from .tools.greetings import say_hello
from .callbacks.before_model import block_keyword_guardrail
from .callbacks.before_tool import block_tool_guardrail
from dotenv import load_dotenv
import warnings

warnings.filterwarnings("ignore")

## Code to read .env file to set environment variables
load_dotenv()

from arize.otel import register

# Register with Arize AX
tracer_provider = register(
    space_id=os.getenv("SPACE_ID"),      # Found in app space settings page
    api_key=os.getenv("API_KEY"),        # Found in app space settings page
    project_name="RCA_Helper"  # Name this whatever you prefer
)

# Import and configure the automatic instrumentor from OpenInference
from openinference.instrumentation.google_adk import GoogleADKInstrumentor

# Finish automatic instrumentation
GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)

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

thinking_config = types.ThinkingConfig(
    include_thoughts=True,
    thinking_budget=256
)
planner=BuiltInPlanner(
    thinking_config=thinking_config
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
    planner=planner,
    tools=[check_changes, check_ticket, create_ticket, search_tickets_by_ci],
    output_key="last_itsm_response",
)

itsm_health_agent = Agent(
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    name="itsm_health_agent",
    description="Handles ITSM operations including ticket status checks, change verification, ticket creation, and CI-based ticket searches.",
    instruction="""You are an IT Service Management (ITSM) assistant.
You have access to the following tools:
- check_ticket: Check the status of existing tickets
- check_changes: Verify changes for configuration items
- search_tickets_by_ci: Search for tickets related to specific configuration items

**CONTEXT HANDLING:**
- **If the user (or a parent agent) asks for a "Health Check", "Status Check", or "Device Check":** You MUST automatically use `search_tickets_by_ci` to find open incidents for that device and use `check_changes` to see if there is any changes in progress.

### OUTPUT REQUIREMENT FOR HEALTH CHECKS:
When returning data to the parent agent, you must provide a detailed summary of **open/recent incidents** related to the device.

If tickets are found, use this structured format:
[{'ticket_id': 'INC12345', 'status': 'Open - P2', 'summary': 'Network connectivity loss in DC', 'created_date': '2025-11-25'}, ...]

If NO tickets are found, return:
"ITSM_CHECK_RESULT: No open incidents or recent changes found."

Only use these tools to help users with ITSM-related requests.""",
    planner=planner,
    tools=[check_changes, search_tickets_by_ci],
    output_key="last_itsm_response",
)

transaction_agent = Agent(
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    name="transaction_agent",
    description="Retrieves transaction-related information for devices from the database.",
    instruction="""You are a transaction retrieval assistant.
You have access to the following tools only:
- list_transaction_ids_by_device: Retrieve transaction IDs associated with a specific device
- get_transaction_details: Retrieve detailed information about a specific transaction

Only use these tools to help users retrieve transaction data. If a request is outside the scope of these tools, inform the user that you cannot perform that action.""",
    planner=planner,
    tools=[list_transaction_ids_by_device, get_transaction_details],
    output_key="last_transaction_response",
    before_tool_callback=block_tool_guardrail,
)

transaction_health_agent = Agent(
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    name="transaction_health_agent",
    description="Retrieves transaction-related information for devices from the database.",
    instruction="""You are a transaction retrieval assistant.
You have access to the following tools:
- list_transaction_ids_by_device: Retrieve transaction IDs associated with a specific device

**CONTEXT HANDLING:**
- **If the user (or a parent agent) asks for a "Health Check" or "Device Check":** You MUST use `list_transaction_ids_by_device` to see if traffic is flowing.
### OUTPUT REQUIREMENT FOR HEALTH CHECKS:
You must provide a structured summary of the transaction flow.

Return data in this structured format:
{'time_window_checked': 'Last 24 hours', 'total_transactions_found': 150, 'status': 'Nominal', 'sample_ids': ['TXN1A', 'TXN1B']}

If NO transactions are found, return:
"TRANSACTION_CHECK_RESULT: Zero transactions found in the last 24 hours."

Only use these tools to help users retrieve transaction data.""",
    planner=planner,
    tools=[list_transaction_ids_by_device],
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
    planner=planner,
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
    planner=planner,
    tools=[say_goodbye],
)


logs_agent = Agent(
    model=Gemini(model='gemini-2.5-flash', retry_options=retry_config),
    name="logs_agent",
    instruction="""You are a logs retrieval assistant.
You have access to only one tool:
- query_device_logs: Retrieve device logs for a specific device

**CONTEXT HANDLING:**
- **If the user (or a parent agent) asks for a "Health Check" or "Device Check":** You MUST use `query_device_logs` to fetch recent error logs.

Use the 'query_device_logs' tool when the user requests device logs.""",
    description="Retrieves device logs for devices.",
    planner=planner,
    tools=[query_device_logs]
)

logs_health_agent = Agent(
    model=Gemini(model='gemini-2.5-flash', retry_options=retry_config),
    name="logs_health_agent",
    instruction="""You are a logs retrieval assistant.
You have access to only one tool:
- query_device_logs: Retrieve device logs for a specific device

**CONTEXT HANDLING:**
- **If the user (or a parent agent) asks for a "Health Check" or "Device Check":** You MUST use `query_device_logs` to fetch recent error logs.
### OUTPUT REQUIREMENT FOR HEALTH CHECKS:
You must provide a structured list of the critical logs found.

If logs are found, use this structured format:
[{'timestamp': '2025-11-26 10:01:05', 'level': 'ERROR', 'message': 'DB Connection Timeout'}, {'timestamp': '2025-11-26 10:00:50', 'level': 'CRITICAL', 'message': 'Process [PID 55] terminated'}, ...]

If NO critical logs are found, return:
"LOGS_CHECK_RESULT: No critical or error logs found in the recent history."

Use the 'query_device_logs' tool when the user requests device logs.""",
    description="Retrieves device logs for devices.",
    planner=planner,
    tools=[query_device_logs]
)

parallel_health_check_executor = ParallelAgent(
    name="parallel_health_check_executor",
    description="Performs a comprehensive device health check by querying ITSM, Logs, and Transactions simultaneously. Use this for requests like 'How is device X?', 'Quick check', or 'Status report'.",
    # The ParallelAgent will run these 3 asynchronously
    sub_agents=[itsm_health_agent, transaction_health_agent, logs_health_agent]
)

# 2. The Synthesis Agent
summary_agent = Agent(
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    name="summary_agent",
    description="Analyzes and summarizes the raw output from the parallel health checks into a detailed final report.",
    instruction="""You are a Senior Device Health Auditor. Your responsibility is to analyze the raw, parallel-executed data provided to you and synthesize it into a professional, detailed health check report.

The input data you receive contains the separate outputs from the ITSM, Transaction, and Logs agents.

### ANALYSIS STEPS:
1.  **Extract Key Findings:** Identify the most relevant data points (e.g., specific error codes, ticket IDs, transaction counts).
2.  **Correlate Data:** Determine if findings are related. Explicitly state any direct link found between tickets, logs, and transaction failures.
3.  **Synthesize Status:** Translate the raw data into a clear business impact.

### FINAL OUTPUT TEMPLATE (Must be strictly followed):
**Detailed Device Health Report for [Inferred Device Name]**
---
**1. 🎫 ITSM Status Assessment**
* **Key Finding:** [List any open tickets/changes by ID or summary. If none, state clearly.]
* **Time Since Last Incident:** [Provide relevant context if possible.]

**2. 📊 Transaction Health & Flow**
* **Key Finding:** [Report total number of transactions found. If zero, highlight the period checked.]
* **Status Verdict:** [Healthy/Warning based on transaction flow.]

**3. 📜 System Logs Deep Dive**
* **Key Finding:** [List the most recent 2-3 critical errors found, including timestamps if available.]
* **Impact Summary:** [Describe the likely impact of the log errors.]

**4. 🔗 Cross-System Correlation**
* **Summary:** [State any direct links found between the three data sources. If no correlation, state "No direct correlation observed."]

**5. 📈 Final Executive Assessment**
* **Overall Health Rating:** **[CRITICAL / WARNING / HEALTHY]**
* **Recommended Next Step:** [Suggest the most logical action based on the summary.]
""",
    planner=planner,
    # This agent uses its LLM to summarize, so it requires no tools.
    tools=[],
    output_key="final_health_report",
)


# 3. The Sequential Wrapper Agent
health_check_agent = SequentialAgent(
    name="health_check_agent",
    description="Performs a complete, two-step device health check: parallel data gathering followed by detailed summary creation. Use this for all general status and health report requests.",
    # The sub_agents list defines the sequence of execution
    sub_agents=[
        parallel_health_check_executor,  # Step 1: Execute all checks in parallel
        summary_agent,                   # Step 2: Summarize the output from Step 1
    ]
)

root_agent = Agent(
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    name="rca_agent",
    description="Main coordinator agent.",
    instruction="""You are the main coordinator. Route user queries to the correct specialized agent.

### ROUTING LOGIC:
1.  **General Status / Health Checks:**
    - Triggers: "Check device X", "How is X doing?", "Status of X", "Health report".
    - Action: Route to `health_check_agent`.

2.  **Specific ITSM Tasks:**
    - Triggers: "Create ticket", "Search for ticket #123", "ticket for CI #343".
    - Action: Route to `itsm_agent`.

3.  **Specific Transaction Tasks:**
    - Triggers: "Get details for transaction #ABC", "Get transactions for #124".
    - Action: Route to `transaction_agent`.

4.  **Specific Log Tasks:**
    - Triggers: "Show me the logs".
    - Action: Route to `logs_agent`.

5.  **Social:**
    - Action: Route to `greeting_agent` or `farewell_agent`.

If a request is ambiguous, ask for clarification. Do not invent answers.""",
    planner=planner,
    # Health Check is added to the sub-agents list
    sub_agents=[greeting_agent, farewell_agent, itsm_agent, transaction_agent, logs_agent, health_check_agent],
    output_key="last_response",
    before_model_callback=block_keyword_guardrail,
    before_tool_callback=block_tool_guardrail
)

## Initial state
initial_state = {}

def _create_session():
    return  session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID, state=initial_state
    )

session = _create_session()
# Pass the session *service* to Runner (not a single session object).
# Runner expects a SessionService implementation with a `get_session` method.
runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)