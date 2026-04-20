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


@mcp.tool
def add_result(
    test_id: int,
    status_id: int,
    comment: str | None = None,
    elapsed: str | None = None,
    defects: str | None = None,
    assignedto_id: int | None = None,
) -> dict:
    """
    Add a result to a specific test within a run.

    test_id is the ID of the test instance (not the case ID) within the run.
    Use get_run to list tests and find the correct test_id.

    status_id (required): 1=Passed, 2=Blocked, 3=Untested, 4=Retest, 5=Failed

    comment: free-text notes about the result (e.g. failure details, observations)
    elapsed: time taken, e.g. "30s", "1m 45s", "2h 30m"
    defects: comma-separated defect/ticket IDs, e.g. "PROJ-123,PROJ-456"
    assignedto_id: reassign the test to a different user for follow-up
    """
    body: dict = {"status_id": status_id}
    if comment is not None:
        body["comment"] = comment
    if elapsed is not None:
        body["elapsed"] = elapsed
    if defects is not None:
        body["defects"] = defects
    if assignedto_id is not None:
        body["assignedto_id"] = assignedto_id

    return get_client().post(f"add_result/{test_id}", body)


@mcp.tool
def add_results_for_cases(
    run_id: int,
    results: list[dict],
) -> list[dict]:
    """
    Add results for multiple test cases in a single request.

    run_id is the ID of the test run to add results to.

    results is a list of result objects. Each object must include:
      - case_id (int): the test case ID
      - status_id (int): 1=Passed, 2=Blocked, 3=Untested, 4=Retest, 5=Failed

    Each result object may optionally include:
      - comment (str): notes about the result
      - elapsed (str): time taken, e.g. "30s", "2m 15s"
      - defects (str): comma-separated ticket IDs

    Example results value:
      [
        {"case_id": 101, "status_id": 1, "comment": "Passed on first attempt"},
        {"case_id": 102, "status_id": 5, "comment": "Failed — see PROJ-99"},
      ]

    Use this instead of repeated add_result calls when recording bulk results,
    especially during file ingestion workflows.
    """
    return get_client().post(f"add_results_for_cases/{run_id}", {"results": results})

