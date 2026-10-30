# codbot

Answers questions about a Markdown knowledge base using Claude. Currently loaded with a
**Call of Duty: Modern Warfare 4 (2026)** knowledge base covering Multiplayer and DMZ (see [`knowledge/README.md`](knowledge/README.md)).

You can ask from the terminal or from Discord.

## How it works

- Every `.md` file under [`knowledge/`](knowledge/) is loaded and placed in Claude's system prompt
  (with prompt caching, so repeat questions are cheap). At ~65 KB this fits easily; no vector DB needed.
- [`codbot/answer.py`](codbot/answer.py) asks Claude (`claude-opus-5-5` by default) and returns the answer.
- [`codbot/discord_bot.py`](codbot/discord_bot.py) is a [discord.py](https://github.com/Rapptz/discord.py) bot:
  - `/ask question:<text>` slash command
  - `@codbot <question>` mentions
  - `/reload` re-reads `knowledge/` after you edit it

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env   # then fill in ANTHROPIC_API_KEY and DISCORD_TOKEN
```

### Try it from the terminal

```bash
uv run codbot "What's the best gun in DMZ right now?"
```

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

## Updating the knowledge base

Add or edit `.md` files anywhere under `knowledge/`, then run `/reload` in Discord or restart the bot.
Point `CODBOT_KNOWLEDGE_DIR` at another folder to use a different knowledge base.
