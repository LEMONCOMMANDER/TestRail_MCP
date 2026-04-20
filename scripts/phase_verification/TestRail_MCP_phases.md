Phase 1 — Project Scaffold Set up the Python project structure, dependency management, and Docker skeleton. Establish the two-wrapper architecture: the FastMCP server shell and the TestRail Client wrapper with auth and base URL wiring. Nothing functional yet — just the foundation everything else builds on. Include the PORT env var alongside the
 credential env vars.

Phase 1 — Scaffold What to look for (no running code yet):

 - Folder structure matches the plan — does each layer have its own home?
 - Dockerfile exists and references the right entry point
 - docker-compose.yml has all three credential env vars plus PORT
 - A README.md stub exists with the env var names documented
 - Running docker build completes without errors — the image should build even if it does nothing yet
 - Running the server locally (outside Docker) should start without crashing
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  Phase 2 — TestRail Client Wrapper (Cross-Cutting Concerns) Before writing a single tool, finish the client wrapper completely. This means: pagination auto-handling, retry logic with exponential backoff for transient errors (429, 500, 503), hard fail-fast for permanent errors (401, 403, 404, 400), error response normalization into clean human-readable
  messages, and suite mode detection. Every tool built after this point gets all of it for free.


Phase 2 — TestRail Client Wrapper This is the most important phase to review carefully — bugs here affect everything:

 - Run the client directly (not through MCP) with valid credentials → should return data
 - Run with invalid credentials → should return a clear auth error, not a Python stack trace
 - Point it at a project with many cases (100+) and request them all → verify the count matches what TestRail shows (pagination working)
 - Temporarily point at a bad URL → should fail gracefully, not hang indefinitely
 - Check that a 429 response triggers a retry with a wait, not an immediate crash
 - Check that a 404 fails immediately without retrying
 - You don't need a test framework for this — a simple throwaway script that calls the client directly is enough

  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  Phase 3 — Core Read Tools (Layer 1 Atomic) Build all the GET operations: projects, suites, sections, cases, plans, runs, results, milestones. Strict read-only, clearly named with get_ / list_ prefixes. This is the safe foundation — no risk of unintended data changes.

Phase 3 — Read Tools Use FastMCP's built-in dev inspector for this:

 - FastMCP ships with a fastmcp dev command that opens a visual interface to call your tools manually — use this throughout
 - Call list_projects → verify it returns your real TestRail projects by name
 - Call get_cases on a known project/section → verify case count and titles match what you see in TestRail's UI
 - Call a tool with a bad ID (e.g., a section that doesn't exist) → verify the error message is readable and helpful, not a raw API dump
 - Call list_sections on both a single-suite and multi-suite project if you have both → verify suite mode handling works transparently
 - Nothing should be changing data at this phase — safe to run against a real TestRail instance

  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  Phase 4 — Write Tools (Layer 1 Atomic) Build all the mutation operations: add_, update_, delete_ for cases, sections, suites, runs, plans, results. Each tool accepts standard fields explicitly plus an open-ended custom fields bucket for org-specific fields. Kept strictly separate from read tools.

Phase 4 — Write Tools Important: use a dedicated throwaway test project in TestRail — never test writes against real project data:

 - Call add_section → verify it appears in TestRail UI immediately
 - Call add_case with only required fields → verify it creates correctly
 - Call add_case with a custom fields dict → verify those fields populate in TestRail
 - Call update_case → verify the change is reflected in the UI
 - Call delete_case → verify it's gone
 - Try passing obviously wrong input (e.g., a string where a number is expected) → verify the error is caught before hitting the API, not after
 - After each test, manually check the TestRail UI — the source of truth is always what actually appeared there, not what the tool reported back
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  Phase 5 — File Ingestion Tool Build the import_from_file tool. Enforce the size limit gate at entry, validate content is valid text, accept a format parameter (markdown headers, Gherkin, numbered list, etc.) to drive parsing, and process scenarios in batches through the write tools from Phase 4. This is intentionally its own phase because it depends on
  write tools being solid first.

Phase 5 — File Ingestion This phase has the most edge cases to check:

 - Pass a small, well-formed markdown file → verify scenarios are parsed correctly and cases appear in TestRail
 - Pass the same content in each supported format (Gherkin, numbered list, etc.) → each should parse correctly
 - Pass a file that's just under your size limit → should work
 - Pass a file that's just over your size limit → should be rejected with a clear message before any processing starts
 - Pass a file with 50+ scenarios → verify they all get created (chunking works) and none are skipped
 - Pass a file with some malformed/incomplete scenarios → verify the tool handles partial failures gracefully (creates the valid ones, reports which ones failed)
 - Try passing binary content (e.g., rename a .png to .md) → should be rejected at content validation
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  Phase 6 — Workflow Tools (Layer 2) Build higher-level tools that orchestrate the atomic tools for known workflows — primarily the "port test scenarios" use case. These call Phase 3/4/5 tools internally in a defined sequence so the LLM doesn't have to figure out the orchestration every time. Also build any metrics/reporting tools here (pass/fail
  summaries, milestone progress, etc.).

Phase 6 — Workflow Tools End-to-end integration review:

 - Run the full "import test scenarios" workflow from a real markdown file you'd actually use — does the end result in TestRail look right?
 - Run a metrics tool on a project with known results → verify the numbers match what TestRail's built-in reports show
 - Check that workflow tools fail gracefully if a dependency step fails (e.g., section creation fails → tool should stop and report, not silently continue creating orphaned cases)
 - This is a good phase to have someone else (or a fresh set of eyes) try the workflow cold — if they can follow it without explanation, it's working
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  Phase 7 — Prompt Templates Define reusable MCP Prompts — the instruction templates that guide the LLM when using the server. The primary one is the "import scenarios" prompt that tells the LLM how to interpret an uploaded file and map its contents to TestRail fields. These make the server dramatically more useful out of the box.


Phase 7 — Prompt Templates This is the most subjective phase — you're reviewing LLM behavior, not code behavior:

 - In Claude or Cursor, use the prompt template and provide a real test plan file — does the LLM map the right fields to the right TestRail fields without extra guidance?
 - Try a deliberately ambiguous scenario description — does the prompt template give the LLM enough context to make a reasonable decision?
 - Try asking the LLM to do something the prompt isn't designed for — does it handle it gracefully or get confused?
 - There's no pass/fail here — you're tuning instruction quality, not debugging code. Expect iteration.
  -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

  Phase 8 — Polish & Publish README with setup instructions and env var documentation, Docker Hub or GHCR image publish, MCP client config examples (Claude Desktop, Cursor, VS Code), and any final error handling edge cases. Make it something anyone can pick up and use in under 10 minutes.
  
  Phase 8 — Polish & Publish The "stranger test" — pretend you've never seen this project:

 - Pull the Docker image fresh (don't use your locally-built one) and follow only the README instructions → can you get it running in under 10 minutes?
 - Every env var in the README should be required for the server to start — try omitting one and see if the error message tells you which one is missing
 - Paste the MCP config block from the README directly into Claude Desktop/Cursor config → does it connect on the first try?
 - Check that no credentials, API keys, or internal URLs appear anywhere in the image or README examples
