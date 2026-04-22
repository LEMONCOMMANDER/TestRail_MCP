"""
Workflow and metrics tools for TestRail.

Phase 6: Higher-level orchestration tools that chain atomic tools for
known workflows, plus metrics/reporting tools.

Tools:
  import_scenarios         — name/ID-based flat import into a single section
  import_from_hierarchy    — structured markdown import with auto section creation
  get_run_summary          — pass/fail/coverage stats for a run
  get_milestone_progress   — completion metrics for a milestone
  get_project_health       — aggregate health across recent runs
  get_coverage_report      — case coverage across recent runs
  get_full_project_report  — comprehensive report combining all metrics
"""

from __future__ import annotations

from testrail_mcp.server import mcp, get_client
from testrail_mcp.client import TestRailClient
from testrail_mcp.parsers import parse, parse_hierarchy

_BATCH_SIZE = 25
_BDD_TEMPLATE_ID = 4
_BDD_FIELD_KEY = "custom_testrail_bdd_scenario"
_MAX_CONTENT_BYTES = 500 * 1024


# ── Name/ID resolvers ──────────────────────────────────────────────────────────

def _resolve_project(client: TestRailClient, project: int | str) -> tuple[int, str]:
    """Return (project_id, project_name). Accepts int ID or string name."""
    if isinstance(project, int):
        p = client.get(f"get_project/{project}")
        return p["id"], p["name"]

    projects = client.get_all("get_projects", "projects")
    matches = [p for p in projects if p["name"].lower() == str(project).lower()]
    if not matches:
        available = ", ".join(p["name"] for p in projects)
        raise ValueError(
            f"No project found with name '{project}'. "
            f"Available projects: {available}"
        )
    if len(matches) > 1:
        raise ValueError(
            f"Multiple projects match the name '{project}'. "
            "Use a project ID to avoid ambiguity."
        )
    return matches[0]["id"], matches[0]["name"]


def _resolve_suite(
    client: TestRailClient, project_id: int, suite: int | str | None
) -> tuple[int | None, str | None]:
    """
    Return (suite_id, suite_name). Accepts int ID or string name.
    Returns (None, None) for single-suite projects when suite is not provided.
    """
    suite_mode = client.get_suite_mode(project_id)

    if suite is None:
        if suite_mode == 3:
            raise ValueError(
                f"Project {project_id} uses multiple suites (suite_mode=3). "
                "Provide a suite name or ID — use list_suites to see available suites."
            )
        return None, None

    if isinstance(suite, int):
        s = client.get(f"get_suite/{suite}")
        return s["id"], s["name"]

    suites = client.get_all(f"get_suites/{project_id}", "suites")
    matches = [s for s in suites if s["name"].lower() == str(suite).lower()]
    if not matches:
        available = ", ".join(s["name"] for s in suites)
        raise ValueError(
            f"No suite found with name '{suite}' in project {project_id}. "
            f"Available suites: {available}"
        )
    if len(matches) > 1:
        raise ValueError(
            f"Multiple suites match the name '{suite}'. "
            "Use a suite ID instead."
        )
    return matches[0]["id"], matches[0]["name"]


def _resolve_section(
    client: TestRailClient,
    project_id: int,
    suite_id: int | None,
    section: int | str,
) -> tuple[int, str]:
    """Return (section_id, section_name). Accepts int ID or string name."""
    if isinstance(section, int):
        s = client.get(f"get_section/{section}")
        return s["id"], s["name"]

    params: dict = {}
    if suite_id is not None:
        params["suite_id"] = suite_id
    sections = client.get_all(f"get_sections/{project_id}", "sections", params=params)

    matches = [s for s in sections if s["name"].lower() == str(section).lower()]
    if not matches:
        available = ", ".join(s["name"] for s in sections)
        raise ValueError(
            f"No section found with name '{section}'. "
            f"Available sections: {available}"
        )
    if len(matches) > 1:
        ids = ", ".join(f"'{s['name']}' (id={s['id']})" for s in matches)
        raise ValueError(
            f"Multiple sections match the name '{section}': {ids}. "
            "Use a section ID instead."
        )
    return matches[0]["id"], matches[0]["name"]


