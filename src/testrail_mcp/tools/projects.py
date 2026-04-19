"""
Read and write tools for TestRail projects.

Phase 3 (this file): list_projects, get_project
"""

from testrail_mcp.server import mcp, get_client


@mcp.tool
def list_projects() -> list[dict]:
    """
    List all TestRail projects accessible to the configured user.

    Returns a list of projects each with id, name, and suite_mode.
    Always call this first to find the correct project_id before using
    any other tools.

    suite_mode values:
      1 = Single suite (suite_id not required)
      2 = Single suite with baselines
      3 = Multiple suites (suite_id required for sections and cases)
    """
    return get_client().get_all("get_projects", "projects")


@mcp.tool
def get_project(project_id: int) -> dict:
    """
    Get full details of a single TestRail project.

    Use list_projects first to find the correct project_id.
    """
    return get_client().get(f"get_project/{project_id}")
