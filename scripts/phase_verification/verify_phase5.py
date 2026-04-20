"""
Phase 5 verification script — file ingestion tool tests.

Tests parser logic offline, then runs a live import into
cortado_clone / Testing Scenarios and cleans up afterward.

Run with:
    uv run python scripts/verify_phase5.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from testrail_mcp.config import Settings
from testrail_mcp.client import TestRailClient
from testrail_mcp.parsers import parse
import testrail_mcp.server as _server

PASS = "✅"
FAIL = "❌"
SKIP = "⏭️ "

created_case_ids: list[int] = []


def check(label: str, fn):
    try:
        result = fn()
        print(f"{PASS} {label}")
        return result
    except AssertionError as e:
        print(f"{FAIL} {label}: {e}")
        return None
    except Exception as e:
        print(f"{FAIL} {label}: {type(e).__name__}: {e}")
        return None


# ── Sample content ─────────────────────────────────────────────────────────────

GHERKIN_SAMPLE = """\
Feature: User Authentication

  Scenario: User logs in with valid credentials
    Given the user is on the login page
    When they enter a valid email and password
    Then they should be redirected to the dashboard

  Scenario: User cannot log in with an incorrect password
    Given the user is on the login page
    When they enter an incorrect password
    Then they should see an error message
"""

MARKDOWN_SAMPLE = """\
## User logs in with valid credentials
Given the user is on the login page
When they enter a valid email and password
Then they should be redirected to the dashboard