def _resolve_run(
    client: TestRailClient, project_id: int, run: int | str
) -> dict:
    """Return the run dict. Accepts int ID or string name."""
    if isinstance(run, int):
        return client.get(f"get_run/{run}")

    runs = client.get_all(f"get_runs/{project_id}", "runs")
    matches = [r for r in runs if r["name"].lower() == str(run).lower()]
    if not matches:
        available = ", ".join(r["name"] for r in runs[:10])
        raise ValueError(
            f"No run found with name '{run}' in project {project_id}. "
            f"Recent runs: {available}"
        )
    # When multiple runs share a name, return the most recent (first in list).
    return matches[0]


def _resolve_milestone(
    client: TestRailClient, project_id: int, milestone: int | str
) -> dict:
    """Return the milestone dict. Accepts int ID or string name."""
    if isinstance(milestone, int):
        return client.get(f"get_milestone/{milestone}")

    milestones = client.get_all(f"get_milestones/{project_id}", "milestones")
    matches = [m for m in milestones if m["name"].lower() == str(milestone).lower()]
    if not matches:
        available = ", ".join(m["name"] for m in milestones)
        raise ValueError(
            f"No milestone found with name '{milestone}' in project {project_id}. "
            f"Available milestones: {available}"
        )
    return matches[0]


# ── Stats helpers ──────────────────────────────────────────────────────────────

def _run_stats(run: dict) -> dict:
    """
    Compute pass/fail/coverage stats from a TestRail run object.

    TestRail run objects include passed_count, failed_count, blocked_count,
    untested_count, and retest_count directly on the run.
    """
    passed = run.get("passed_count") or 0
    failed = run.get("failed_count") or 0
    blocked = run.get("blocked_count") or 0
    untested = run.get("untested_count") or 0
    retest = run.get("retest_count") or 0

    total = passed + failed + blocked + untested + retest
    executed = passed + failed + blocked + retest  # everything except untested

    pass_rate = round(passed / executed * 100, 1) if executed > 0 else 0.0
    execution_rate = round(executed / total * 100, 1) if total > 0 else 0.0

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "retest": retest,
        "untested": untested,
        "executed": executed,
        "pass_rate_pct": pass_rate,
        "execution_rate_pct": execution_rate,
    }


def _aggregate_stats(runs: list[dict]) -> dict:
    """Sum _run_stats across a list of runs and recompute aggregate rates."""
    totals: dict[str, int] = {
        "total": 0, "passed": 0, "failed": 0,
        "blocked": 0, "retest": 0, "untested": 0, "executed": 0,
    }
    for run in runs:
        stats = _run_stats(run)
        for k in totals:
            totals[k] += stats[k]

    executed = totals["executed"]
    total = totals["total"]
    pass_rate = round(totals["passed"] / executed * 100, 1) if executed > 0 else 0.0
    exec_rate = round(executed / total * 100, 1) if total > 0 else 0.0

    return {**totals, "pass_rate_pct": pass_rate, "execution_rate_pct": exec_rate}


# ── Workflow tools ─────────────────────────────────────────────────────────────

