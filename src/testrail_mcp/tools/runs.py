"""
Read and write tools for TestRail test runs.

Phase 3 (this file): list_runs, get_run
Phase 4 (this file): add_run, update_run, close_run, delete_run
"""

from testrail_mcp.server import mcp, get_client


@mcp.tool
def list_runs(project_id: int) -> list[dict]:
    """
    List all test runs in a project.

    Test runs are executable instances of a set of test cases.
    They can be standalone or part of a test plan.
    Returns a summary list — use get_run for full test details.
    """
    return get_client().get_all(f"get_runs/{project_id}", "runs")


@mcp.tool
def get_run(run_id: int) -> dict:
    """
    Get full details of a single test run.

    Returns the run's name, status counts (passed, failed, untested),
    the suite it draws from, and the assigned milestone if any.
    Use list_runs to find the correct run_id.
    """
    return get_client().get(f"get_run/{run_id}")

