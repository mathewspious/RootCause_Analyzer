# RootCause Analyzer: Multi-Agent AI System for ITSM & Diagnostics

<p align="center">
  <img src="images/rca_analyser.png" width="400" alt="RootCause Analyzer architecture">
</p>

### Project Pitch: Solving the IT Operations Fragmentation Crisis 💡

Operations teams face critical challenges in incident response due to siloed data across ITSM, transaction records, and system logs. Troubleshooting is a manual, time-sensitive ordeal involving multiple tools and expert knowledge.

RootCause Analyzer is a modular, AI-agent system built on the Google ADK/Gemini API that automatically correlates these disparate data sources in real-time, delivering a consolidated device health report in minutes, not hours.

### 🎯 The Problem: Why Troubleshooting Fails Today

1. **Information Fragmentation**
   - Ops teams must manually correlate data across ITSM tickets, transaction databases, and logs
   - Average incident response time: 2-4 hours due to context-switching between tools
   - Root cause identification requires jumping between 5+ different systems

2. **Slow Incident Response**
   - When a critical outage occurs (e.g., payment gateway failure), operations staff must:
     - Check ITSM for related tickets
     - Query transaction logs for error patterns
     - Manually investigate device-level metrics
     - Manually correlate findings across all systems
   - This multi-step manual process leads to delayed resolution and business impact

3. **Knowledge Silos & Scalability Issues**
   - Expert knowledge lives in individual contributors' heads
   - New team members require weeks of training to understand system interactions
   - As infrastructure scales (100s of devices, 1000s of transactions/sec), manual correlation becomes impossible

4. **Lack of Intelligent Automation**
   - Current monitoring systems generate alerts but don't correlate root causes
   - No unified interface to query multiple systems using natural language
   - Guardrails and security policies are inconsistently applied across tools

- **Solution:** RootCause_Analyzer is a modular agent-based system that runs coordinated, automated device health checks by querying ITSM, transaction records, and logs in parallel and synthesizing results into an executive health report.

## Why this matters
- Faster incident triage and reduced mean time to resolution (MTTR).
- Consolidated evidence for decision making: tickets, transactions, and logs in a single report.
- Modular agents make it easy to extend to additional data sources or change policies.

## Project Overview (Solution)

RootCause_Analyzer coordinates multiple lightweight agents to perform health checks and generate a consolidated report. It uses a combination of specialized agents for ITSM, Transactions, and Logs, a Parallel executor to gather data concurrently, and a summary agent to synthesize the findings.

### Key Features

#### 1. **Unified Query Interface**
- Single conversational endpoint for multi-domain queries
- Natural language understanding (no SQL or API knowledge required)
- Context-aware agent routing

#### 2. **Intelligent Agent Specialization**
| Agent | Specialization 
|-------|----------------
| ITSM Agent | Ticket lifecycle, change management, CI tracking 
| Transaction Agent | Device status, transaction histories 
| Logs Agent | Time-series log queries, anomaly detection 
| Greeting/Farewell | Conversation lifecycle management
| health check Agent | Do a complete health check of the requested CI

#### 3. **Enterprise Security Guardrails**
- **Keyword Filtering**: Blocks sensitive queries (e.g., password requests)
- **Tool-Based Access Control**: Prevents queries to restricted devices (e.g., sensor-c)
- **Session State Isolation**: Per-user session tracking for audit compliance

#### 4. **Real-Time Correlation**
- Simultaneously queries multiple data sources
- Correlates findings across ITSM, transactions, and logs
- Identifies root cause patterns automatically

#### 5. **Resilience & Reliability**
- Exponential backoff retry logic (5 attempts, max ~2.8 min)
- Async/await non-blocking architecture
- In-memory session management for fast state access

### Before vs. After