@mcp.tool
def import_scenarios(
    content: str,
    project: int | str,
    section: int | str,
    suite: int | str | None = None,
    fmt: str = "gherkin",
    type_id: int | None = None,
    priority_id: int | None = None,
) -> dict:
    """
    Parse text content and create TestRail test cases — accepts names or IDs.

    This is the high-level import workflow. It resolves project, suite, and
    section by name so you don't need to look up IDs manually first. Pass
    either a numeric ID or an exact name string for each container.

    content: the full text of the file (plain text only, max 500KB).

    project: project ID (int) or exact project name (str).
      Example: 3  or  "My Web App"

    section: section ID (int) or exact section name (str).
      Example: 45  or  "Login Tests"

    suite: suite ID (int) or exact suite name (str).
      Required for multi-suite projects (suite_mode=3). Omit for single-suite.
      Example: 12  or  "Regression Suite"

    fmt: content format — "gherkin" (default), "markdown", or "numbered".

    type_id: optional case type for all created cases.
      1=Automated, 2=Functionality, 4=Regression, 5=Smoke & Sanity

    priority_id: optional priority for all created cases.
      1=Low, 2=Medium, 3=High, 4=Critical

    Returns a summary including which names were resolved, total_parsed,
    total_created, a list of created cases, and any failures with details.
    """
    content_bytes = len(content.encode("utf-8"))
    if content_bytes > _MAX_CONTENT_BYTES:
        raise ValueError(
            f"Content too large ({content_bytes // 1024}KB). "
            f"Maximum is {_MAX_CONTENT_BYTES // 1024}KB. "
            "Split the file into smaller sections and import each separately."
        )

    if "\x00" in content:
        raise ValueError(
            "Content appears to be binary. Only plain text files are supported."
        )

    client = get_client()

    project_id, project_name = _resolve_project(client, project)
    suite_id, suite_name = _resolve_suite(client, project_id, suite)
    section_id, section_name = _resolve_section(client, project_id, suite_id, section)

    scenarios = parse(content, fmt)
    if not scenarios:
        return {
            "resolved": {
                "project": project_name,
                "project_id": project_id,
                "suite": suite_name,
                "suite_id": suite_id,
                "section": section_name,
                "section_id": section_id,
            },
            "total_parsed": 0,
            "total_created": 0,
            "created": [],
            "failed": [],
            "message": (
                f"No scenarios found using format '{fmt}'. "
                "Check that the fmt parameter matches the file structure."
            ),
        }

    created = []
    failed = []

    for i in range(0, len(scenarios), _BATCH_SIZE):
        batch = scenarios[i : i + _BATCH_SIZE]
        for scenario in batch:
            try:
                body: dict = {"title": scenario.title, "template_id": _BDD_TEMPLATE_ID}
                if scenario.bdd_content:
                    body[_BDD_FIELD_KEY] = [{"content": scenario.bdd_content}]
                elif scenario.description:
                    body["custom_preconds"] = scenario.description
                if type_id is not None:
                    body["type_id"] = type_id
                if priority_id is not None:
                    body["priority_id"] = priority_id

                case = client.post(f"add_case/{section_id}", body)
                created.append({"id": case["id"], "title": case["title"]})
            except Exception as e:
                failed.append({"title": scenario.title, "error": str(e)})

    return {
        "resolved": {
            "project": project_name,
            "project_id": project_id,
            "suite": suite_name,
            "suite_id": suite_id,
            "section": section_name,
            "section_id": section_id,
        },
        "total_parsed": len(scenarios),
        "total_created": len(created),
        "created": created,
        "failed": failed,
        "message": (
            f"Created {len(created)} of {len(scenarios)} cases in "
            f"'{section_name}' → '{project_name}'."
            + (f" {len(failed)} failed — see 'failed' for details." if failed else "")
        ),
    }


