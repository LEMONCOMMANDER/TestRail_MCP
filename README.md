# TestRail MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server for TestRail. Connect any MCP-compatible AI client — Claude Desktop, Cursor, VS Code — and manage your entire TestRail workflow through natural language.

**What you can do:**
- Import test scenarios from Gherkin, Markdown, or numbered-list files directly into TestRail
- Create, update, and delete test cases, sections, suites, runs, plans, and results
- Generate health reports, coverage metrics, and milestone progress summaries
- Use built-in prompt templates to guide the AI through common workflows without manual tool calls

---

## Requirements

- A TestRail account with API access enabled (My Settings → API Keys)
- **For local use:** [uv](https://docs.astral.sh/uv/) + Python 3.12+
- **For Docker use:** [Docker](https://www.docker.com/)

---

## Quick Start (under 10 minutes)

### Step 1 — Get your credentials

In TestRail: **My Settings → API Keys → Add Key**

You need three values:
- Your TestRail instance URL (e.g. `https://yourorg.testrail.io`)
- Your login email
- Your API key

### Step 2 — Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
TESTRAIL_URL=https://yourorg.testrail.io
TESTRAIL_EMAIL=your@email.com
TESTRAIL_API_KEY=your_api_key_here
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `TESTRAIL_URL` | ✅ | — | TestRail instance URL, no trailing slash |
| `TESTRAIL_EMAIL` | ✅ | — | Your TestRail login email |
| `TESTRAIL_API_KEY` | ✅ | — | Your TestRail API key |
| `TRANSPORT` | — | `http` | `http` for Docker/remote, `stdio` for Claude Desktop/Cursor |
| `PORT` | — | `8000` | HTTP server port (only used when `TRANSPORT=http`) |

If any required variable is missing, the server will exit immediately with a clear error message naming exactly which variable is not set.

### Step 3 — Run the server

**Option A — Local with uv (recommended for Claude Desktop / Cursor)**

```bash
uv sync
TRANSPORT=stdio uv run python -m testrail_mcp
```

Or set `TRANSPORT=stdio` in your `.env` file and run:

```bash
uv run python -m testrail_mcp
```

**Option B — Docker (recommended for HTTP/shared use)**

```bash
docker compose up --build
```

The server starts at `http://localhost:8000/mcp`.

### Step 4 — Connect your AI client

See [MCP Client Configuration](#mcp-client-configuration) below.

---

## MCP Client Configuration

### Claude Desktop — STDIO (local uv)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "testrail": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/TestRail_MCP", "python", "-m", "testrail_mcp"],
      "env": {
        "TESTRAIL_URL": "https://yourorg.testrail.io",
        "TESTRAIL_EMAIL": "your@email.com",
        "TESTRAIL_API_KEY": "your_api_key_here",
        "TRANSPORT": "stdio"
      }
    }
  }
}
```

Replace `/absolute/path/to/TestRail_MCP` with the actual path to this repository.

### Cursor — STDIO (local uv)

Add to your Cursor MCP settings (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "testrail": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/TestRail_MCP", "python", "-m", "testrail_mcp"],
      "env": {
        "TESTRAIL_URL": "https://yourorg.testrail.io",
        "TESTRAIL_EMAIL": "your@email.com",
        "TESTRAIL_API_KEY": "your_api_key_here",
        "TRANSPORT": "stdio"
      }
    }
  }
}
```

### VS Code (GitHub Copilot) — STDIO

Add to your VS Code `settings.json`:

```json
{
  "mcp": {
    "servers": {
      "testrail": {
        "type": "stdio",
        "command": "uv",
        "args": ["run", "--directory", "/absolute/path/to/TestRail_MCP", "python", "-m", "testrail_mcp"],
        "env": {
          "TESTRAIL_URL": "https://yourorg.testrail.io",
          "TESTRAIL_EMAIL": "your@email.com",
          "TESTRAIL_API_KEY": "your_api_key_here",
          "TRANSPORT": "stdio"
        }
      }
    }
  }
}
```

### HTTP (Docker) — Any MCP client

Start the server with `docker compose up --build`, then point your client at:

```
http://localhost:8000/mcp
```

For clients that take a URL directly:

