from __future__ import annotations
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pprint import pprint
from google.adk.tools.tool_context import ToolContext

"""
Mock transactions tool for LLM agents.

File: /Users/mathewspious/MyWorks/AI_projects/RootCause_Analyzer/agent_team/tools/transactions.py

Provides:
- list_transaction_ids_by_device(device_name) -> list[str]
- get_transaction_details(transaction_id) -> dict | None
- tool_handler(payload: dict) -> dict  (simple tool entrypoint for agents)

Transaction detail schema:
{
    "start_date": "ISO8601 string",
    "end_date": "ISO8601 string",
    "device_name": "string",
    "transaction_id": "string",
    "transaction_status": "SUCCESS" | "FAILED" | "IN_PROGRESS",
    "error_details": "string"  # empty unless FAILED
}
"""


# Internal in-memory store of mock transactions
_TRANSACTIONS: List[Dict] = []


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat() + "Z"


def generate_mock_transactions(
    num: int = 20, devices: Optional[List[str]] = None, seed: int = 42
) -> None:
    """
    Populate the internal store with deterministic mock transactions.
    Call this once at import or from tests to (re)seed the dataset.
    """
    global _TRANSACTIONS
    random.seed(seed)
    devices = devices or ["sensor-A", "sensor-B", "gateway-1", "edge-12"]
    now = datetime.utcnow()
    transactions = []
    statuses = ["SUCCESS", "FAILED", "IN_PROGRESS"]
    for _ in range(num):
        device = random.choice(devices)
        # start time within past 30 days
        start = now - timedelta(
            days=random.uniform(0, 30), seconds=random.uniform(0, 86400)
        )
        duration = timedelta(seconds=random.randint(1, 7200))
        # For IN_PROGRESS, end is None (use start + duration anyway but mark as in progress)
        end = start + duration
        status = random.choices(statuses, weights=[0.7, 0.15, 0.15], k=1)[0]
        txid = str(uuid.uuid4())
        error = ""
        if status == "FAILED":
            error = random.choice(
                [
                    "Timeout connecting to device",
                    "Malformed payload",
                    "Authentication failed",
                    "Disk write error",
                ]
            )
        if status == "IN_PROGRESS":
            # make end slightly in the future sometimes
            end = start + duration + timedelta(seconds=random.randint(0, 3600))
        transactions.append(
            {
                "start_date": _iso(start),
                "end_date": _iso(end),
                "device_name": device,
                "transaction_id": txid,
                "transaction_status": status,
                "error_details": error,
            }
        )
    _TRANSACTIONS = transactions


# Initialize default dataset at import
generate_mock_transactions()


def list_transaction_ids_by_device(
    device_name: str, tool_context: ToolContext
) -> List[str]:
    """
    Return a list of transaction IDs for transactions related to device_name.
    """
    return [
        tx["transaction_id"]
        for tx in _TRANSACTIONS
        if tx["device_name"].lower() == device_name.lower()
    ]


def get_transaction_details(
    transaction_id: str, tool_context: ToolContext
) -> Optional[Dict]:
    """
    Return full transaction details dict for the given transaction_id,
    or None if not found.
    """
    for tx in _TRANSACTIONS:
        if tx["transaction_id"] == transaction_id:
            return tx.copy()
    return None


def tool_handler(payload: Dict) -> Dict:
    """
    Simple agent-facing handler.

    Expected payload examples:
    - {"action": "list", "device_name": "sensor-A"}
    - {"action": "get", "transaction_id": "<uuid>"}

    Returns a dict containing result or error key.
    """
    action = payload.get("action")
    if action == "list":
        device = payload.get("device_name")
        if not device:
            return {"error": "missing device_name for list action"}
        ids = list_transaction_ids_by_device(device)
        return {"device_name": device, "transaction_ids": ids}
    elif action == "get":
        txid = payload.get("transaction_id")
        if not txid:
            return {"error": "missing transaction_id for get action"}
        details = get_transaction_details(txid)
        if details is None:
            return {"error": f"transaction_id {txid} not found"}
        return {"transaction": details}
    else:
        return {"error": "unknown action; supported: list, get"}


if __name__ == "__main__":
    # quick manual demo when run as script
    print(
        "Sample devices in dataset:", sorted({t["device_name"] for t in _TRANSACTIONS})
    )
    sample_device = _TRANSACTIONS[0]["device_name"]
    print("Listing transaction ids for device:", sample_device)
    print(list_transaction_ids_by_device(sample_device)[:5])
    sample_tx = _TRANSACTIONS[0]["transaction_id"]
    print("Details for a sample transaction id:")
    pprint(get_transaction_details(sample_tx))