@mcp.tool
def import_from_hierarchy(
    content: str,
    project: int | str,
    suite: int | str | None = None,
    parent_section: int | str | None = None,
    type_id: int | None = None,
    priority_id: int | None = None,
) -> dict:
    """
    Import a structured markdown document into TestRail, auto-creating sections.

    Reads the heading hierarchy from the document and creates matching sections
    in TestRail before importing the test cases beneath each heading. This is
    the preferred tool when your markdown file has organised sections — it
    eliminates the need to manually create sections and call import_scenarios
    per section.

    Heading mapping:
      ## heading  → creates a top-level TestRail section
      ### heading → creates a child section nested under the nearest ##

    Case titles are detected from:
      #### headings       — explicit case title marker
      **bold-only lines** — common in exported or hand-written docs

    BDD steps (Given/When/Then/And/But) under a case title are captured as
    the BDD scenario content.

    content: the full markdown text (plain text only, max 500KB).

    project: project ID (int) or exact project name (str).
      Example: 3  or  "My Web App"

    suite: suite ID (int) or exact suite name (str).
      Required for multi-suite projects (suite_mode=3). Omit for single-suite.
      Example: 12  or  "Regression Suite"

    parent_section: optional section ID (int) or name (str) to nest all
      created sections under. Omit to create at the root of the suite.

    type_id: optional case type for all created cases.
      1=Automated, 2=Functionality, 4=Regression, 5=Smoke & Sanity

    priority_id: optional priority for all created cases.
      1=Low, 2=Medium, 3=High, 4=Critical

    Returns a summary with:
      - resolved: project/suite names and IDs that were found
      - sections_created: list of {name, id, parent_id} for each section created
      - total_parsed: total number of cases found across all sections
      - total_created: total number of cases successfully created
      - by_section: per-section breakdown with case list
      - failed: list of {title, section, error} for any failures
    """
    content_bytes = len(content.encode("utf-8"))
    if content_bytes > _MAX_CONTENT_BYTES:
        raise ValueError(
            f"Content too large ({content_bytes // 1024}KB). "
            f"Maximum is {_MAX_CONTENT_BYTES // 1024}KB. "
            "Split the file into smaller sections and import each separately."
        )
    if "\x00" in content:
        raise ValueError(
            "Content appears to be binary. Only plain text files are supported."
        )

    hierarchy = parse_hierarchy(content)
    if not hierarchy:
        return {
            "sections_created": [],
            "total_parsed": 0,
            "total_created": 0,
            "by_section": [],
            "failed": [],
            "message": (
                "No sections or cases found. "
                "Ensure the document uses ## / ### headings for sections and "
                "#### headings or **bold lines** for case titles."
            ),
        }

    client = get_client()
    project_id, project_name = _resolve_project(client, project)
    suite_id, suite_name = _resolve_suite(client, project_id, suite)

    # Resolve optional parent section
    parent_section_id: int | None = None
    if parent_section is not None:
        parent_section_id, _ = _resolve_section(client, project_id, suite_id, parent_section)

    # Create sections in document order, tracking name → id for parent linking
    section_id_map: dict[str, int | None] = {}
    sections_created = []

    for node in hierarchy:
        pid = (
            parent_section_id
            if node.level == 2
            else section_id_map.get(node.parent_name or "")
        )

        body: dict = {"name": node.name}
        if suite_id is not None:
            body["suite_id"] = suite_id
        if pid is not None:
            body["parent_id"] = pid

        try:
            new_section = client.post(f"add_section/{project_id}", body)
            section_id_map[node.name] = new_section["id"]
            sections_created.append({
                "name": new_section["name"],
                "id": new_section["id"],
                "parent_id": pid,
            })
        except Exception as e:
            section_id_map[node.name] = None
            sections_created.append({
                "name": node.name,
                "id": None,
                "error": str(e),
            })

    # Import cases into each section
    total_parsed = sum(len(n.cases) for n in hierarchy)
    total_created = 0
    failed: list[dict] = []
    by_section: list[dict] = []

    for node in hierarchy:
        sid = section_id_map.get(node.name)
        if sid is None:
            for case in node.cases:
                failed.append({
                    "title": case.title,
                    "section": node.name,
                    "error": "Section creation failed — cannot import cases",
                })
            continue

        section_cases: list[dict] = []
        for i in range(0, len(node.cases), _BATCH_SIZE):
            for scenario in node.cases[i : i + _BATCH_SIZE]:
                try:
                    case_body: dict = {
                        "title": scenario.title,
                        "template_id": _BDD_TEMPLATE_ID,
                    }
                    if scenario.bdd_content:
                        case_body[_BDD_FIELD_KEY] = [{"content": scenario.bdd_content}]
                    elif scenario.description:
                        case_body["custom_preconds"] = scenario.description
                    if type_id is not None:
                        case_body["type_id"] = type_id
                    if priority_id is not None:
                        case_body["priority_id"] = priority_id

                    result = client.post(f"add_case/{sid}", case_body)
                    section_cases.append({"id": result["id"], "title": result["title"]})
                    total_created += 1
                except Exception as e:
                    failed.append({
                        "title": scenario.title,
                        "section": node.name,
                        "error": str(e),
                    })

        by_section.append({
            "section_name": node.name,
            "section_id": sid,
            "cases_parsed": len(node.cases),
            "cases_created": len(section_cases),
            "cases": section_cases,
        })

    return {
        "resolved": {
            "project": project_name,
            "project_id": project_id,
            "suite": suite_name,
            "suite_id": suite_id,
        },
        "sections_created": sections_created,
        "total_parsed": total_parsed,
        "total_created": total_created,
        "by_section": by_section,
        "failed": failed,
        "message": (
            f"Created {len(sections_created)} sections and {total_created} of "
            f"{total_parsed} cases in '{project_name}'."
            + (f" {len(failed)} cases failed — see 'failed' for details." if failed else "")
        ),
    }

