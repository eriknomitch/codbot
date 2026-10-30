# Common codbot tasks. Run `just` to list them.

set dotenv-load

port := env("CODBOT_PORT", "8000")

# List recipes
default:
    @just --list

# Install uv, just and the Python dependencies
setup:
    ./scripts/setup.sh

# Ask a question from the terminal, in a new conversation
[positional-arguments]
ask +question:
    uv run codbot "$@"

# Chat back and forth in the terminal (`just chat -c` continues the last conversation)
[positional-arguments]
chat *args:
    uv run codbot "$@"

# Refresh knowledge base files from the web (all of them if none given), then review with `git diff`
[positional-arguments]
update *paths:
    uv run codbot-update "$@"

# Start the web server (http://localhost:8000 by default)
web:
    uv run codbot-web

# Re-read knowledge/ on a running web server
reload:
    curl -fsS -X POST "http://localhost:{{port}}/reload"

# Start the Discord bot
discord:
    uv run codbot-discord

# Update uv.lock after changing dependencies in pyproject.toml
lock:
    uv lock
