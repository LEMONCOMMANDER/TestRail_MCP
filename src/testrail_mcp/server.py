from fastmcp import FastMCP

from testrail_mcp.config import Settings

mcp = FastMCP(
    "TestRail MCP",
    instructions=(
        "MCP server for interacting with TestRail. Use this server to manage test cases, "
        "sections, suites, test plans, test runs, and results. You can also import test "
        "scenarios from markdown or Gherkin files, retrieve pass/fail metrics, and manage "
        "your full testing workflow. Always use get/list tools before write tools to confirm "
        "the correct IDs for the target project, suite, and section."
    ),
)

# Tool modules are imported and registered here as each phase is completed.
# Phase 3: cases, sections, suites, plans, runs, results (read)
# Phase 4: cases, sections, suites, plans, runs, results (write)
# Phase 5: file ingestion
# Phase 6: workflow and metrics tools


def main() -> None:
    settings = Settings()

    if settings.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="http", host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()
