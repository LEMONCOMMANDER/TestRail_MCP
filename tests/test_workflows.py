"""Tests for import_from_hierarchy in workflows.py — no live TestRail connection needed."""
import pytest
from unittest.mock import MagicMock, patch

_PATCH = "testrail_mcp.tools.workflows.get_client"


def _make_client():
    """Return a mock TestRailClient with auto-incrementing IDs for sections/cases."""
    c = MagicMock()
    c.get_suite_mode.return_value = 1
    c.get.side_effect = lambda ep: {"id": 1, "name": "Test Project"}
    c.get_all.return_value = []
    n = {"s": 100, "c": 200}

    def post(ep, body=None):
        if ep.startswith("add_section"):
            n["s"] += 1
            return {"id": n["s"], "name": body.get("name", ""), "parent_id": body.get("parent_id")}
        if ep.startswith("add_case"):
            n["c"] += 1
            return {"id": n["c"], "title": body.get("title", "")}
        return {}

    c.post.side_effect = post
    return c


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

def test_empty_content_returns_early():
    from testrail_mcp.tools.workflows import import_from_hierarchy
    with patch(_PATCH, return_value=_make_client()):
        r = import_from_hierarchy(content="", project=1)
    assert r["total_parsed"] == 0
    assert r["sections_created"] == []
    assert "No sections" in r["message"]


def test_binary_content_rejected():
    from testrail_mcp.tools.workflows import import_from_hierarchy
    with patch(_PATCH, return_value=_make_client()):
        with pytest.raises(ValueError, match="binary"):
            import_from_hierarchy(content="hello\x00world", project=1)


def test_oversized_content_rejected():
    from testrail_mcp.tools.workflows import import_from_hierarchy
    with patch(_PATCH, return_value=_make_client()):
        with pytest.raises(ValueError, match="too large"):
            import_from_hierarchy(content="x" * (500 * 1024 + 1), project=1)


# ---------------------------------------------------------------------------
# Section creation
# ---------------------------------------------------------------------------

def test_h2_creates_top_level_section():
    from testrail_mcp.tools.workflows import import_from_hierarchy
    md = "## Auth\n**C**\nGiven a\nWhen b\nThen c\n"
    with patch(_PATCH, return_value=_make_client()):
        r = import_from_hierarchy(content=md, project=1)
    assert r["sections_created"][0]["name"] == "Auth"
    assert r["sections_created"][0]["parent_id"] is None


def test_h3_parent_id_set_to_h2_id():
    from testrail_mcp.tools.workflows import import_from_hierarchy
    md = "## Auth\n### Login\n**C**\nGiven a\nWhen b\nThen c\n"
    with patch(_PATCH, return_value=_make_client()):
        r = import_from_hierarchy(content=md, project=1)
    auth_id = r["sections_created"][0]["id"]
    assert r["sections_created"][1]["name"] == "Login"
    assert r["sections_created"][1]["parent_id"] == auth_id


def test_multiple_h2_sections_all_created():
    from testrail_mcp.tools.workflows import import_from_hierarchy
    md = "## A\n**C1**\nGiven a\nWhen b\nThen c\n## B\n**C2**\nGiven x\nWhen y\nThen z\n"
    with patch(_PATCH, return_value=_make_client()):
        r = import_from_hierarchy(content=md, project=1)
    names = [s["name"] for s in r["sections_created"]]
    assert "A" in names and "B" in names


def test_empty_section_still_created():
    from testrail_mcp.tools.workflows import import_from_hierarchy
    with patch(_PATCH, return_value=_make_client()):
        r = import_from_hierarchy(content="## Empty\n", project=1)
    assert len(r["sections_created"]) == 1
    assert r["total_parsed"] == 0


# ---------------------------------------------------------------------------
# Case creation
# ---------------------------------------------------------------------------

def test_case_created_in_section():
    from testrail_mcp.tools.workflows import import_from_hierarchy
    md = "## Auth\n**Login**\nGiven a\nWhen b\nThen c\n"
    with patch(_PATCH, return_value=_make_client()):
        r = import_from_hierarchy(content=md, project=1)
    assert r["total_created"] == 1
    assert r["by_section"][0]["cases"][0]["title"] == "Login"


