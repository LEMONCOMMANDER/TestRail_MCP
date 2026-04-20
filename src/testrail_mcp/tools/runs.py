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


@mcp.tool
def add_run(
    project_id: int,
    name: str,
    suite_id: int | None = None,
    description: str | None = None,
    milestone_id: int | None = None,
    assignedto_id: int | None = None,
    include_all: bool = True,
    case_ids: list[int] | None = None,
) -> dict:
    """
    Create a new test run in a project.

    name is the display name for the run (required).

    suite_id is required for projects with multiple suites (suite_mode = 3).
    Use list_suites to find the correct suite_id.

    include_all: if True (default), the run includes all test cases in the suite.
    If False, only the cases listed in case_ids are included.

    case_ids: list of specific case IDs to include when include_all is False.

    milestone_id optionally links the run to a release milestone.
    assignedto_id optionally assigns the run to a specific user.
    """
    client = get_client()
    suite_mode = client.get_suite_mode(project_id)

    if suite_mode == 3 and suite_id is None:
        raise ValueError(
            f"Project {project_id} uses multiple suites (suite_mode=3). "
            "Provide a suite_id — use list_suites to find available suites."
        )

    body: dict = {"name": name, "include_all": include_all}
    if suite_id is not None:
        body["suite_id"] = suite_id
    if description is not None:
        body["description"] = description
    if milestone_id is not None:
        body["milestone_id"] = milestone_id
    if assignedto_id is not None:
        body["assignedto_id"] = assignedto_id
    if case_ids is not None:
        body["case_ids"] = case_ids

    return client.post(f"add_run/{project_id}", body)


@mcp.tool
def update_run(
    run_id: int,
    name: str | None = None,
    description: str | None = None,
    milestone_id: int | None = None,
    include_all: bool | None = None,
    case_ids: list[int] | None = None,
) -> dict:
    """
    Update an existing test run.

    Only fields provided will be changed; omit any field to leave it unchanged.
    """
    body: dict = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if milestone_id is not None:
        body["milestone_id"] = milestone_id
    if include_all is not None:
        body["include_all"] = include_all
    if case_ids is not None:
        body["case_ids"] = case_ids

    return get_client().post(f"update_run/{run_id}", body)


@mcp.tool
def close_run(run_id: int) -> dict:
    """
    Close a test run, marking it as completed.

    Closed runs are read-only — no further results can be added.
    Use this when a test cycle is finished.
    This action cannot be undone via the API.
    """
    return get_client().post(f"close_run/{run_id}")


@mcp.tool
def delete_run(run_id: int) -> dict:
    """
    Permanently delete a test run and all its results.

    WARNING: This cannot be undone. All result history in the run
    will be permanently lost.

    Only use this in test/sandbox projects.
    """
    return get_client().post(f"delete_run/{run_id}")

