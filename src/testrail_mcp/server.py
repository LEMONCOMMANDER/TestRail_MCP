from fastmcp import FastMCP

from testrail_mcp.client import TestRailClient
from testrail_mcp.config import Settings

mcp = FastMCP(
    "TestRail MCP",
    instructions=(
        "MCP server for interacting with TestRail. "
        "Use this server to manage test cases, sections, suites, test plans, "
        "test runs, and results. You can also import test scenarios from markdown "
        "or Gherkin files, retrieve pass/fail metrics, and manage your full "
        "testing workflow.\n\n"
        "IMPORTANT — before starting any task:\n"
        "1. Call prompts/list to see all available prompt templates. Each prompt "
        "encodes the correct workflow, field mappings, and rules for common tasks "
        "(importing scenarios, reporting, triage, case generation). Always prefer "
        "a matching prompt over ad-hoc tool calls — it will produce better results "
        "with fewer iterations.\n"
        "2. If no prompt matches, call tools/list to see all available tools before "
        "deciding on an approach.\n"
        "3. When writing or importing test cases, always use get/list tools first "
        "to confirm the correct IDs for the target project, suite, and section.\n"
        "4. For importing a structured markdown file (with ## / ### headings), use "
        "import_from_hierarchy — it auto-creates sections and cases in one call. "
        "For a flat list of scenarios into one section, use import_scenarios."
    ),
)

# Shared client instance — initialised in main() before the server starts.
# Tools call get_client() to access it; it is never None during normal operation.
client: TestRailClient | None = None


def get_client() -> TestRailClient:
    """Return the shared TestRailClient. Called by tool modules."""
    if client is None:
        raise RuntimeError("TestRailClient has not been initialised. Is the server running?")
    return client


# Tool modules are imported after mcp and get_client are defined so that the
# @mcp.tool decorators and get_client references resolve without circular import
# errors. Add new modules here as each phase is completed.
from testrail_mcp.tools import (  # noqa: E402, F401
    projects,
    suites,
    sections,
    cases,
    plans,
    runs,
    results,
    milestones,
    importer,
    workflows,
)
from testrail_mcp import prompt_templates  # noqa: F401


def main() -> None:
    global client
    settings = Settings()
    client = TestRailClient(
        url=settings.testrail_url,
        email=settings.testrail_email,
        api_key=settings.testrail_api_key,
    )

    if settings.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="http", host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()
