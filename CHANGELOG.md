# Changelog

All notable changes to this project will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/): MAJOR.MINOR.PATCH

---

## [1.0.0] — 2026-04-20

### Added
- Full TestRail MCP server built on FastMCP with stdio and HTTP transport support
- **45 tools** across all TestRail resource types:
  - Projects, suites, sections, test cases (read + write)
  - Test plans, test runs, test results (read + write)
  - Milestones (read + write)
  - File ingestion: `import_from_file` and `import_scenarios` (Gherkin, Markdown, numbered list)
  - Metrics and workflow tools: `get_run_summary`, `get_project_health`, `get_coverage_report`,
    `get_milestone_progress`, `get_full_project_report`
- **4 prompt templates** for guided AI workflows:
  - `import_test_scenarios` — import a test file with format auto-detection
  - `generate_project_report` — structured health and coverage report
  - `triage_test_failures` — prioritised failure analysis with recommended actions
  - `create_test_cases_from_description` — BDD scenario generation from natural language
- Name-based lookup across all workflow tools — pass project/suite/section names instead of IDs
- Automatic pagination, retry with exponential backoff, and normalised error messages in the API client
- Docker support with `docker-compose.yml` for HTTP transport
- MCP client configuration examples for Claude Desktop, Cursor, and VS Code
- Startup validation with clear error messages for missing environment variables
- MIT License

---

<!-- Add new versions above this line in the same format:

## [X.Y.Z] — YYYY-MM-DD

### Added
- New features

### Changed
- Changes to existing behaviour

### Fixed
- Bug fixes

### Removed
- Removed features

-->
