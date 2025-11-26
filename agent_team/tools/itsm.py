from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import uuid
import logging
from google.adk.tools.tool_context import ToolContext

"""
Simple mock ITSM toolset used by LLM agents.

File: /Users/mathewspious/MyWorks/AI_projects/RootCause_Analyzer/agent_team/tools/itsm.py

This module provides lightweight, deterministic, in-memory mock implementations of
common ITSM operations that an LLM-based agent can call during orchestration:
- check_ticket(ticket_id): retrieve ticket details
- check_changes(ci_name, since=None): list change records that reference a CI
- create_ticket(summary, description, ci_name, priority='Medium', reporter=None): create a new ticket

Each function returns simple JSON-serializable Python dicts (and lists of dicts).
Docstrings below describe expected input, return schema, errors and examples. The
module is intentionally dependent-free (standard library only) so it can be used
safely in unit tests and agent simulations.
"""


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# --- In-memory mock datastore (pre-populated for predictable behavior) ---


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Ticket:
    id: str
    summary: str
    description: str
    ci_name: Optional[str]
    priority: str
    status: str
    reporter: Optional[str]
    created_at: str
    updated_at: str
    external_link: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChangeRecord:
    id: str
    ci_name: str
    change_type: str
    description: str
    changed_at: str
    author: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Seed datastore with a couple of deterministic records so the agent sees realistic results.
_TICKETS: Dict[str, Ticket] = {}
_CHANGES: List[ChangeRecord] = []