```json
{
  "mcpServers": {
    "testrail": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

---

## Prompt Templates

The server ships with four built-in prompt templates. Select them from your AI client's prompt picker to start a guided workflow.

| Prompt | Description |
|---|---|
| `import_test_scenarios` | Import a Gherkin, Markdown, or numbered-list file into TestRail. Auto-detects the format, confirms the target section, and reports results. |
| `generate_project_report` | Generate a structured health report for a project — pass rate, coverage, and milestone progress in one response. |
| `triage_test_failures` | Analyse a test run's results and produce a prioritised triage summary with recommended actions. |
| `create_test_cases_from_description` | Convert a natural-language feature description into BDD test cases, review them with you, then import to TestRail. |

**Example usage (no prompt template needed):**

> *"Import this feature file into the Login Tests section of My App"*
> *"Give me a full health report for the Sample Project"*
> *"How did the Sprint 5 regression run go?"*

---

## Tools Reference

### Projects
| Tool | Description |
|---|---|
| `list_projects` | List all accessible TestRail projects |
| `get_project` | Get details for a single project |

### Suites
| Tool | Description |
|---|---|
| `list_suites` | List all suites in a project |
| `get_suite` | Get details for a single suite |
| `add_suite` | Create a new suite |
| `update_suite` | Update a suite's name or description |
| `delete_suite` | Permanently delete a suite and all its cases |

### Sections
| Tool | Description |
|---|---|
| `list_sections` | List all sections in a project or suite |
| `get_section` | Get details for a single section |
| `add_section` | Create a new section |
| `update_section` | Update a section's name or description |
| `delete_section` | Permanently delete a section and all its cases |

### Test Cases
| Tool | Description |
|---|---|
| `list_cases` | List cases in a project, optionally filtered by suite or section |
| `get_case` | Get full details for a single case |
| `add_case` | Create a new test case |
| `update_case` | Update an existing test case |
| `delete_case` | Permanently delete a test case |

### Test Plans
| Tool | Description |
|---|---|
| `list_plans` | List all test plans in a project |
| `get_plan` | Get details for a single plan |
| `add_plan` | Create a new test plan |
| `update_plan` | Update a test plan |
| `close_plan` | Close a test plan (read-only after closing) |
| `delete_plan` | Permanently delete a test plan |

### Test Runs
| Tool | Description |
|---|---|
| `list_runs` | List all test runs in a project |
| `get_run` | Get details for a single run |
| `add_run` | Create a new test run |
| `update_run` | Update a test run |
| `close_run` | Close a test run |
| `delete_run` | Permanently delete a test run |

### Results
| Tool | Description |
|---|---|
| `list_results` | List results for a specific test |
| `list_results_for_case` | List results for a case within a run |
| `add_result` | Add a result to a test |
| `add_results_for_cases` | Add results for multiple cases in one request |

### Milestones
| Tool | Description |
|---|---|
| `list_milestones` | List all milestones in a project |
| `get_milestone` | Get details for a single milestone |
| `add_milestone` | Create a new milestone |
| `update_milestone` | Update a milestone |
| `delete_milestone` | Permanently delete a milestone |

### File Import
| Tool | Description |
|---|---|
| `import_from_file` | Parse and import scenarios by section ID (max 500KB) |
| `import_scenarios` | Import scenarios using project/suite/section names or IDs |

### Metrics & Reports
| Tool | Description |
|---|---|
| `get_run_summary` | Pass/fail/coverage stats for a test run |
| `get_milestone_progress` | Aggregate pass/fail metrics across a milestone's runs |
| `get_project_health` | Aggregate health across the N most recent runs |
| `get_coverage_report` | Case execution coverage for a project or suite |
| `get_full_project_report` | Comprehensive report combining all metrics in one call |

---

## Supported Import Formats

| Format | `fmt` value | Description |
|---|---|---|
| Gherkin / BDD | `gherkin` | `Feature` / `Scenario` / `Given` / `When` / `Then` blocks |
| Markdown | `markdown` | `##` or `###` headings as titles, body as BDD steps or description |
| Numbered list | `numbered` | `1. Title` lines as case titles (no step content) |

---

## Troubleshooting

**Server exits immediately with "environment variables are not set"**
→ Check your `.env` file exists, is in the project root, and contains all three required variables.

**`401 Authentication failed`**
→ Verify `TESTRAIL_EMAIL` and `TESTRAIL_API_KEY` are correct. Confirm API access is enabled in TestRail under My Settings → API Keys.

**`400 Bad request` when creating cases**
→ Verify the `section_id` exists and belongs to the project. Use `list_sections` to find valid IDs.

**Multi-suite project errors**
→ Projects with `suite_mode=3` require a `suite_id` for section and case operations. Use `list_suites` to find the correct ID, or pass the suite name to workflow tools.

**Import creates cases but BDD steps are empty**
→ Ensure `TRANSPORT=stdio` is set when running locally. Confirm your TestRail instance has the BDD template (template_id=4) enabled.

---

## Development Status

| Phase | Description | Status |
|---|---|---|
| 1 | Project scaffold, structure, Docker | ✅ Complete |
| 2 | TestRail client wrapper (auth, pagination, retries, errors) | ✅ Complete |
| 3 | Core read tools (projects, suites, sections, cases, plans, runs) | ✅ Complete |
| 4 | Write tools (add/update/delete cases, sections, runs, results) | ✅ Complete |
| 5 | File ingestion (import scenarios from Gherkin / Markdown files) | ✅ Complete |
| 6 | Workflow & metrics tools | ✅ Complete |
| 7 | Prompt templates | ✅ Complete |
| 8 | Polish & publish | ✅ Complete |

