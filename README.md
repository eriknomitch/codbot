# codbot

Answers questions about a Markdown knowledge base using an LLM via [OpenRouter](https://openrouter.ai). Currently loaded with a
**Call of Duty: Modern Warfare 4 (2026)** knowledge base covering Multiplayer and DMZ (see [`knowledge/README.md`](knowledge/README.md)).

You can ask from the terminal, a web page, or Discord.

## How it works

- Every `.md` file under [`knowledge/`](knowledge/) is loaded and placed in the model's system prompt
  (with prompt caching, so repeat questions are cheap). At ~65 KB this fits easily; no vector DB needed.
- [`codbot/answer.py`](codbot/answer.py) asks the model set by `OPEN_ROUTER_MODEL` and returns the answer.
  Use the model's `canonical_slug` from [OpenRouter's model list](https://openrouter.ai/api/v1/models);
  the default is `anthropic/claude-opus-5.5-20260921`.
- [`codbot/web/`](codbot/web/) is a small [aiohttp](https://docs.aiohttp.org) server: a chat-style page at `/`,
  `POST /ask` with `{"question": "..."}` returning `{"answer": "..."}`, and `POST /reload` to re-read `knowledge/`.
- [`codbot/discord_bot.py`](codbot/discord_bot.py) is a [discord.py](https://github.com/Rapptz/discord.py) bot:
  - `/ask question:<text>` slash command
  - `@codbot <question>` mentions
  - `/reload` re-reads `knowledge/` after you edit it

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
./scripts/setup.sh     # installs uv and just if needed, then dependencies
cp .env.example .env   # then fill in OPEN_ROUTER_API_KEY and DISCORD_TOKEN
```

Common tasks live in the [`justfile`](justfile); run `just` to list them
(`just web`, `just ask "..."`, `just discord`, `just reload`, `just lock`, `just setup`).

### Try it from the terminal

```bash
uv run codbot "What's the best gun in DMZ right now?"
```

### Ask from the browser

```bash
uv run codbot-web
```

Then open <http://localhost:8000>. It listens on `127.0.0.1:8000` by default; set `CODBOT_HOST` / `CODBOT_PORT` to change that.
There's no login, so anyone who can reach the server can spend your OpenRouter credits: keep it on localhost
or put it behind something that authenticates before exposing it.

### Create the Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and click **New Application**.
2. **Bot** tab: click **Reset Token**, then copy it into `DISCORD_TOKEN` in `.env`.
   No privileged intents are needed.
3. **OAuth2 → URL Generator**: tick the `bot` and `applications.commands` scopes, and the
   `Send Messages`, `Read Message History` and `Use Slash Commands` permissions. Open the URL to invite the bot to your server.
4. Optional: put your server ID in `DISCORD_GUILD_ID` so slash commands show up instantly (global sync can take up to an hour).
   Right-click the server name with Developer Mode on → **Copy Server ID**.

### Run the bot

```bash
uv run codbot-discord
```

## Claude Code cloud environment

In the environment's settings, set **Setup script** to:

```bash
#!/bin/bash
bash /home/user/codbot/scripts/setup.sh
```

Put `OPEN_ROUTER_API_KEY` (and optionally `OPEN_ROUTER_MODEL`, and `DISCORD_TOKEN` if you want to run the bot there) in the environment's variables.
The setup script itself can't read them, and doesn't need to.

## Updating the knowledge base

Add or edit `.md` files anywhere under `knowledge/`, then run `/reload` in Discord, `POST /reload` to the web server, or restart.
Point `CODBOT_KNOWLEDGE_DIR` at another folder to use a different knowledge base.