def _seed_data():
    # Create two tickets
    t1 = Ticket(
        id="TCKT-1001",
        summary="Database connection errors observed",
        description="Intermittent connection failures to DB-Prod cluster.",
        ci_name="sensor-B",
        priority="High",
        status="Open",
        reporter="ops-monitor",
        created_at=_now_iso(),
        updated_at=_now_iso(),
        external_link="https://itsm.example/tickets/TCKT-1001",
    )
    t2 = Ticket(
        id="TCKT-1002",
        summary="Planned network maintenance",
        description="Network team will perform maintenance on routers",
        ci_name="sensor-A",
        priority="Low",
        status="Closed",
        reporter="net-team",
        created_at=(datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
        updated_at=(datetime.now(timezone.utc) - timedelta(days=6)).isoformat(),
        external_link="https://itsm.example/tickets/TCKT-1002",
    )
    _TICKETS[t1.id] = t1
    _TICKETS[t2.id] = t2

    # Create two change records
    c1 = ChangeRecord(
        id="CHG-2001",
        ci_name="sensor-B",
        change_type="configuration",
        description="Updated DB connection pool parameters",
        changed_at=(datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
        author="dba1",
    )
    c2 = ChangeRecord(
        id="CHG-2002",
        ci_name="sensor-A",
        change_type="deploy",
        description="Deployed v2.3.1 to sensor-A",
        changed_at=(
            datetime.now(timezone.utc) - timedelta(days=1, hours=2)
        ).isoformat(),
        author="ci-pipeline",
    )
    _CHANGES.extend([c1, c2])


_seed_data()

# --- Exceptions used by tool functions ---


class ITSMError(Exception):
    """Base class for ITSM tool errors."""


class TicketNotFound(ITSMError):
    """Raised when a ticket cannot be found by ID."""


# --- Public API: mock ITSM functions ---


def check_ticket(ticket_id: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Retrieve ticket details by ticket_id.

    Parameters
    - ticket_id: string identifier of the ticket (e.g., "TCKT-1001").

    Returns
    A dict with the following keys:
    - status: "ok" or "not_found"
    - ticket: ticket dict when found (see Ticket.to_dict schema)
    - error: optional error message when not found

    Behavior:
    - Deterministic: looks up in an in-memory datastore seeded with examples.
    - Does not perform network I/O.

    Example:
    >>> check_ticket("TCKT-1001")
    {
        "status": "ok",
        "ticket": { "id": "TCKT-1001", "summary": "...", ... }
    }
    """
    logger.debug("check_ticket called with ticket_id=%s", ticket_id)
    ticket = _TICKETS.get(ticket_id)
    if not ticket:
        logger.info("Ticket %s not found", ticket_id)
        return {
            "status": "not_found",
            "ticket": None,
            "error": f"Ticket {ticket_id} not found.",
        }
    return {"status": "ok", "ticket": ticket.to_dict(), "error": None}


def create_ticket(
    summary: str,
    tool_context: ToolContext,
    description: str,
    ci_name: Optional[str] = None,
    priority: str = "Medium",
    reporter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new mock ticket.

    Parameters
    - summary: short summary/title for the ticket (required)
    - description: longer description (required)
    - ci_name: optional configuration item / resource name this ticket is related to
    - priority: one of "Low", "Medium", "High" (defaults to "Medium")
    - reporter: identity string for who reported the issue (defaults to "agent")

    Returns
    A dict with keys:
    - status: "created" or "error"
    - ticket_id: generated ticket id when created (e.g., "TCKT-<number>")
    - ticket: full ticket dict (same schema as check_ticket returns)
    - message: human-friendly message

    Notes for agent usage:
    - This is a mock create that updates the module in-memory datastore and returns
      a synthetic external link. Repeated calls will persist for the lifetime of
      the Python process.
    """
    logger.debug(
        "create_ticket called summary=%s ci_name=%s priority=%s reporter=%s",
        summary,
        ci_name,
        priority,
        reporter,
    )
    if not summary or not description:
        return {
            "status": "error",
            "ticket_id": None,
            "ticket": None,
            "message": "summary and description are required.",
        }

    # Create a deterministic-ish ticket id using a UUID suffix for uniqueness.
    uid = uuid.uuid4().hex[:6].upper()
    ticket_number = 1000 + len(_TICKETS) + 1
    ticket_id = f"TCKT-{ticket_number}-{uid}"
    now = _now_iso()
    ticket = Ticket(
        id=ticket_id,
        summary=summary,
        description=description,
        ci_name=ci_name,
        priority=priority,
        status="Open",
        reporter=reporter if reporter else "agent",
        created_at=now,
        updated_at=now,
        external_link=f"https://itsm.example/tickets/{ticket_id}",
    )
    _TICKETS[ticket_id] = ticket

    logger.info("Created ticket %s", ticket_id)
    return {
        "status": "created",
        "ticket_id": ticket_id,
        "ticket": ticket.to_dict(),
        "message": f"Ticket {ticket_id} created successfully.",
    }


def check_changes(ci_name: str, since: Optional[str] = None) -> Dict[str, Any]:
    """
    List changes associated with a configuration item (CI).

    Parameters
    - ci_name: the name of the CI to search changes for (required).
    - since: optional ISO-8601 timestamp string. When provided, only changes
             whose changed_at >= since are returned. If omitted, returns recent changes.

    Returns
    A dict with keys:
    - status: "ok" or "not_found" or "error"
    - ci_name: echoed input
    - changes: list of change dicts (each follows ChangeRecord.to_dict schema)
    - message: optional message (e.g., when none are found)

    Example:
    >>> check_changes("db-prod-cluster", since="2025-01-01T00:00:00+00:00")
    {
        "status": "ok",
        "ci_name": "db-prod-cluster",
        "changes": [ { "id": "CHG-2001", "ci_name": "db-prod-cluster", ... } ],
        "message": None
    }
    """
    logger.debug("check_changes called ci_name=%s since=%s", ci_name, since)
    if not ci_name:
        return {
            "status": "error",
            "ci_name": ci_name,
            "changes": [],
            "message": "ci_name is required.",
        }

    # Parse 'since' into datetime if provided
    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
        except Exception as e:
            logger.warning("Invalid since timestamp provided: %s", since)
            return {
                "status": "error",
                "ci_name": ci_name,
                "changes": [],
                "message": "since must be an ISO-8601 timestamp.",
            }

    # Filter changes by ci_name (case-insensitive match) and timestamp
    matched = []
    for ch in _CHANGES:
        if ch.ci_name.lower() == ci_name.lower():
            if since_dt:
                try:
                    ch_dt = datetime.fromisoformat(ch.changed_at)
                except Exception:
                    # if a stored record is malformed, skip it
                    continue
                if ch_dt >= since_dt:
                    matched.append(ch.to_dict())
            else:
                matched.append(ch.to_dict())

    if not matched:
        logger.info("No changes found for CI=%s", ci_name)
        return {
            "status": "not_found",
            "ci_name": ci_name,
            "changes": [],
            "message": f"No changes found for {ci_name}.",
        }

    return {"status": "ok", "ci_name": ci_name, "changes": matched, "message": None}


# --- Utility functions that an agent may find useful ---


def search_tickets_by_ci(ci_name: str) -> Dict[str, Any]:
    """
    Convenience helper to find all tickets referencing a CI.

    Returns:
    - status: "ok" or "not_found"
    - ci_name: echoed input
    - tickets: list of ticket dicts
    - message: optional
    """
    logger.debug("search_tickets_by_ci called ci_name=%s", ci_name)
    if not ci_name:
        return {
            "status": "error",
            "ci_name": ci_name,
            "tickets": [],
            "message": "ci_name is required.",
        }
    matches = [
        t.to_dict()
        for t in _TICKETS.values()
        if t.ci_name and t.ci_name.lower() == ci_name.lower()
    ]
    if not matches:
        return {
            "status": "not_found",
            "ci_name": ci_name,
            "tickets": [],
            "message": f"No tickets found for {ci_name}.",
        }
    return {"status": "ok", "ci_name": ci_name, "tickets": matches, "message": None}
