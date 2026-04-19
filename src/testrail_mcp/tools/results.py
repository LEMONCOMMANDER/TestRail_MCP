"""
Read and write tools for TestRail test results.

Phase 3 (this file): list_results, list_results_for_case
Phase 4 (this file): add_result, add_results_for_cases
"""

from testrail_mcp.server import mcp, get_client


@mcp.tool
def list_results(test_id: int, limit: int = 50) -> list[dict]:
    """
    List results for a specific test (a test case instance within a run).

    Results are returned in reverse chronological order (newest first).
    Each result includes status_id, comment, elapsed time, and who added it.

    status_id values: 1=Passed, 2=Blocked, 3=Untested, 4=Retest, 5=Failed

    Use get_run to find tests within a run, then use the test id here.
    limit controls how many results to return (default 50, max 250).
    """
    return get_client().get_all(
        f"get_results/{test_id}",
        "results",
        params={"limit": min(limit, 250)},
    )


@mcp.tool
def list_results_for_case(run_id: int, case_id: int, limit: int = 50) -> list[dict]:
    """
    List results for a specific test case within a specific test run.

    Useful when you know the case_id and run_id but not the test_id.
    Results are returned in reverse chronological order (newest first).

    status_id values: 1=Passed, 2=Blocked, 3=Untested, 4=Retest, 5=Failed

    Use list_runs to find run_id and list_cases to find case_id.
    limit controls how many results to return (default 50, max 250).
    """
    return get_client().get_all(
        f"get_results_for_case/{run_id}/{case_id}",
        "results",
        params={"limit": min(limit, 250)},
    )