## User cannot log in with an incorrect password
Given the user is on the login page
When they enter an incorrect password
Then they should see an error message
"""

NUMBERED_SAMPLE = """\
1. User can log in with valid credentials
2. User cannot log in with invalid password
3. User is locked out after five failed attempts
"""


def main():
    print("\n── Phase 5 Verification ──────────────────────────────────────\n")

    # ── Parser tests (no network required) ────────────────────────────────────

    print("Parser tests (offline):\n")

    # Gherkin
    gherkin_scenarios = check(
        "Gherkin parser: finds 2 scenarios",
        lambda: parse(GHERKIN_SAMPLE, "gherkin")
                if len(parse(GHERKIN_SAMPLE, "gherkin")) == 2
                else (_ for _ in ()).throw(AssertionError(
                    f"Expected 2, got {len(parse(GHERKIN_SAMPLE, 'gherkin'))}"
                )),
    )
    if gherkin_scenarios:
        check(
            "Gherkin parser: title extracted correctly",
            lambda: gherkin_scenarios[0].title == "User logs in with valid credentials"
                    or (_ for _ in ()).throw(AssertionError(
                        f"Got: '{gherkin_scenarios[0].title}'"
                    )),
        )
        check(
            "Gherkin parser: BDD content includes Given/When/Then",
            lambda: gherkin_scenarios[0].bdd_content is not None
                    and "Given" in gherkin_scenarios[0].bdd_content
                    or (_ for _ in ()).throw(AssertionError(
                        f"BDD content: {gherkin_scenarios[0].bdd_content}"
                    )),
        )

    # Markdown
    md_scenarios = check(
        "Markdown parser: finds 2 scenarios",
        lambda: parse(MARKDOWN_SAMPLE, "markdown")
                if len(parse(MARKDOWN_SAMPLE, "markdown")) == 2
                else (_ for _ in ()).throw(AssertionError(
                    f"Expected 2, got {len(parse(MARKDOWN_SAMPLE, 'markdown'))}"
                )),
    )
    if md_scenarios:
        check(
            "Markdown parser: BDD content detected from Given/When/Then lines",
            lambda: md_scenarios[0].bdd_content is not None
                    or (_ for _ in ()).throw(AssertionError("bdd_content is None")),
        )

    # Numbered list
    num_scenarios = check(
        "Numbered list parser: finds 3 scenarios",
        lambda: parse(NUMBERED_SAMPLE, "numbered")
                if len(parse(NUMBERED_SAMPLE, "numbered")) == 3
                else (_ for _ in ()).throw(AssertionError(
                    f"Expected 3, got {len(parse(NUMBERED_SAMPLE, 'numbered'))}"
                )),
    )
    if num_scenarios:
        check(
            "Numbered list parser: no BDD content (titles only)",
            lambda: all(s.bdd_content is None for s in num_scenarios)
                    or (_ for _ in ()).throw(AssertionError("Expected no BDD content")),
        )

    # Size limit gate
    check(
        "Size gate: content over 500KB is rejected",
        lambda: _test_size_gate(),
    )

    # Binary content gate
    check(
        "Binary gate: null bytes are rejected",
        lambda: _test_binary_gate(),
    )

    # Unsupported format
    check(
        "Format validation: unsupported format raises ValueError",
        lambda: _test_bad_format(),
    )

    # Empty content
    check(
        "Empty content: returns 0 parsed with helpful message",
        lambda: _test_empty_content(),
    )

    print()

    # ── Live import test ───────────────────────────────────────────────────────

    print("Live import test (cortado_clone / Testing Scenarios):\n")

    settings = Settings()
    client = TestRailClient(
        url=settings.testrail_url,
        email=settings.testrail_email,
        api_key=settings.testrail_api_key,
    )
    _server.client = client

    # Find sandbox section
    suites = client.get_all("get_suites/2", "suites")
    suite = next((s for s in suites if s["name"] == "Testing Scenarios"), None)
    if not suite:
        print("❌ Testing Scenarios suite not found — skipping live tests")
        print("\n── Done ──────────────────────────────────────────────────────\n")
        return

    sections = client.get_all("get_sections/2", "sections", params={"suite_id": suite["id"]})
    # Use the first available section, or create a temp one
    if sections:
        target_section = sections[0]
        created_temp_section = False
    else:
        target_section = client.post("add_section/2", {
            "name": "[MCP Test] Phase 5 Import",
            "suite_id": suite["id"],
        })
        created_temp_section = True

    print(f"   Target section: '{target_section['name']}' (id={target_section['id']})\n")

    # Import 2 Gherkin scenarios
    from testrail_mcp.tools.importer import import_from_file

    result = check(
        "import_from_file: imports 2 Gherkin scenarios",
        lambda: import_from_file(
            content=GHERKIN_SAMPLE,
            section_id=target_section["id"],
            fmt="gherkin",
            priority_id=2,
        ),
    )

    if result:
        check(
            "import_from_file: total_created == 2",
            lambda: result["total_created"] == 2
                    or (_ for _ in ()).throw(AssertionError(
                        f"Expected 2 created, got {result['total_created']}. "
                        f"Failures: {result['failed']}"
                    )),
        )
        check(
            "import_from_file: no failures",
            lambda: len(result["failed"]) == 0
                    or (_ for _ in ()).throw(AssertionError(
                        f"Failures: {result['failed']}"
                    )),
        )
        if result.get("created"):
            for c in result["created"]:
                created_case_ids.append(c["id"])
            print(f"\n   Created cases: {[c['title'] for c in result['created']]}\n")

        # Verify BDD content was written to the case
        if created_case_ids:
            case = client.get(f"get_case/{created_case_ids[0]}")
            check(
                "import_from_file: BDD template applied (template_id=4)",
                lambda: case.get("template_id") == 4
                        or (_ for _ in ()).throw(AssertionError(
                            f"Expected template_id=4, got {case.get('template_id')}"
                        )),
            )
            check(
                "import_from_file: Given/When/Then content saved to BDD field",
                lambda: case.get("custom_testrail_bdd_scenario") is not None
                        and "Given" in case.get("custom_testrail_bdd_scenario", "")
                        or (_ for _ in ()).throw(AssertionError(
                            f"BDD field value: {case.get('custom_testrail_bdd_scenario')}"
                        )),
            )

    # ── Cleanup ────────────────────────────────────────────────────────────────

    print("\n── Cleanup ───────────────────────────────────────────────────\n")
    for case_id in created_case_ids:
        try:
            client.post(f"delete_case/{case_id}")
            print(f"{PASS} Deleted case {case_id}")
        except Exception as e:
            print(f"{FAIL} Could not delete case {case_id}: {e}")

    if created_temp_section:
        try:
            client.post(f"delete_section/{target_section['id']}")
            print(f"{PASS} Deleted temp section {target_section['id']}")
        except Exception as e:
            print(f"{FAIL} Could not delete temp section: {e}")

    print("\n── Done ──────────────────────────────────────────────────────\n")


def _test_size_gate():
    from testrail_mcp.tools.importer import import_from_file
    big_content = "x" * (500 * 1024 + 1)
    try:
        import_from_file(content=big_content, section_id=1)
        raise AssertionError("Expected ValueError but call succeeded")
    except ValueError as e:
        assert "too large" in str(e).lower(), f"Unexpected message: {e}"
    return True


def _test_binary_gate():
    from testrail_mcp.tools.importer import import_from_file
    try:
        import_from_file(content="hello\x00world", section_id=1)
        raise AssertionError("Expected ValueError but call succeeded")
    except ValueError as e:
        assert "binary" in str(e).lower(), f"Unexpected message: {e}"
    return True


def _test_bad_format():
    try:
        parse("content", "csv")
        raise AssertionError("Expected ValueError but call succeeded")
    except ValueError as e:
        assert "unsupported format" in str(e).lower(), f"Unexpected message: {e}"
    return True


def _test_empty_content():
    from testrail_mcp.tools.importer import import_from_file
    # Inject a client so the tool doesn't raise RuntimeError before parsing
    import testrail_mcp.server as _s
    from unittest.mock import MagicMock
    _s.client = MagicMock()
    result = import_from_file(content="# No scenarios here", section_id=1, fmt="gherkin")
    assert result["total_parsed"] == 0, f"Expected 0, got {result['total_parsed']}"
    assert "message" in result
    return True


if __name__ == "__main__":
    main()