@mcp.tool
def get_run_summary(
    run: int | str,
    project_id: int | None = None,
) -> dict:
    """
    Get pass/fail/coverage statistics for a test run.

    run: the run ID (int) or run name (str).
      When using a name, project_id is required.
      Example: 88  or  "Sprint 12 Regression"

    project_id: required when run is a name; ignored when run is a numeric ID.

    Returns:
      - run_id, run_name, is_completed, milestone_id
      - total, passed, failed, blocked, retest, untested counts
      - executed: total minus untested
      - pass_rate_pct: passed / executed × 100 (excludes untested from denominator)
      - execution_rate_pct: executed / total × 100 (how much of the run is done)
    """
    client = get_client()

    if isinstance(run, str) and project_id is None:
        raise ValueError(
            "project_id is required when looking up a run by name. "
            "Provide project_id, or use the numeric run ID instead."
        )

    run_obj = _resolve_run(client, project_id, run) if isinstance(run, str) else client.get(f"get_run/{run}")

    return {
        "run_id": run_obj["id"],
        "run_name": run_obj.get("name"),
        "is_completed": run_obj.get("is_completed", False),
        "milestone_id": run_obj.get("milestone_id"),
        **_run_stats(run_obj),
    }


@mcp.tool
def get_milestone_progress(
    milestone: int | str,
    project_id: int | None = None,
) -> dict:
    """
    Get completion and pass/fail metrics for a milestone.

    Aggregates all test runs linked to the milestone so you can see the
    overall state of a release or sprint in one call.

    milestone: the milestone ID (int) or exact name (str).
      When using a name, project_id is required.
      Example: 5  or  "v2.4 Release"

    project_id: required when milestone is a name.

    Returns:
      - milestone_id, milestone_name, due_on, is_completed
      - total_runs: how many runs are tied to this milestone
      - aggregate counts: passed, failed, blocked, retest, untested, executed
      - pass_rate_pct: passed / executed across all runs in the milestone
      - execution_rate_pct: executed / total across all runs
      - per_run: per-run breakdown with individual stats
    """
    client = get_client()

    if isinstance(milestone, str) and project_id is None:
        raise ValueError(
            "project_id is required when looking up a milestone by name."
        )

    ms = _resolve_milestone(client, project_id, milestone) if isinstance(milestone, str) else client.get(f"get_milestone/{milestone}")

    proj_id = ms.get("project_id") or project_id
    all_runs = client.get_all(f"get_runs/{proj_id}", "runs")
    ms_runs = [r for r in all_runs if r.get("milestone_id") == ms["id"]]

    agg = _aggregate_stats(ms_runs)

    per_run = [
        {
            "run_id": r["id"],
            "run_name": r.get("name"),
            "is_completed": r.get("is_completed", False),
            **_run_stats(r),
        }
        for r in ms_runs
    ]

    return {
        "milestone_id": ms["id"],
        "milestone_name": ms.get("name"),
        "due_on": ms.get("due_on"),
        "is_completed": ms.get("is_completed", False),
        "total_runs": len(ms_runs),
        **agg,
        "per_run": per_run,
    }


# ── Metrics tools ──────────────────────────────────────────────────────────────

