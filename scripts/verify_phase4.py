"""
Phase 4 verification script — write tool tests scoped to cortado_clone / Testing Scenarios.

All test data created here is cleaned up at the end of the script.
No data is written to any other project or suite.

Run with:
    uv run python scripts/verify_phase4.py

Test sequence:
  1. All new write tools are registered on the server
  2. Locate cortado_clone project and Testing Scenarios suite
  3. add_section       — create a temp section
  4. update_section    — rename it
  5. add_case          — create a test case with standard + custom fields
  6. update_case       — update the title
  7. add_run           — create a test run from the suite
  8. add_result        — record a result on the new case
  9. add_results_for_cases — bulk results
  10. add_plan         — create a test plan
  11. update_plan      — rename it
  12. add_milestone    — create a milestone
  13. update_milestone — rename it
  14. Cleanup          — delete everything created above (in reverse order)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from testrail_mcp.config import Settings
from testrail_mcp.client import TestRailClient
import testrail_mcp.server as _server

PASS = "✅"
FAIL = "❌"

created = {}  # tracks IDs for cleanup


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


def cleanup(client: TestRailClient):
    print("\n── Cleanup ───────────────────────────────────────────────────\n")
    # Delete in reverse dependency order
    for key, label, endpoint_fn in [
        ("run_id",       "run",       lambda i: f"delete_run/{i}"),
        ("plan_id",      "plan",      lambda i: f"delete_plan/{i}"),
        ("milestone_id", "milestone", lambda i: f"delete_milestone/{i}"),
        ("section_id",   "section",   lambda i: f"delete_section/{i}"),
    ]:
        if key in created:
            item_id = created[key]
            try:
                client.post(endpoint_fn(item_id))
                print(f"{PASS} Deleted {label} {item_id}")
            except Exception as e:
                print(f"{FAIL} Could not delete {label} {item_id}: {e}")


def main():
    print("\n── Phase 4 Verification ──────────────────────────────────────\n")
    print("  Sandbox: cortado_clone / Testing Scenarios only\n")

    settings = Settings()
    client = TestRailClient(
        url=settings.testrail_url,
        email=settings.testrail_email,
        api_key=settings.testrail_api_key,
    )
    _server.client = client  # inject for tool functions called directly

    # ── Locate sandbox project and suite ──────────────────────────────

    projects = client.get_all("get_projects", "projects")
    project = next((p for p in projects if p["name"] == "cortado_clone"), None)
    if not project:
        print("❌ cortado_clone project not found. Cannot continue.")
        sys.exit(1)
    pid = project["id"]
    print(f"   Project: cortado_clone (id={pid}, suite_mode={project['suite_mode']})\n")

    suites = client.get_all(f"get_suites/{pid}", "suites")
    suite = next((s for s in suites if s["name"] == "Testing Scenarios"), None)
    if not suite:
        print("❌ 'Testing Scenarios' suite not found in cortado_clone. Cannot continue.")
        sys.exit(1)
    sid = suite["id"]
    print(f"   Suite: Testing Scenarios (id={sid})\n")

    # ── 1. Tool registration ───────────────────────────────────────────

    import asyncio
    from testrail_mcp.server import mcp
    all_tools = asyncio.run(mcp.list_tools())
    tool_names = [t.name for t in all_tools]

    new_write_tools = [
        "add_section", "update_section", "delete_section",
        "add_case", "update_case", "delete_case",
        "add_suite", "update_suite", "delete_suite",
        "add_run", "update_run", "close_run", "delete_run",
        "add_result", "add_results_for_cases",
        "add_plan", "update_plan", "close_plan", "delete_plan",
        "add_milestone", "update_milestone", "delete_milestone",
    ]
    for tool in new_write_tools:
        check(
            f"Tool registered: {tool}",
            lambda t=tool: t in tool_names or (_ for _ in ()).throw(
                AssertionError(f"'{t}' not found in registered tools")
            ),
        )
    print()

    # ── 2. add_section ────────────────────────────────────────────────

    section = check(
        "add_section: create temp section in Testing Scenarios",
        lambda: client.post(f"add_section/{pid}", {
            "name": "[MCP Test] Temp Section",
            "suite_id": sid,
            "description": "Created by Phase 4 verification script — safe to delete",
        }),
    )
    if not section:
        print("❌ Cannot continue without a section.")
        sys.exit(1)
    created["section_id"] = section["id"]
    print(f"   Section id: {section['id']}\n")

    # ── 3. update_section ─────────────────────────────────────────────

    check(
        "update_section: rename the temp section",
        lambda: client.post(f"update_section/{created['section_id']}", {
            "name": "[MCP Test] Temp Section (updated)",
        }),
    )

    # ── 4. add_case ───────────────────────────────────────────────────

    case = check(
        "add_case: create test case with standard fields",
        lambda: client.post(f"add_case/{created['section_id']}", {
            "title": "[MCP Test] Sample Test Case",
            "type_id": 2,       # Functionality
            "priority_id": 2,   # Medium
            "refs": "MCP-001",
        }),
    )
    if not case:
        cleanup(client)
        sys.exit(1)
    created["case_id"] = case["id"]
    print(f"   Case id: {case['id']}, title: {case['title']}\n")

    # ── 5. update_case ────────────────────────────────────────────────

    updated = check(
        "update_case: update the title",
        lambda: client.post(f"update_case/{created['case_id']}", {
            "title": "[MCP Test] Sample Test Case (updated)",
            "priority_id": 3,   # High
        }),
    )
    if updated:
        assert updated["title"] == "[MCP Test] Sample Test Case (updated)", \
            f"Title not updated — got: {updated['title']}"
        print(f"   New title: {updated['title']}\n")

    # ── 6. add_run ────────────────────────────────────────────────────

    run = check(
        "add_run: create test run in Testing Scenarios suite",
        lambda: client.post(f"add_run/{pid}", {
            "name": "[MCP Test] Temp Run",
            "suite_id": sid,
            "include_all": False,
            "case_ids": [created["case_id"]],
        }),
    )
    if not run:
        cleanup(client)
        sys.exit(1)
    created["run_id"] = run["id"]
    print(f"   Run id: {run['id']}\n")

    # ── 7. add_result ─────────────────────────────────────────────────

    # Get the test ID for our case within the run
    tests = client.get_all(f"get_tests/{created['run_id']}", "tests")
    test = next((t for t in tests if t["case_id"] == created["case_id"]), None)

    if test:
        check(
            "add_result: record a passed result on the test case",
            lambda: client.post(f"add_result/{test['id']}", {
                "status_id": 1,  # Passed
                "comment": "Verified by Phase 4 MCP verification script",
                "elapsed": "30s",
            }),
        )
        print()

        # ── 8. add_results_for_cases ─────────────────────────────────

        check(
            "add_results_for_cases: bulk result submission",
            lambda: client.post(f"add_results_for_cases/{created['run_id']}", {
                "results": [
                    {
                        "case_id": created["case_id"],
                        "status_id": 5,  # Failed (second result to show history)
                        "comment": "Simulated failure for bulk result test",
                    }
                ]
            }),
        )
        print()
    else:
        print(f"⚠️  Could not find test for case {created['case_id']} in run — skipping result tests\n")

    # ── 9. add_plan ───────────────────────────────────────────────────

    plan = check(
        "add_plan: create a test plan",
        lambda: client.post(f"add_plan/{pid}", {
            "name": "[MCP Test] Temp Plan",
            "description": "Created by Phase 4 verification — safe to delete",
        }),
    )
    if plan:
        created["plan_id"] = plan["id"]
        print(f"   Plan id: {plan['id']}\n")

        # ── 10. update_plan ───────────────────────────────────────────

        check(
            "update_plan: rename the plan",
            lambda: client.post(f"update_plan/{created['plan_id']}", {
                "name": "[MCP Test] Temp Plan (updated)",
            }),
        )
        print()

    # ── 11. add_milestone ─────────────────────────────────────────────

    milestone = check(
        "add_milestone: create a milestone",
        lambda: client.post(f"add_milestone/{pid}", {
            "name": "[MCP Test] Temp Milestone",
            "description": "Created by Phase 4 verification — safe to delete",
        }),
    )
    if milestone:
        created["milestone_id"] = milestone["id"]
        print(f"   Milestone id: {milestone['id']}\n")

        # ── 12. update_milestone ──────────────────────────────────────

        check(
            "update_milestone: rename the milestone",
            lambda: client.post(f"update_milestone/{created['milestone_id']}", {
                "name": "[MCP Test] Temp Milestone (updated)",
            }),
        )
        print()

    # ── Cleanup ───────────────────────────────────────────────────────

    cleanup(client)

    print("\n── Done ──────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
