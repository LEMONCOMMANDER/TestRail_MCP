import sys
from pydantic import ValidationError


def main():
    try:
        from testrail_mcp.server import main as _main
        _main()
    except ValidationError as exc:
        # Map pydantic field names → environment variable names for readable errors.
        _ENV_VAR_NAMES = {
            "testrail_url": "TESTRAIL_URL",
            "testrail_email": "TESTRAIL_EMAIL",
            "testrail_api_key": "TESTRAIL_API_KEY",
        }
        missing = [
            _ENV_VAR_NAMES.get(e["loc"][0], str(e["loc"][0]).upper())
            for e in exc.errors()
            if e["type"] == "missing"
        ]
        if missing:
            print(
                "ERROR: The following required environment variables are not set:\n"
                + "".join(f"  - {v}\n" for v in missing)
                + "\nSet them in a .env file or pass them as environment variables.\n"
                "See README.md for setup instructions.",
                file=sys.stderr,
            )
        else:
            print(f"ERROR: Configuration is invalid:\n{exc}", file=sys.stderr)
        sys.exit(1)


main()

