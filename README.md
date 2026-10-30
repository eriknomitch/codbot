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
- When the knowledge base doesn't cover a question, or the question is about something newer, the model can search the web
  with OpenRouter's [web search server tool](https://openrouter.ai/docs/guides/features/server-tools/web-search)
  (up to 3 searches per question). Answers say which parts came from the web and link their sources.
  The default `auto` engine uses the model's native search where it has one (it does for Anthropic, OpenAI and Google models)
  and Exa otherwise; searches cost a little on top of tokens. Set `CODBOT_WEB_SEARCH=0` to turn this off.
- Conversations are saved, so you can follow up: each new question is sent along with the conversation so far
  (the last 40 messages). [`codbot/history.py`](codbot/history.py) keeps them in a SQLite database at
  `data/history.sqlite3` (set `CODBOT_HISTORY_DB` to move it), and [`codbot/chat.py`](codbot/chat.py) ties it to the model.
- [`codbot/web/`](codbot/web/) is a small [aiohttp](https://docs.aiohttp.org) server: a chat page at `/` with your saved
  chats in a sidebar, and a JSON API:
  - `POST /ask` with `{"question": "...", "conversation_id": "..."}` returns `{"answer": "...", "conversation_id": "..."}`.
    Leave out `conversation_id` to start a new conversation.
  - `GET /conversations` lists conversations, newest first; `GET /conversations/<id>` returns one with its messages;
    `DELETE /conversations/<id>` deletes one.
  - `POST /reload` re-reads `knowledge/`.
- [`codbot/discord_bot.py`](codbot/discord_bot.py) is a [discord.py](https://github.com/Rapptz/discord.py) bot:
  - `/ask question:<text>` slash command
  - `@codbot <question>` mentions
  - reply to any of the bot's answers (leaving the reply's @mention on) to follow up in the same conversation
  - `/reload` re-reads `knowledge/` after you edit it

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
./scripts/setup.sh     # installs uv and just if needed, then dependencies
cp .env.example .env   # then fill in OPEN_ROUTER_API_KEY and DISCORD_TOKEN
```

Common tasks live in the [`justfile`](justfile); run `just` to list them
(`just web`, `just ask "..."`, `just chat`, `just discord`, `just reload`, `just lock`, `just setup`).

### Try it from the terminal

```bash
uv run codbot "What's the best gun in DMZ right now?"
```

Every question starts a saved conversation. Follow up on the most recent one with `-c`:

```bash
uv run codbot -c "What attachments should I run on it?"
```

Run `codbot` with no question to chat back and forth (Ctrl-D to quit). Other options:

| Command | What it does |
| --- | --- |
| `codbot` | Chat interactively in a new conversation |
| `codbot -c ["follow-up"]` | Continue the most recent conversation (interactively, if no question) |
| `codbot -r ID ["follow-up"]` | Continue conversation `ID` |
| `codbot --list` | List saved conversations |
| `codbot --show ID` | Print a conversation |
| `codbot --delete ID` | Delete a conversation |

### Ask from the browser

```bash
uv run codbot-web
```

Then open <http://localhost:8000>. It listens on `127.0.0.1:8000` by default; set `CODBOT_HOST` / `CODBOT_PORT` to change that.
There's no login, so anyone who can reach the server can spend your OpenRouter credits and read, continue or delete
every saved chat: keep it on localhost or put it behind something that authenticates before exposing it.

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

To refresh files from the web, run:

```bash
uv run codbot-update season-1.md multiplayer/06-meta-tier-list.md
```

(or `just update ...`). With no arguments it goes through every file, which takes a while and costs more.
For each file the model searches for anything out of date or missing, then rewrites the file in place, keeping its structure
and linking a source for each change. Review the changes with `git diff` before you commit them.
Point `CODBOT_KNOWLEDGE_DIR` at another folder to use a different knowledge base.
