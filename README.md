# TestRail MCP Server

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Build](https://github.com/jtroop/TestRail_MCP/actions/workflows/publish.yml/badge.svg)

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

## Quick Start

### Step 1 — Get your credentials

In TestRail: **My Settings → API Keys → Add Key**

You need three values:
- Your TestRail instance URL (e.g. `https://yourorg.testrail.io`)
- Your login email
- Your API key

**NOTE:** You will need to enable API access in TestRail. Admin > Site Settings > API > Enable API = ON

### Step 2 — Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
TESTRAIL_URL=https://yourorg.testrail.io
TESTRAIL_EMAIL=your@email.com
TESTRAIL_API_KEY=your_api_key_here
TRANSPORT=stdio
```

| Variable | Required | Default | Description |
|---|---|---|---|
| `TESTRAIL_URL` | ✅ | — | TestRail instance URL, no trailing slash |
| `TESTRAIL_EMAIL` | ✅ | — | Your TestRail login email |
| `TESTRAIL_API_KEY` | ✅ | — | Your TestRail API key |
| `TRANSPORT` | — | `http` | `stdio` for local AI clients, `http` for Docker |
| `PORT` | — | `8000` | HTTP server port (only used when `TRANSPORT=http`) |

The server reads this file automatically at startup — you never need to put credentials anywhere else.

> **Already have a `.env` in your project?** If you're adding the TestRail MCP server to an existing project that already has a `.env`, just append the four variables above to it. `docker compose` and the local server both pick up `.env` from the working directory.

If any required variable is missing, the server will exit immediately with a clear error message naming exactly which variable is not set.

### Step 3 — Run the server

**Option A — Local (STDIO) — for VS Code, Cursor, JetBrains, Claude Desktop**

```bash
uv sync
uv run python -m testrail_mcp --ide <your_ide>
```
See MCP Client Configuration section below for IDE-specific setup instructions. Supported IDE values are: `vscode`, `cursor`, `jetbrains`.


The server is managed by your AI client — you don't leave this running in a terminal. The setup script in Step 4 tells your client how to launch it.

**Option B — Docker pre-built image**

No clone required. Pull and run directly:

```bash
# Create a .env with your credentials (see Step 2)
docker run -d \
  --env-file .env \
  -p 8000:8000 \
  ghcr.io/jtroop/testrail-mcp:latest
```

The server starts at `http://localhost:8000/mcp`. Point your MCP client at that URL — no setup script needed.

**Option C — Docker build from source**

```bash
docker compose up --build
```

The server starts at `http://localhost:8000/mcp`.

### Step 4 — Connect your AI client

> **Docker users** — skip this step. Your server is already running at `http://localhost:8000/mcp`. See [HTTP (Docker)](#http-docker--any-mcp-client) below to configure your client.

For local (STDIO) use, run the setup script once after cloning. It writes the correct config file for your AI client — no manual JSON editing required:

```bash
# Interactive (prompts you to pick your IDE):
uv run python scripts/setup_mcp.py

# Or pass your IDE directly:
uv run python scripts/setup_mcp.py --ide vscode
uv run python scripts/setup_mcp.py --ide cursor
uv run python scripts/setup_mcp.py --ide jetbrains
uv run python scripts/setup_mcp.py --ide claude
```

Credentials are **not** written into the config file — the server reads them from your `.env` at runtime.

| `--ide` value | File written | Notes |
|---|---|---|
| `vscode` | `.vscode/mcp.json` | Auto-discovered when you open the project |
| `cursor` | `.cursor/mcp.json` | Auto-discovered when you open the project |
| `jetbrains` | `.idea/mcp.json` | Requires AI Assistant plugin (see below) |
| `claude` | `~/Library/Application Support/Claude/claude_desktop_config.json` | Merges safely with existing config |

These files are gitignored — they contain your local absolute path and are not meant to be committed.

---

## MCP Client Configuration

### VS Code (GitHub Copilot)

Run `uv run python scripts/setup_mcp.py --ide vscode`. This writes `.vscode/mcp.json`, which VS Code auto-discovers when you open the project folder.

No credentials in the config — VS Code launches the server with `uv run --directory <project>`, which sets the working directory so the `.env` file is loaded automatically.

### Cursor

Run `uv run python scripts/setup_mcp.py --ide cursor`. This writes `.cursor/mcp.json`, which Cursor auto-discovers when you open the project folder.

### JetBrains (any IDE — RubyMine, IntelliJ, PyCharm, WebStorm, etc.)

Run `uv run python scripts/setup_mcp.py --ide jetbrains`. This writes `.idea/mcp.json`.

All JetBrains IDEs use the same `.idea/` project folder, so this config works across every JetBrains product. Requires JetBrains IDE **2024.3+** with the AI Assistant plugin: **Settings → Tools → AI Assistant → MCP Servers**. See the [JetBrains MCP documentation](https://www.jetbrains.com/help/idea/mcp-server.html) for details.

### Claude Desktop

Run `uv run python scripts/setup_mcp.py --ide claude`. This writes (or merges into) the global Claude Desktop config at:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Restart Claude Desktop after running the script.

### HTTP (Docker) — Any MCP client

Start the server with `docker compose up` (or `docker run` as shown above), then configure your MCP client to connect at:

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

No setup script needed for Docker — the server is already running and credentials are supplied via `--env-file .env`.

---

## Adding to an Existing docker-compose

If you already have a `docker-compose.yml` for another project and want the TestRail MCP server to start alongside it, add this service block:

```yaml
services:
  # ... your existing services ...

  testrail-mcp:
    image: ghcr.io/jtroop/testrail-mcp:latest
    ports:
      - "8000:8000"
    environment:
      TESTRAIL_URL: ${TESTRAIL_URL}
      TESTRAIL_EMAIL: ${TESTRAIL_EMAIL}
      TESTRAIL_API_KEY: ${TESTRAIL_API_KEY}
      TRANSPORT: http
      PORT: 8000
    restart: unless-stopped
```

Then add the three `TESTRAIL_*` variables to your existing `.env` file. No other changes needed — `docker compose up` will start the TestRail server alongside your app.

Configure your MCP client to connect via `http://localhost:8000/mcp` using the HTTP config block above.

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

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a full history of releases and changes.

---

## License

[MIT](LICENSE) — free to use, modify, and distribute. See the LICENSE file for details.

