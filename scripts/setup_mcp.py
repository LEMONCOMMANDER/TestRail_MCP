#!/usr/bin/env python3
"""
setup_mcp.py — TestRail MCP client configuration helper

Writes the correct MCP config file for your AI client. Credentials are NOT
written here — the server reads them from the .env file in the project root.

Usage:
    uv run python scripts/setup_mcp.py --ide vscode
    uv run python scripts/setup_mcp.py --ide cursor
    uv run python scripts/setup_mcp.py --ide jetbrains
    uv run python scripts/setup_mcp.py --ide claude

Run without arguments for an interactive prompt.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SUPPORTED_IDES = ["vscode", "cursor", "jetbrains", "claude"]

IDE_LABELS = {
    "vscode": "VS Code (GitHub Copilot)",
    "cursor": "Cursor",
    "jetbrains": "JetBrains (RubyMine / IntelliJ / PyCharm)",
    "claude": "Claude Desktop",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"  ✅  Written: {path}")


def _confirm(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    raw = input(f"{prompt} [{hint}]: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")


def _server_block() -> dict:
    """
    Stdio server block. Credentials are intentionally omitted — the server
    loads them from the .env file in the project root via pydantic-settings.
    """
    return {
        "command": "uv",
        "args": [
            "run",
            "--directory",
            str(PROJECT_ROOT),
            "python",
            "-m",
            "testrail_mcp",
        ],
        "env": {
            "TRANSPORT": "stdio",
        },
    }


def _safe_write(path: Path, data: dict) -> None:
    if path.exists() and not _confirm(f"\n{path} already exists. Overwrite?"):
        print("  Skipped.")
        return
    _write_json(path, data)


# ---------------------------------------------------------------------------
# Per-IDE writers
# ---------------------------------------------------------------------------

def configure_vscode() -> None:
    dest = PROJECT_ROOT / ".vscode" / "mcp.json"
    _safe_write(dest, {
        "servers": {
            "testrail": {
                "type": "stdio",
                **_server_block(),
            }
        }
    })
    print("  VS Code will auto-discover this when you open the project folder.")


def configure_cursor() -> None:
    dest = PROJECT_ROOT / ".cursor" / "mcp.json"
    _safe_write(dest, {"mcpServers": {"testrail": _server_block()}})
    print("  Cursor will auto-discover this when you open the project folder.")


def configure_jetbrains() -> None:
    dest = PROJECT_ROOT / ".idea" / "mcp.json"
    _safe_write(dest, {"mcpServers": {"testrail": _server_block()}})
    print(
        "  JetBrains AI Assistant will auto-discover this.\n"
        "  Requires: Settings → AI Assistant → Model Context Protocol → Enable."
    )


def configure_claude() -> None:
    system = platform.system()
    if system == "Darwin":
        config_dir = Path.home() / "Library" / "Application Support" / "Claude"
    elif system == "Windows":
        config_dir = Path(os.environ.get("APPDATA", "")) / "Claude"
    else:
        config_dir = Path.home() / ".config" / "Claude"

    dest = config_dir / "claude_desktop_config.json"

    # Merge into existing config rather than overwrite unrelated servers
    existing: dict = {}
    if dest.exists():
        try:
            existing = json.loads(dest.read_text())
        except json.JSONDecodeError:
            print(f"  Warning: {dest} exists but is not valid JSON — will overwrite.")
        else:
            print(f"\n  Existing config found at {dest}. The 'testrail' server entry will be added or updated.")

    existing.setdefault("mcpServers", {})["testrail"] = _server_block()
    _safe_write(dest, existing)
    print(
        "  Restart Claude Desktop for the change to take effect.\n"
        f"  Config location: {dest}"
    )


CONFIGURATORS = {
    "vscode": configure_vscode,
    "cursor": configure_cursor,
    "jetbrains": configure_jetbrains,
    "claude": configure_claude,
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _pick_ide_interactively() -> str:
    print("\nWhich AI client are you configuring?\n")
    for i, (key, label) in enumerate(IDE_LABELS.items(), 1):
        print(f"  {i}. {label}  [{key}]")
    print()
    while True:
        raw = input(f"Enter a number [1–{len(IDE_LABELS)}]: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(IDE_LABELS):
            return list(IDE_LABELS.keys())[int(raw) - 1]
        print(f"  Please enter a number between 1 and {len(IDE_LABELS)}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write the MCP config file for your AI client.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(
            f"  --ide {k:<12} {v}" for k, v in IDE_LABELS.items()
        ),
    )
    parser.add_argument(
        "--ide",
        choices=SUPPORTED_IDES,
        metavar="IDE",
        help=f"Target IDE: {', '.join(SUPPORTED_IDES)}",
    )
    args = parser.parse_args()

    print("╔══════════════════════════════════════════╗")
    print("║   TestRail MCP — Client Setup Script     ║")
    print("╚══════════════════════════════════════════╝")
    print(f"\n  Project root: {PROJECT_ROOT}")
    print("  Credentials : read from .env at runtime (not stored in config)\n")

    ide = args.ide or _pick_ide_interactively()

    print(f"\nConfiguring for: {IDE_LABELS[ide]}")
    CONFIGURATORS[ide]()

    print("\nDone! 🎉")
    print("Make sure your .env file is set up in the project root before starting the server.")
    print("See README.md for .env instructions.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted.")
        sys.exit(0)

