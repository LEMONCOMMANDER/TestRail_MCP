"""
Phase 6 verification script — workflow and metrics tools.

Tests:
  1. Offline unit tests for stats helpers (_run_stats, _aggregate_stats)
  2. Name/ID resolver error paths (no network needed for bad-name tests)
  3. Live import_scenarios using project/section names instead of IDs
  4. Live metrics tools (get_project_health, get_coverage_report,
     get_run_summary, get_milestone_progress, get_full_project_report)
  5. Cleanup — all created cases are deleted at the end

The script is self-discovering: it reads whatever projects/suites/sections
exist in your TestRail account and adapts, so it works against the sample
project that TestRail creates on first startup.

Run with:
    uv run python scripts/verify_phase6.py
"""

import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from testrail_mcp.config import Settings
from testrail_mcp.client import TestRailClient
import testrail_mcp.server as _server

PASS = "✅"
FAIL = "❌"
SKIP = "⏭️ "

created_case_ids: list[int] = []
created_run_ids: list[int] = []


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


def skip(label: str, reason: str):
    print(f"{SKIP} {label} — {reason}")


# ── Offline stats helper tests ─────────────────────────────────────────────────

def test_run_stats_offline():
    from testrail_mcp.tools.workflows import _run_stats, _aggregate_stats

    print("Stats helper tests (offline):\n")

    fake_run = {
        "passed_count": 8,
        "failed_count": 2,
        "blocked_count": 1,
        "retest_count": 1,
        "untested_count": 3,
    }

    check(
        "_run_stats: total = sum of all counts",
        lambda: _run_stats(fake_run)["total"] == 15
        or (_ for _ in ()).throw(AssertionError(f"Got {_run_stats(fake_run)['total']}")),
    )
    check(
        "_run_stats: executed = total minus untested",
        lambda: _run_stats(fake_run)["executed"] == 12
        or (_ for _ in ()).throw(AssertionError(f"Got {_run_stats(fake_run)['executed']}")),
    )
    check(
        "_run_stats: pass_rate_pct = passed/executed × 100",
        lambda: _run_stats(fake_run)["pass_rate_pct"] == round(8 / 12 * 100, 1)
        or (_ for _ in ()).throw(AssertionError(f"Got {_run_stats(fake_run)['pass_rate_pct']}")),
    )
    check(
        "_run_stats: execution_rate_pct = executed/total × 100",
        lambda: _run_stats(fake_run)["execution_rate_pct"] == round(12 / 15 * 100, 1)
        or (_ for _ in ()).throw(AssertionError(f"Got {_run_stats(fake_run)['execution_rate_pct']}")),
    )

    # Zero-safe: all untested
    zero_run = {"passed_count": 0, "failed_count": 0, "blocked_count": 0,
                "retest_count": 0, "untested_count": 5}
    check(
        "_run_stats: pass_rate_pct is 0.0 when no tests executed (no division error)",
        lambda: _run_stats(zero_run)["pass_rate_pct"] == 0.0
        or (_ for _ in ()).throw(AssertionError(f"Got {_run_stats(zero_run)['pass_rate_pct']}")),
    )

    # Aggregate
    runs = [fake_run, fake_run]
    agg = _aggregate_stats(runs)
    check(
        "_aggregate_stats: sums counts across two identical runs",
        lambda: agg["passed"] == 16 and agg["total"] == 30
        or (_ for _ in ()).throw(AssertionError(f"passed={agg['passed']} total={agg['total']}")),
    )
    check(
        "_aggregate_stats: pass_rate_pct recomputed from aggregated totals",
        lambda: agg["pass_rate_pct"] == round(16 / 24 * 100, 1)
        or (_ for _ in ()).throw(AssertionError(f"Got {agg['pass_rate_pct']}")),
    )

    print()


# ── Resolver error-path tests (uses mock client — no network) ──────────────────

