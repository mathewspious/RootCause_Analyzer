from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# /Users/mathewspious/MyWorks/AI_projects/RootCause_Analyzer/agent_team/tools/logs.py

ALLOWED_DEVICES = {"sensor-A", "sensor-B", "gateway-1", "edge-12"}

# Mocked, static transaction records for each device (times are UTC)
_SAMPLE_TX = {
    "sensor-A": [
        {
            "start_time": datetime.now() - timedelta(minutes=30),
            "end_time": datetime.now() - timedelta(minutes=29, seconds=40),
            "transaction_id": "tx-sa-1001",
            "status": "success",
            "response_time_ms": 120,
        },
        {
            "start_time": datetime.now() - timedelta(hours=2),
            "end_time": datetime.now() - timedelta(hours=2, minutes=-1),
            "transaction_id": "tx-sa-1002",
            "status": "failure",
            "response_time_ms": 800,
        },
    ],
    "sensor-B": [
        {
            "start_time": datetime.now() - timedelta(minutes=10),
            "end_time": datetime.now() - timedelta(minutes=9, seconds=55),
            "transaction_id": "tx-sb-2001",
            "status": "success",
            "response_time_ms": 95,
        }
    ],
    "gateway-1": [
        {
            "start_time": datetime.now() - timedelta(days=1, minutes=5),
            "end_time": datetime.now() - timedelta(days=1, minutes=4, seconds=50),
            "transaction_id": "tx-gw-3001",
            "status": "success",
            "response_time_ms": 350,
        }
    ],
    "edge-12": [],
}


def _to_dt(value: Optional[Any]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # try ISO formats
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            raise ValueError(f"Invalid datetime string: {value!r}")
    raise TypeError("start_time/end_time must be datetime or ISO string")


def _serialize_tx(tx: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "start_time": tx["start_time"].isoformat(),
        "end_time": tx["end_time"].isoformat(),
        "transaction_id": tx["transaction_id"],
        "status": tx["status"],
        "response_time_ms": tx["response_time_ms"],
    }


def query_device_logs(
    device: str, start_time: Optional[Any] = None, end_time: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Mock API call to a distributed logging system returning device log details.

    Parameters:
    - device: one of "sensor-A", "sensor-B", "gateway-1", "edge-12"
    - start_time / end_time: optional, datetime or ISO8601 string. If provided, logs will be
      filtered to those that start on/after start_time and end on/before end_time.

    Returns:
    - dict with keys:
      - "device": device name
      - "logs": list of logs (each has start_time, end_time, transaction_id, status, response_time_ms)
      OR
      - "device": device, "status": "no result found" if no matching logs.
    """
    if device not in ALLOWED_DEVICES:
        raise ValueError(f"unsupported device: {device!r}")

    start_dt = _to_dt(start_time)
    end_dt = _to_dt(end_time)

    records = _SAMPLE_TX.get(device, [])

    def matches(tx: Dict[str, Any]) -> bool:
        if start_dt and tx["start_time"] < start_dt:
            return False
        if end_dt and tx["end_time"] > end_dt:
            return False
        return True

    matched = [_serialize_tx(tx) for tx in records if matches(tx)]

    if not matched:
        return {"device": device, "status": "no result found"}

    return {"device": device, "transactions": matched}


# Example usage (can be removed when integrating into larger codebase)
if __name__ == "__main__":
    # Query without time range
    print(query_device_logs("sensor-A"))

    # Query with ISO string time range (last 1 hour)
    one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
    now_iso = datetime.now().isoformat()
    print(
        query_device_logs("sensor-A", start_time=one_hour_ago, end_time=now_iso)
    )

    # Device with no records
    print(query_device_logs("edge-12"))