| Aspect | Before | After |
|--------|--------|-------|
| **Time to Incident Root Cause** | 30 min - 1 hours | 5 mins |
| **User Expertise Required** | Expert (knows all systems) | Novice (natural language) |
| **Number of Systems Queried** | Manual (operator switches) | Automatic (coordinated) |
| **Correlation Accuracy** | Manual (error-prone) | LLM-assisted (comprehensive) |
| **Audit Trail** | Fragmented logs | Unified session state |
| **Scalability** | Manual process (doesn't scale) | Agent-based (scales to 100s of agents) |

**What RootCause Analyzer Solves:**
✅ Multi-domain query correlation
✅ Intelligent agent routing
✅ Natural language incident analysis
✅ Audit-ready session tracking
✅ Security guardrails enforcement
✅ Asynchronous, real-time responses

**What's Out of Scope (Future Phases):**
🔄 Live ITSM system integration (uses mock data currently)
🔄 Real device APIs (uses mock transaction data)
🔄 Persistent data warehouse
🔄 Advanced ML-based root cause prediction
🔄 Mobile/web UI frontend

## Limitations
- External dependencies: relies on Google ADK/Gemini APIs and any external data sources (ITSM DB, transaction DB, log store). Availability, quotas, and costs apply.
- InMemory session storage: current `InMemorySessionService` is ephemeral — not suitable for long-lived sessions or multi-instance deployments.
- No built-in authentication for underlying tools: adapt the tool implementations to securely access real data sources.
- Simplified error handling: production deployments should add retries, circuit breakers, and observability around each tool call.

## Detailed Implementation

Repository structure (high level):

- `agent_team/agent.py` — defines all agents, parallel/sequential flows, runner, and instrumentation.
- `agent_team/tools/` — tool implementations used by agents (ITSM, logs, transactions, greetings, goodbye).
- `agent_team/callbacks/` — guardrails for models and tools.
- `agent_team/tools/test/test_itsm.py` — example unit tests for ITSM tools.

Core components and responsibilities

- Agents
  - `itsm_agent` and `itsm_health_agent`: interact with ITSM tooling to check ticket status, search tickets by configuration item (CI), and check change windows.
  - `transaction_agent` and `transaction_health_agent`: retrieve transaction IDs and transaction details to assess traffic flow.
  - `logs_agent` and `logs_health_agent`: query device logs and return critical error events.
  - `greeting_agent` / `farewell_agent`: small social assistants for greets and goodbyes.
  - `parallel_health_check_executor` (a `ParallelAgent`): executes ITSM, transaction, and log health agents concurrently.
  - `summary_agent`: synthesizes the parallel outputs into a strictly-formatted health report.
  - `health_check_agent` (a `SequentialAgent`): wraps the parallel executor followed by the summary agent.
  - `root_agent`: the top-level coordinator that routes incoming user requests to the proper sub-agent.

- Tools (in `agent_team/tools/`)
  - `itsm.py`: functions like `search_tickets_by_ci`, `check_ticket`, `check_changes`, and `create_ticket`.
  - `transactions.py`: functions like `list_transaction_ids_by_device` and `get_transaction_details`.
  - `logs.py`: `query_device_logs` for fetching log entries.
  - `greetings.py`, `goodbye.py`: social tools.

- Callbacks
  - `callbacks/before_model.py`: `block_keyword_guardrail` to prevent sensitive or off-limits prompts.
  - `callbacks/before_tool.py`: `block_tool_guardrail` to prevent unauthorized tool usage.

- Instrumentation
  - `arize.otel.register(...)` is used to register tracing with Arize for observability.
  - `openinference.instrumentation.google_adk.GoogleADKInstrumentor` is used for automatic instrumentation.

Design and behavior notes

- Health check flow:
  1. `root_agent` routes health-check style requests to `health_check_agent`.
  2. `health_check_agent` runs `parallel_health_check_executor` which concurrently runs the ITSM, Transactions, and Logs health agents (each returns a structured response expected by `summary_agent`).
  3. `summary_agent` consumes the combined outputs and emits a final, human-readable report following a strict template.

- Output format enforcement:
  - Health-check sub-agents return structured outputs (e.g., lists of ticket objects, transaction summary dicts, lists of log dicts) so the summarizer can reliably parse and correlate findings.

How to run (local / dev)

This project is designed to be run via the ADK tooling. Use one of the following commands to start the system:

- Run the agent team flow:

```zsh
adk run agent_teams
```

- Start the web interface on port 8080:

```zsh
adk web --port 8080
```

If you prefer to prepare a development environment (optional):

```zsh
# Example (optional): create a virtual environment and install local dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Required environment variables (create a `.env` file or set them in your environment):

- `SPACE_ID` — Arize space id (for tracing).
- `API_KEY` — Arize API key.
- `APP_NAME` — application name (default: RootCause_Analyzer).
- `USER_ID` — user id for the session (default: user_1234).
- `SESSION_ID` — session id (default: session_1234).
- Any secrets or credentials required by your ITSM, DB, or logging backends.

Notes: The ADK commands will load and run the agent code (defined in `agent_team/agent.py`). If you prefer to run a specific script directly, `main.py` can be used as an alternative entry point, but the ADK flow is the intended developer/demo experience.

Testing

- There is a small test under `agent_team/tools/test/test_itsm.py`. Run tests with your preferred test runner (e.g., `pytest`).

```zsh
pytest -q
```

Extending the system

- Add new tools in `agent_team/tools/` and expose them to Agents via the `tools` list.
- For persistent sessions, replace `InMemorySessionService` with a database-backed implementation and pass it to the `Runner`.
- Implement production-grade auth and encryption for tool credentials.

Security and operational considerations

- Limit model capabilities and tool access via `before_model_callback` and `before_tool_callback` guardrails.
- Add rate limiting and quota handling for external APIs (Gemini, ITSM, logging backends).
- Deploy instrumentation to observe errors and latency: traces are registered via Arize and OpenInference instrumentation.

Deliverables in this repo

- `agent_team/agent.py` — agent definitions and orchestration (core logic).
- `agent_team/tools/` — tool implementations (ITSM, logs, transactions, greetings, goodbye).
- `agent_team/callbacks/` — guardrail callbacks for tools and models.

Next steps (suggested)

- Replace `InMemorySessionService` with a persistent session store for long-running runs.
- Add integration tests that mock external systems to verify end-to-end health-check flow.
- Harden tool implementations to use secure credential storage and robust retry logic.

## System Architecture & Agent Hierarchy

This focused section summarizes how the system is composed at runtime and how agents are organized to handle queries.

High-level runtime flow:

1. User issues a natural language query to the `root_agent` (main coordinator).
2. `root_agent` analyzes intent and routes the request to the appropriate specialized agent(s).
3. For device health checks, `health_check_agent` (a `SequentialAgent`) triggers `parallel_health_check_executor` (a `ParallelAgent`) which runs `itsm_health_agent`, `transaction_health_agent`, and `logs_health_agent` concurrently. Their structured outputs are passed to `summary_agent` which synthesizes the final report.
4. **ITSM Agent**
    - **Role**: IT Service Management operations coordinator
    - **Tools**:
        - `check_ticket(ticket_id)` - Retrieve ticket details and status
        - `check_changes(ci_name, since=datetime)` - Query change records for a CI
        - `create_ticket(summary, description, ci_name, priority, reporter)` - Create new tickets
        - `search_tickets_by_ci(ci_name)` - Find all tickets linked to a configuration item
    - **Output Key**: `last_itsm_response`
    - **Use Cases**: Ticket status tracking, change audits, CI-based incident correlation
5. **Transaction Agent**
    - **Role**: Real-time transaction and device health analysis
    - **Tools**:
        - `list_transaction_ids_by_device(device_name)` - Get all transaction IDs for a device
        - `get_transaction_details(transaction_id)` - Retrieve detailed transaction metadata
    - **Output Key**: `last_transaction_response`
    - **Guardrails**: Blocks transaction queries for "sensor-c" (via `block_tool_guardrail`)
    - **Use Cases**: Device performance analysis, transaction failure investigation
6. **Logs Agent**
    - **Role**: Distributed logging and transaction history queries
    - **Tools**:
        - `query_transaction_logs(device, start_time, end_time)` - Fetch time-range filtered logs
    - **Purpose**: Retrieve historical transaction records with optional time filtering
    - **Use Cases**: Root cause analysis, performance trending, incident timeline reconstruction

Agent hierarchy (visual):

<p align="center">
  <img src="images/agent_hierarchy.png" width="800" alt="RootCause Analyzer agent_hierarchy">
</p>

Execution notes:

- `ParallelAgent` reduces latency by running independent domain checks concurrently.
- `SequentialAgent` enforces order when later steps (summarization) depend on combined outputs.
- Structured outputs (lists/dicts) from health sub-agents ensure deterministic parsing and correlation in `summary_agent`.

Security & observability:

- Guardrails (`before_model_callback` and `before_tool_callback`) are evaluated at routing and tool-invocation time to prevent sensitive or unauthorized actions.
- Tracing is enabled via Arize and OpenInference instrumentation to track requests through agents and tools end-to-end.

## Appendix: Example Queries

### ITSM Queries
```
"Show me the tickets for sensor-A"
"Show me the details for ticket TCKT-1002"
"Create a high-priority ticket for Sensor-B latency"
"What changes were made to Sensor-A in the last week?"
```

### Transaction Queries
```
"List all transactions for sensor-A"
"Get details for transaction xyz-123"
"Show me failed transactions in the last 24 hours"
"Which devices had successful transactions in the past hour?"
```

### Logs Queries
```
"Get transaction logs for gateway-1"
"Show logs for sensor-B from Nov 15 10:00 to Nov 15 14:00"
"Did edge-12 have any failed transactions recently?"
```

### Restricted Queries
```
"What's my password?" → ❌ BLOCKED (keyword guardrail)
"List transactions for sensor-c" → ❌ BLOCKED (tool guardrail)
```
