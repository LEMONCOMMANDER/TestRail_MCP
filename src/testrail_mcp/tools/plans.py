"""
Read and write tools for TestRail test plans.

Phase 3 (this file): list_plans, get_plan
Phase 4 (this file): add_plan, update_plan, close_plan, delete_plan
"""

from testrail_mcp.server import mcp, get_client


@mcp.tool
def list_plans(project_id: int) -> list[dict]:
    """
    List all test plans in a project.

    Test plans group related test runs together, often aligned to a milestone
    or release. Returns a summary list — use get_plan for full run details.
    """
    return get_client().get_all(f"get_plans/{project_id}", "plans")


@mcp.tool
def get_plan(plan_id: int) -> dict:
    """
    Get full details of a single test plan, including all its runs and entries.

    Use list_plans to find the correct plan_id.
    """
    return get_client().get(f"get_plan/{plan_id}")

