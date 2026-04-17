# TestRail MCP Server

An MCP (Model Context Protocol) server for interacting with TestRail. Manage test cases, sections, suites, plans, runs, and results — or import entire test scenario files — directly from any MCP-compatible AI client.

---

## Requirements

- [Docker](https://www.docker.com/) — for containerized HTTP use
- **or** [uv](https://docs.astral.sh/uv/) + Python 3.12 — for local STDIO use
- A TestRail account with API access enabled

---

## Setup

### 1. Get your TestRail API key

In TestRail: **My Settings → API Keys → Add Key**

### 2. Configure environment variables

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `TESTRAIL_URL` | ✅ | Your TestRail instance URL, e.g. `https://yourorg.testrail.io` |
| `TESTRAIL_EMAIL` | ✅ | Your TestRail login email |
| `TESTRAIL_API_KEY` | ✅ | Your TestRail API key |
| `TRANSPORT` | — | `http` (default) or `stdio` |
| `PORT` | — | HTTP server port (default: `8000`) |

---

## Running the Server

### Option A — Docker (HTTP transport, recommended for sharing)

```bash
docker compose up --build
```

The server will be available at `http://localhost:8000/mcp`.

To use a different external port (e.g., if 8000 is taken):

```bash
PORT=9090 docker compose up --build
```

Then point your MCP client at `http://localhost:9090/mcp`.

---

### Option B — Local with uv (STDIO transport, for Claude Desktop / Cursor)

Install dependencies:

```bash
uv sync
```

Run directly:

```bash
TRANSPORT=stdio uv run python -m testrail_mcp
```

Or set `TRANSPORT=stdio` in your `.env` file.

---

## MCP Client Configuration

### HTTP (Docker) — Claude Desktop / Cursor

```json
{
  "mcpServers": {
    "testrail": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### STDIO (local uv) — Claude Desktop

```json
{
  "mcpServers": {
    "testrail": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/testrail-mcp", "python", "-m", "testrail_mcp"],
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

---

## Development Status

| Phase | Description | Status |
|---|---|---|
| 1 | Project scaffold, structure, Docker | ✅ Complete |
| 2 | TestRail client wrapper (auth, pagination, retries, errors) | 🔜 Next |
| 3 | Core read tools (projects, suites, sections, cases, plans, runs) | ⬜ Pending |
| 4 | Write tools (add/update/delete cases, sections, runs, results) | ⬜ Pending |
| 5 | File ingestion (import scenarios from .md / Gherkin files) | ⬜ Pending |
| 6 | Workflow & metrics tools | ⬜ Pending |
| 7 | Prompt templates | ⬜ Pending |
| 8 | Polish & publish | ⬜ Pending |