def test_multiple_cases_in_one_section():
    from testrail_mcp.tools.workflows import import_from_hierarchy
    md = "## Auth\n**C1**\nGiven a\nWhen b\nThen c\n\n**C2**\nGiven x\nWhen y\nThen z\n"
    with patch(_PATCH, return_value=_make_client()):
        r = import_from_hierarchy(content=md, project=1)
    assert r["total_parsed"] == 2 and r["total_created"] == 2


def test_cases_split_across_sections():
    from testrail_mcp.tools.workflows import import_from_hierarchy
    md = (
        "## Auth\n**C1**\nGiven a\nWhen b\nThen c\n"
        "## Dashboard\n**C2**\nGiven x\nWhen y\nThen z\n**C3**\nGiven p\nWhen q\nThen r\n"
    )
    with patch(_PATCH, return_value=_make_client()):
        r = import_from_hierarchy(content=md, project=1)
    assert r["total_parsed"] == 3 and r["total_created"] == 3


def test_type_id_and_priority_id_forwarded():
    from testrail_mcp.tools.workflows import import_from_hierarchy
    client = _make_client()
    with patch(_PATCH, return_value=client):
        import_from_hierarchy(
            content="## S\n**C**\nGiven a\nWhen b\nThen c\n",
            project=1, type_id=2, priority_id=3,
        )
    case_calls = [c for c in client.post.call_args_list if "add_case" in c.args[0]]
    body = case_calls[0].args[1]
    assert body["type_id"] == 2 and body["priority_id"] == 3


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------

def test_section_creation_failure_skips_its_cases():
    from testrail_mcp.tools.workflows import import_from_hierarchy
    md = "## Good\n**C1**\nGiven a\nWhen b\nThen c\n## Bad\n**C2**\nGiven x\nWhen y\nThen z\n"
    client = _make_client()
    nv = {"v": 0}

    def _post(ep, body=None):
        if ep.startswith("add_section"):
            nv["v"] += 1
            if nv["v"] == 2:
                raise Exception("API error")
            return {"id": 100 + nv["v"], "name": body.get("name", "")}
        return {"id": 200, "title": body.get("title", "")}

    client.post.side_effect = _post
    with patch(_PATCH, return_value=client):
        r = import_from_hierarchy(content=md, project=1)
    assert any(f["title"] == "C2" for f in r["failed"])


def test_case_creation_failure_reported():
    from testrail_mcp.tools.workflows import import_from_hierarchy
    client = _make_client()

    def _post(ep, body=None):
        if ep.startswith("add_section"):
            return {"id": 101, "name": body.get("name", "")}
        raise Exception("case api error")

    client.post.side_effect = _post
    with patch(_PATCH, return_value=client):
        r = import_from_hierarchy(
            content="## S\n**Fail**\nGiven a\nWhen b\nThen c\n",
            project=1,
        )
    assert r["total_created"] == 0
    assert r["failed"][0]["title"] == "Fail"
    assert "case api error" in r["failed"][0]["error"]


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

def test_response_has_resolved_block():
    from testrail_mcp.tools.workflows import import_from_hierarchy
    with patch(_PATCH, return_value=_make_client()):
        r = import_from_hierarchy(content="## S\n", project=1)
    assert "resolved" in r
    assert "project" in r["resolved"]
    assert "project_id" in r["resolved"]


def test_by_section_has_required_keys():
    from testrail_mcp.tools.workflows import import_from_hierarchy
    with patch(_PATCH, return_value=_make_client()):
        r = import_from_hierarchy(
            content="## S\n**C**\nGiven a\nWhen b\nThen c\n",
            project=1,
        )
    entry = r["by_section"][0]
    for k in ("section_name", "section_id", "cases_parsed", "cases_created", "cases"):
        assert k in entry


def test_message_mentions_counts():
    from testrail_mcp.tools.workflows import import_from_hierarchy
    with patch(_PATCH, return_value=_make_client()):
        r = import_from_hierarchy(
            content="## S\n**C**\nGiven a\nWhen b\nThen c\n",
            project=1,
        )
    assert "1" in r["message"]