def test_resolver_errors():
    from testrail_mcp.tools.workflows import (
        _resolve_project, _resolve_suite, _resolve_section,
        _resolve_run, _resolve_milestone,
    )

    print("Resolver error-path tests (offline):\n")

    mock_client = MagicMock()
    mock_client.get_all.return_value = [
        {"id": 1, "name": "Real Project", "suite_mode": 1},
    ]
    mock_client.get_suite_mode.return_value = 1

    check(
        "_resolve_project: bad name raises ValueError listing available projects",
        lambda: _test_bad_project_name(_resolve_project, mock_client),
    )
    check(
        "_resolve_project: numeric ID bypasses name lookup",
        lambda: _test_project_by_id(_resolve_project, mock_client),
    )

    mock_client.get_all.return_value = [
        {"id": 10, "name": "Real Suite"},
    ]
    check(
        "_resolve_suite: bad suite name raises ValueError",
        lambda: _test_bad_suite_name(_resolve_suite, mock_client),
    )
    check(
        "_resolve_suite: None suite on single-suite project returns (None, None)",
        lambda: _resolve_suite(mock_client, 1, None) == (None, None)
        or (_ for _ in ()).throw(AssertionError("Expected (None, None)")),
    )

    mock_client.get_all.return_value = [
        {"id": 20, "name": "Login Tests"},
    ]
    check(
        "_resolve_section: bad section name raises ValueError listing available",
        lambda: _test_bad_section_name(_resolve_section, mock_client),
    )

    mock_client.get_all.return_value = [
        {"id": 5, "name": "Sprint 1"},
        {"id": 6, "name": "Sprint 1"},  # duplicate name
    ]
    check(
        "_resolve_run: duplicate run names returns most recent (first in list)",
        lambda: _resolve_run(mock_client, 1, "Sprint 1")["id"] == 5
        or (_ for _ in ()).throw(AssertionError("Expected id=5 (most recent)")),
    )

    print()


def _test_bad_project_name(resolver, client):
    try:
        resolver(client, "Ghost Project")
        raise AssertionError("Expected ValueError but call succeeded")
    except ValueError as e:
        msg = str(e)
        assert "Ghost Project" in msg, f"Project name missing from error: {msg}"
        assert "Real Project" in msg, f"Available projects missing from error: {msg}"
    return True


def _test_project_by_id(resolver, client):
    client.get.return_value = {"id": 99, "name": "By ID Project"}
    pid, pname = resolver(client, 99)
    assert pid == 99, f"Expected 99, got {pid}"
    assert pname == "By ID Project", f"Expected 'By ID Project', got {pname}"
    return True


def _test_bad_suite_name(resolver, client):
    try:
        resolver(client, 1, "Ghost Suite")
        raise AssertionError("Expected ValueError but call succeeded")
    except ValueError as e:
        msg = str(e)
        assert "Ghost Suite" in msg, f"Suite name missing from error: {msg}"
        assert "Real Suite" in msg, f"Available suites missing from error: {msg}"
    return True


def _test_bad_section_name(resolver, client):
    try:
        resolver(client, 1, None, "Ghost Section")
        raise AssertionError("Expected ValueError but call succeeded")
    except ValueError as e:
        msg = str(e)
        assert "Ghost Section" in msg, f"Section name missing from error: {msg}"
        assert "Login Tests" in msg, f"Available sections missing from error: {msg}"
    return True


# ── Live tests ─────────────────────────────────────────────────────────────────

