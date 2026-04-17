FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first so Docker can cache the install layer
# uv.lock is optional — if present it pins exact versions; if not, uv resolves fresh
COPY pyproject.toml uv.lock* ./

# Install production dependencies only
RUN uv sync --no-dev

# Copy source after dependencies so code changes don't bust the install cache
COPY src/ src/

EXPOSE 8000

# TRANSPORT defaults to "http" inside the container.
# PORT is read from the environment by the server (default: 8000).
CMD ["uv", "run", "python", "-m", "testrail_mcp"]