@mcp.tool
def get_project_health(
    project: int | str,
    run_limit: int = 10,
) -> dict:
    """
    Get aggregate health metrics across the most recent runs in a project.

    Provides a quick "how is this project doing?" answer — overall pass rate,
    execution rate, and a per-run breakdown to spot trends over time.

    project: the project ID (int) or exact project name (str).
    run_limit: how many recent runs to include (default 10, max 50).

    Returns:
      - project_id, project_name
      - runs_analyzed: number of runs included
      - aggregate counts: passed, failed, blocked, retest, untested, executed
      - pass_rate_pct: passed / executed across all analyzed runs
      - execution_rate_pct: how much of the total test volume has been run
      - per_run: list of runs newest-first with individual stats and milestone_id
    """
    client = get_client()
    run_limit = min(max(1, run_limit), 50)

    project_id, project_name = _resolve_project(client, project)
    all_runs = client.get_all(f"get_runs/{project_id}", "runs")
    recent = all_runs[:run_limit]

    agg = _aggregate_stats(recent)

    per_run = [
        {
            "run_id": r["id"],
            "run_name": r.get("name"),
            "is_completed": r.get("is_completed", False),
            "milestone_id": r.get("milestone_id"),
            **_run_stats(r),
        }
        for r in recent
    ]

    return {
        "project_id": project_id,
        "project_name": project_name,
        "runs_analyzed": len(recent),
        **agg,
        "per_run": per_run,
    }


@mcp.tool
def get_coverage_report(
    project: int | str,
    suite: int | str | None = None,
) -> dict:
    """
    Get test case coverage for a project or suite.

    Coverage measures what fraction of the total cases defined in TestRail
    have been executed (received a non-Untested result) in test runs.
    This tells you how much of your test library is actively being exercised.

    project: the project ID (int) or exact project name (str).
    suite: optional suite ID (int) or name (str). Required for multi-suite projects.

    Returns:
      - total_cases: cases defined in TestRail for this project/suite
      - total_runs: number of runs found
      - most_recent_run: coverage detail for the latest run
          run_name, total_tests_in_run, executed, untested
          execution_rate_pct: how much of this run has been done
          run_scope_pct: what fraction of total cases this run covers
      - all_runs_aggregate: execution rate summed across all runs
        (a case executed in multiple runs is counted multiple times — this
        reflects testing thoroughness, not unique case coverage)
    """
    client = get_client()

    project_id, project_name = _resolve_project(client, project)
    suite_id, suite_name = _resolve_suite(client, project_id, suite)

    params: dict = {}
    if suite_id is not None:
        params["suite_id"] = suite_id
    all_cases = client.get_all(f"get_cases/{project_id}", "cases", params=params)
    total_cases = len(all_cases)

    all_runs = client.get_all(f"get_runs/{project_id}", "runs")
    if suite_id is not None:
        all_runs = [r for r in all_runs if r.get("suite_id") == suite_id]

    if not all_runs:
        return {
            "project_id": project_id,
            "project_name": project_name,
            "suite_id": suite_id,
            "suite_name": suite_name,
            "total_cases": total_cases,
            "total_runs": 0,
            "most_recent_run": None,
            "all_runs_aggregate": None,
            "message": "No runs found for this project/suite.",
        }

    recent = all_runs[0]
    recent_stats = _run_stats(recent)
    run_scope_pct = (
        round(recent_stats["total"] / total_cases * 100, 1)
        if total_cases > 0
        else 0.0
    )

    agg_exec = sum(_run_stats(r)["executed"] for r in all_runs)
    agg_total = sum(_run_stats(r)["total"] for r in all_runs)
    agg_rate = round(agg_exec / agg_total * 100, 1) if agg_total > 0 else 0.0

    return {
        "project_id": project_id,
        "project_name": project_name,
        "suite_id": suite_id,
        "suite_name": suite_name,
        "total_cases": total_cases,
        "total_runs": len(all_runs),
        "most_recent_run": {
            "run_id": recent["id"],
            "run_name": recent.get("name"),
            "total_tests_in_run": recent_stats["total"],
            "executed": recent_stats["executed"],
            "untested": recent_stats["untested"],
            "execution_rate_pct": recent_stats["execution_rate_pct"],
            "run_scope_pct": run_scope_pct,
        },
        "all_runs_aggregate": {
            "total_test_instances": agg_total,
            "executed_instances": agg_exec,
            "execution_rate_pct": agg_rate,
        },
    }