def run_live_tests(client: TestRailClient):
    from testrail_mcp.tools.workflows import (
        import_scenarios,
        get_project_health,
        get_coverage_report,
        get_run_summary,
        get_milestone_progress,
        get_full_project_report,
    )

    # ── Discover the first available project ──────────────────────────────────
    print("Discovery:\n")

    projects = client.get_all("get_projects", "projects")
    if not projects:
        print(f"{SKIP} All live tests — no projects found in TestRail account")
        return

    project = projects[0]
    project_id = project["id"]
    project_name = project["name"]
    suite_mode = client.get_suite_mode(project_id)

    print(f"   Project: '{project_name}' (id={project_id}, suite_mode={suite_mode})\n")

    # Resolve suite
    suites = client.get_all(f"get_suites/{project_id}", "suites")
    suite = suites[0] if suites else None
    suite_id = suite["id"] if suite else None
    suite_name = suite["name"] if suite else None

    # Resolve first available section
    section_params = {"suite_id": suite_id} if suite_id and suite_mode == 3 else {}
    sections = client.get_all(f"get_sections/{project_id}", "sections", params=section_params)

    if not sections:
        print(f"{SKIP} All import tests — no sections found. Create a section in TestRail first.")
        target_section = None
    else:
        target_section = sections[0]
        print(f"   Suite  : '{suite_name}' (id={suite_id})")
        print(f"   Section: '{target_section['name']}' (id={target_section['id']})\n")

    # ── import_scenarios by name ───────────────────────────────────────────────
    print("import_scenarios tests:\n")

    GHERKIN = """\
Feature: Phase 6 Verification

  Scenario: [MCP-P6] Verify import by name works
    Given the import_scenarios tool is called with project/section names
    When the names are resolved to valid IDs
    Then the test cases should be created in TestRail

  Scenario: [MCP-P6] Verify import handles second scenario
    Given a second scenario exists in the file
    When the parser processes the content
    Then both cases should appear in the target section
"""

    if target_section:
        suite_arg = suite_name if suite_mode == 3 else None

        result = check(
            "import_scenarios: import 2 Gherkin scenarios by project/section name",
            lambda: import_scenarios(
                content=GHERKIN,
                project=project_name,
                section=target_section["name"],
                suite=suite_arg,
                fmt="gherkin",
                priority_id=2,
            ),
        )

        if result:
            check(
                "import_scenarios: total_created == 2",
                lambda: result["total_created"] == 2
                or (_ for _ in ()).throw(AssertionError(
                    f"Expected 2, got {result['total_created']}. Failures: {result['failed']}"
                )),
            )
            check(
                "import_scenarios: resolved dict contains project_name and section_id",
                lambda: result["resolved"]["project"] == project_name
                and result["resolved"]["section_id"] == target_section["id"]
                or (_ for _ in ()).throw(AssertionError(f"resolved: {result['resolved']}")),
            )
            check(
                "import_scenarios: no failures",
                lambda: len(result["failed"]) == 0
                or (_ for _ in ()).throw(AssertionError(f"Failures: {result['failed']}")),
            )
            for c in result.get("created", []):
                created_case_ids.append(c["id"])
            print(f"\n   Created cases: {[c['title'] for c in result.get('created', [])]}\n")

        # import_scenarios: also test by numeric ID
        result_by_id = check(
            "import_scenarios: import using numeric project_id and section_id",
            lambda: import_scenarios(
                content=GHERKIN,
                project=project_id,
                section=target_section["id"],
                suite=suite_id,
                fmt="gherkin",
                priority_id=1,
            ),
        )
        if result_by_id:
            for c in result_by_id.get("created", []):
                created_case_ids.append(c["id"])

        # import_scenarios: bad project name gives clear error
        check(
            "import_scenarios: bad project name raises ValueError with available list",
            lambda: _test_import_bad_project(import_scenarios, target_section),
        )

        # import_scenarios: bad section name gives clear error
        check(
            "import_scenarios: bad section name raises ValueError with available list",
            lambda: _test_import_bad_section(import_scenarios, project_name, suite_arg),
        )

    else:
        skip("import_scenarios tests", "no section available")

    print()

    # ── Metrics tools ──────────────────────────────────────────────────────────
    print("Metrics tools:\n")

    # get_coverage_report — should work even with no runs
    cov = check(
        "get_coverage_report: returns coverage structure for project",
        lambda: get_coverage_report(project=project_id),
    )
    if cov:
        check(
            "get_coverage_report: total_cases is a non-negative integer",
            lambda: isinstance(cov["total_cases"], int) and cov["total_cases"] >= 0
            or (_ for _ in ()).throw(AssertionError(f"total_cases={cov['total_cases']}")),
        )
        check(
            "get_coverage_report: project_name matches",
            lambda: cov["project_name"] == project_name
            or (_ for _ in ()).throw(AssertionError(f"Got '{cov['project_name']}'")),
        )

    # get_project_health — may have no runs; should not crash
    health = check(
        "get_project_health: returns health structure (handles zero runs gracefully)",
        lambda: get_project_health(project=project_name),
    )
    if health:
        check(
            "get_project_health: project_id and project_name present",
            lambda: health["project_id"] == project_id and health["project_name"] == project_name
            or (_ for _ in ()).throw(AssertionError(f"Got {health}")),
        )
        check(
            "get_project_health: per_run is a list",
            lambda: isinstance(health["per_run"], list)
            or (_ for _ in ()).throw(AssertionError("per_run is not a list")),
        )

    # get_full_project_report — the comprehensive report
    report = check(
        "get_full_project_report: returns health + coverage + milestones sections",
        lambda: get_full_project_report(project=project_id),
    )
    if report:
        check(
            "get_full_project_report: 'health' section present with runs_analyzed key",
            lambda: "health" in report and "runs_analyzed" in report["health"]
            or (_ for _ in ()).throw(AssertionError(f"Keys: {list(report.keys())}")),
        )
        check(
            "get_full_project_report: 'coverage' section is a list",
            lambda: isinstance(report["coverage"], list)
            or (_ for _ in ()).throw(AssertionError("coverage is not a list")),
        )
        check(
            "get_full_project_report: 'milestones' section has active_count",
            lambda: "milestones" in report and "active_count" in report["milestones"]
            or (_ for _ in ()).throw(AssertionError(f"Keys: {list(report.keys())}")),
        )

    # Runs-dependent tests — only run if at least one run exists
    runs = client.get_all(f"get_runs/{project_id}", "runs")
    if runs:
        run = runs[0]
        run_summary = check(
            "get_run_summary: returns stats for most recent run by ID",
            lambda: get_run_summary(run=run["id"]),
        )
        if run_summary:
            check(
                "get_run_summary: pass_rate_pct and execution_rate_pct are floats",
                lambda: isinstance(run_summary["pass_rate_pct"], float)
                and isinstance(run_summary["execution_rate_pct"], float)
                or (_ for _ in ()).throw(AssertionError(f"Got {run_summary}")),
            )
            check(
                "get_run_summary: run_name lookup by name matches by-ID result",
                lambda: get_run_summary(
                    run=run["name"], project_id=project_id
                )["run_id"] == run["id"]
                or (_ for _ in ()).throw(AssertionError("Name lookup returned different run")),
            )
    else:
        skip("get_run_summary", "no runs in project — create a test run to exercise this tool")

    # Milestone tests — only run if milestones exist
    milestones = client.get_all(f"get_milestones/{project_id}", "milestones")
    if milestones:
        ms = milestones[0]
        ms_result = check(
            "get_milestone_progress: returns progress for first milestone by ID",
            lambda: get_milestone_progress(milestone=ms["id"]),
        )
        if ms_result:
            check(
                "get_milestone_progress: milestone_name matches",
                lambda: ms_result["milestone_name"] == ms["name"]
                or (_ for _ in ()).throw(AssertionError(f"Got '{ms_result['milestone_name']}'")),
            )
    else:
        skip("get_milestone_progress", "no milestones in project — add a milestone to exercise this tool")

    print()


