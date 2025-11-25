import pytest
from datetime import datetime, timedelta, timezone
from agent_team.tools import itsm


def test_check_ticket_found():
    resp = itsm.check_ticket("TCKT-1001")
    assert resp["status"] == "ok"
    assert resp["ticket"] is not None
    assert resp["ticket"]["id"] == "TCKT-1001"
    assert "summary" in resp["ticket"]


def test_check_ticket_not_found():
    resp = itsm.check_ticket("TCKT-DOES-NOT-EXIST")
    assert resp["status"] == "not_found"
    assert resp["ticket"] is None
    assert "error" in resp and resp["error"]


def test_create_ticket_missing_fields():
    resp = itsm.create_ticket("", "")
    assert resp["status"] == "error"
    assert resp["ticket"] is None
    assert "required" in resp["message"].lower()


def test_create_ticket_success_and_lookup():
    summary = "Test created ticket"
    description = "This ticket is created by a unit test"
    ci_name = "unit-ci-1"
    resp = itsm.create_ticket(
        summary, description, ci_name=ci_name, priority="High", reporter="unittest"
    )
    assert resp["status"] == "created"
    tid = resp["ticket_id"]
    assert tid is not None
    ticket = resp["ticket"]
    assert ticket["summary"] == summary
    assert ticket["description"] == description
    assert ticket["ci_name"] == ci_name
    assert ticket["priority"] == "High"
    assert ticket["reporter"] == "unittest"
    assert ticket["external_link"].endswith(tid)
    # ensure ticket is retrievable via check_ticket
    lookup = itsm.check_ticket(tid)
    assert lookup["status"] == "ok"
    assert lookup["ticket"]["id"] == tid


def test_check_changes_found_without_since():
    resp = itsm.check_changes("db-prod-cluster")
    assert resp["status"] == "ok"
    assert resp["ci_name"].lower() == "db-prod-cluster"
    assert isinstance(resp["changes"], list)
    # Expect at least the seeded change CHG-2001 to be present
    ids = {c["id"] for c in resp["changes"]}
    assert "CHG-2001" in ids


def test_check_changes_since_includes_and_excludes():
    # since 1 day ago should include the change seeded ~5 hours ago
    since_include = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    resp_inc = itsm.check_changes("db-prod-cluster", since=since_include)
    assert resp_inc["status"] == "ok"
    ids_inc = {c["id"] for c in resp_inc["changes"]}
    assert "CHG-2001" in ids_inc

    # since now should exclude that past change
    since_exclude = datetime.now(timezone.utc).isoformat()
    resp_exc = itsm.check_changes("db-prod-cluster", since=since_exclude)
    assert resp_exc["status"] in ("not_found", "ok")
    if resp_exc["status"] == "ok":
        # If any change exactly matches the timestamp semantics, ensure CHG-2001 is not returned
        ids_exc = {c["id"] for c in resp_exc["changes"]}
        assert "CHG-2001" not in ids_exc
    else:
        assert resp_exc["changes"] == []


def test_check_changes_invalid_since():
    resp = itsm.check_changes("db-prod-cluster", since="invalid-timestamp")
    assert resp["status"] == "error"
    assert "since" in resp["message"].lower()


def test_search_tickets_by_ci_found_and_not_found():
    # router-edge-1 is seeded as TCKT-1002
    resp = itsm.search_tickets_by_ci("router-edge-1")
    assert resp["status"] == "ok"
    assert any(t["id"] == "TCKT-1002" for t in resp["tickets"])

    # a CI that does not exist should return not_found
    resp_none = itsm.search_tickets_by_ci("ci-does-not-exist-xyz")
    assert resp_none["status"] == "not_found"
    assert resp_none["tickets"] == []