@mcp.tool
def get_full_project_report(
    project: int | str,
    run_limit: int = 10,
) -> dict:
    """
    Generate a comprehensive metrics report for a project in a single call.

    Combines project health, coverage, and milestone progress into one response.
    Equivalent to calling get_project_health + get_coverage_report +
    get_milestone_progress (for each active milestone) individually.

    project: the project ID (int) or exact project name (str).
    run_limit: how many recent runs to include in health analysis (default 10, max 50).

    Returns a dict with three top-level sections:
      health     — aggregate pass/fail stats across recent runs + per_run list
      coverage   — per-suite case coverage breakdown
      milestones — active milestone count + per-milestone progress details

    Note: this tool makes multiple API calls. Expect a short delay for projects
    with many runs, suites, or milestones.
    """
    client = get_client()
    run_limit = min(max(1, run_limit), 50)

    project_id, project_name = _resolve_project(client, project)

    # Fetch runs once; reuse across all sections.
    all_runs = client.get_all(f"get_runs/{project_id}", "runs")
    recent_runs = all_runs[:run_limit]

    # ── Health ────────────────────────────────────────────────────────────────
    health_agg = _aggregate_stats(recent_runs)
    health_per_run = [
        {
            "run_id": r["id"],
            "run_name": r.get("name"),
            "is_completed": r.get("is_completed", False),
            "milestone_id": r.get("milestone_id"),
            **_run_stats(r),
        }
        for r in recent_runs
    ]

    # ── Coverage ──────────────────────────────────────────────────────────────
    suite_mode = client.get_suite_mode(project_id)
    suites = client.get_all(f"get_suites/{project_id}", "suites")

    coverage_by_suite = []
    for suite_obj in suites:
        sid = suite_obj["id"]
        case_params = {"suite_id": sid} if suite_mode == 3 else {}
        cases = client.get_all(f"get_cases/{project_id}", "cases", params=case_params)

        if suite_mode == 3:
            suite_runs = [r for r in all_runs if r.get("suite_id") == sid]
        else:
            suite_runs = all_runs

        if suite_runs:
            agg_exec = sum(_run_stats(r)["executed"] for r in suite_runs)
            agg_tot = sum(_run_stats(r)["total"] for r in suite_runs)
            exec_rate = round(agg_exec / agg_tot * 100, 1) if agg_tot > 0 else 0.0
        else:
            exec_rate = 0.0

        coverage_by_suite.append({
            "suite_id": sid,
            "suite_name": suite_obj.get("name"),
            "total_cases": len(cases),
            "total_runs": len(suite_runs),
            "execution_rate_pct": exec_rate,
        })

        # Single-suite projects have only one suite — stop after the first.
        if suite_mode != 3:
            break

    # ── Milestones ────────────────────────────────────────────────────────────
    all_milestones = client.get_all(f"get_milestones/{project_id}", "milestones")
    active_milestones = [m for m in all_milestones if not m.get("is_completed", False)]

    milestone_details = []
    for ms in active_milestones:
        ms_runs = [r for r in all_runs if r.get("milestone_id") == ms["id"]]
        ms_agg = _aggregate_stats(ms_runs)
        milestone_details.append({
            "milestone_id": ms["id"],
            "milestone_name": ms.get("name"),
            "due_on": ms.get("due_on"),
            "total_runs": len(ms_runs),
            **ms_agg,
        })

    return {
        "project_id": project_id,
        "project_name": project_name,
        "health": {
            "runs_analyzed": len(recent_runs),
            **health_agg,
            "per_run": health_per_run,
        },
        "coverage": coverage_by_suite,
        "milestones": {
            "active_count": len(active_milestones),
            "completed_count": len(all_milestones) - len(active_milestones),
            "details": milestone_details,
        },
    }