def _test_import_bad_project(import_fn, section):
    try:
        import_fn(
            content="Scenario: test\n  Given something",
            project="__nonexistent_project_xyz__",
            section=section["name"],
            fmt="gherkin",
        )
        raise AssertionError("Expected ValueError but call succeeded")
    except ValueError as e:
        assert "__nonexistent_project_xyz__" in str(e), f"Project name missing: {e}"
    return True


def _test_import_bad_section(import_fn, project_name, suite_name):
    try:
        import_fn(
            content="Scenario: test\n  Given something",
            project=project_name,
            section="__nonexistent_section_xyz__",
            suite=suite_name,
            fmt="gherkin",
        )
        raise AssertionError("Expected ValueError but call succeeded")
    except ValueError as e:
        assert "__nonexistent_section_xyz__" in str(e), f"Section name missing: {e}"
    return True


# ── Cleanup ────────────────────────────────────────────────────────────────────

def cleanup(client: TestRailClient):
    if not created_case_ids and not created_run_ids:
        return

    print("── Cleanup ───────────────────────────────────────────────────\n")

    for case_id in created_case_ids:
        try:
            client.post(f"delete_case/{case_id}")
            print(f"{PASS} Deleted case {case_id}")
        except Exception as e:
            print(f"{FAIL} Could not delete case {case_id}: {e}")

    for run_id in created_run_ids:
        try:
            client.post(f"delete_run/{run_id}")
            print(f"{PASS} Deleted run {run_id}")
        except Exception as e:
            print(f"{FAIL} Could not delete run {run_id}: {e}")

    print()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    print("\n── Phase 6 Verification ──────────────────────────────────────\n")

    # Offline tests — no credentials needed
    test_run_stats_offline()
    test_resolver_errors()

    # Live tests
    print("Live tests:\n")
    settings = Settings()
    client = TestRailClient(
        url=settings.testrail_url,
        email=settings.testrail_email,
        api_key=settings.testrail_api_key,
    )
    _server.client = client

    try:
        run_live_tests(client)
    finally:
        cleanup(client)

    print("── Done ──────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
