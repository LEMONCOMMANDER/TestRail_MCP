"""
Parsers for converting file content into structured scenario objects
ready for import into TestRail.

Supported formats:
  gherkin   — Feature/Scenario/Given/When/Then blocks
  markdown  — ## or ### headings as titles, body as BDD content
  numbered  — numbered list items as titles (no step content)
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ParsedScenario:
    """A single test scenario parsed from a file."""
    title: str
    bdd_content: str | None = None  # Given/When/Then block
    description: str | None = None  # Free-text description if no BDD steps


def parse(content: str, fmt: str) -> list[ParsedScenario]:
    """
    Parse file content into a list of ParsedScenario objects.

    fmt must be one of: "gherkin", "markdown", "numbered"
    Raises ValueError for unsupported formats.
    """
    fmt = fmt.lower().strip()
    if fmt == "gherkin":
        return _parse_gherkin(content)
    elif fmt == "markdown":
        return _parse_markdown(content)
    elif fmt == "numbered":
        return _parse_numbered(content)
    else:
        raise ValueError(
            f"Unsupported format '{fmt}'. "
            "Supported formats: gherkin, markdown, numbered"
        )


# ── Gherkin ───────────────────────────────────────────────────────────────────

def _parse_gherkin(content: str) -> list[ParsedScenario]:
    """
    Parse Gherkin content into scenarios.

    Splits on 'Scenario:' and 'Scenario Outline:' keywords.
    Each scenario's name becomes the title; the Given/When/Then
    block becomes the BDD content.

    Example input:
        Feature: User Authentication

        Scenario: User logs in with valid credentials
            Given the user is on the login page
            When they enter valid credentials
            Then they should be redirected to the dashboard

        Scenario: User cannot log in with invalid password
            Given the user is on the login page
            When they enter an invalid password
            Then they should see an error message
    """
    scenarios: list[ParsedScenario] = []
    lines = content.splitlines()

    current_title: str | None = None
    current_steps: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Detect scenario boundary
        if stripped.lower().startswith("scenario outline:"):
            if current_title:
                scenarios.append(_build_gherkin_scenario(current_title, current_steps))
            current_title = stripped[len("scenario outline:"):].strip()
            current_steps = []

        elif stripped.lower().startswith("scenario:"):
            if current_title:
                scenarios.append(_build_gherkin_scenario(current_title, current_steps))
            current_title = stripped[len("scenario:"):].strip()
            current_steps = []

        # Collect steps (Given / When / Then / And / But)
        elif current_title and stripped.lower().startswith(
            ("given ", "when ", "then ", "and ", "but ", "* ")
        ):
            current_steps.append(stripped)

        # Skip Feature:, Background:, blank lines, comments
        # (anything else while we have a current scenario — ignore)

    # Flush last scenario
    if current_title:
        scenarios.append(_build_gherkin_scenario(current_title, current_steps))

    return scenarios


def _build_gherkin_scenario(title: str, steps: list[str]) -> ParsedScenario:
    bdd = "\n".join(steps) if steps else None
    return ParsedScenario(title=title, bdd_content=bdd)


# ── Markdown ──────────────────────────────────────────────────────────────────

def _parse_markdown(content: str) -> list[ParsedScenario]:
    """
    Parse Markdown content into scenarios.

    Uses ## or ### headings as scenario titles. The content under
    each heading (until the next heading) is treated as BDD steps
    if it contains Given/When/Then lines, or as a description otherwise.

    Example input:
        ## User logs in with valid credentials
        Given the user is on the login page
        When they enter valid credentials
        Then they should be redirected to the dashboard

        ## User cannot log in with invalid password
        Given the user is on the login page
        When they enter an invalid password
        Then they should see an error message
    """
    scenarios: list[ParsedScenario] = []
    lines = content.splitlines()

    current_title: str | None = None
    current_body: list[str] = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("## ") or stripped.startswith("### "):
            if current_title:
                scenarios.append(_build_markdown_scenario(current_title, current_body))
            # Strip leading #s and whitespace
            current_title = stripped.lstrip("#").strip()
            current_body = []
        elif current_title and stripped:
            current_body.append(stripped)

    if current_title:
        scenarios.append(_build_markdown_scenario(current_title, current_body))

    return scenarios


def _build_markdown_scenario(title: str, body_lines: list[str]) -> ParsedScenario:
    if not body_lines:
        return ParsedScenario(title=title)

    body = "\n".join(body_lines)
    # If any line looks like a BDD step, treat the whole block as BDD content
    bdd_keywords = ("given ", "when ", "then ", "and ", "but ")
    has_bdd = any(line.lower().startswith(bdd_keywords) for line in body_lines)

    if has_bdd:
        return ParsedScenario(title=title, bdd_content=body)
    else:
        return ParsedScenario(title=title, description=body)


# ── Numbered list ─────────────────────────────────────────────────────────────

def _parse_numbered(content: str) -> list[ParsedScenario]:
    """
    Parse a numbered list into scenarios (titles only, no step content).

    Example input:
        1. User can log in with valid credentials
        2. User cannot log in with invalid password
        3. User is locked out after 5 failed attempts
    """
    import re
    scenarios: list[ParsedScenario] = []

    for line in content.splitlines():
        stripped = line.strip()
        # Match lines starting with a number followed by . or )
        match = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if match:
            scenarios.append(ParsedScenario(title=match.group(1).strip()))

    return scenarios
