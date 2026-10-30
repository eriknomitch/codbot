"""Answer questions about the knowledge base via OpenRouter, falling back to web search."""

import os
from collections.abc import Sequence

from openai import AsyncOpenAI

from codbot.kb import load_documents

# An OpenRouter model's canonical_slug, as listed by https://openrouter.ai/api/v1/models.
DEFAULT_MODEL = "anthropic/claude-opus-5.5-20260921"

# OpenRouter's server-side web search tool: the model decides when (and how often) to search, and OpenRouter runs it.
# The default "auto" engine uses the provider's native search where it has one, and Exa otherwise.
# https://openrouter.ai/docs/guides/features/server-tools/web-search
WEB_SEARCH_TOOL = {"type": "openrouter:web_search", "parameters": {"max_results": 5}}
# Cap on server-tool steps (searches) per request, so one question can't run up the bill.
MAX_SEARCHES = 3
# How many earlier messages of a conversation to send along with a new question, so long chats stay affordable.
MAX_HISTORY_MESSAGES = 40

INSTRUCTIONS = """You answer questions using the knowledge base below.
Base your answers on the documents, and cite the document path(s) you relied on when useful.
If the knowledge base marks a fact as unofficial, reported, or fast-changing (like meta or tier lists), pass that caveat on.
Keep answers concise: they are often shown in Discord.
Questions may follow on from earlier messages in the conversation; read them in that context."""

SEARCH_INSTRUCTIONS = """If the documents don't cover the question, or it asks about something newer than they do,
use web search. Say plainly which parts of your answer come from the web rather than the knowledge base, and link the
pages you used. Don't search when the knowledge base already answers the question."""

NO_SEARCH_INSTRUCTIONS = "If the documents don't cover the question, say so plainly rather than guessing."


def web_search_enabled() -> bool:
    return os.environ.get("CODBOT_WEB_SEARCH", "1").lower() not in ("0", "false", "no", "off")


class Answerer:
    def __init__(self) -> None:
        # OpenRouter speaks the OpenAI Chat Completions API.
        self.client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPEN_ROUTER_API_KEY"])
        self.model = os.environ.get("OPEN_ROUTER_MODEL") or DEFAULT_MODEL
        self.web_search = web_search_enabled()
        self.reload()

    def reload(self) -> None:
        """Re-read the knowledge base from disk."""
        extra = SEARCH_INSTRUCTIONS if self.web_search else NO_SEARCH_INSTRUCTIONS
        self.system = {
            "role": "system",
            "content": [
                {"type": "text", "text": f"{INSTRUCTIONS}\n{extra}"},
                # Large, stable block: cache it so repeat questions are cheap and fast. Anthropic models need this
                # breakpoint; OpenRouter maps it for other providers that cache explicitly, and others cache automatically.
                {
                    "type": "text",
                    "text": f"<knowledge_base>\n{load_documents()}\n</knowledge_base>",
                    "cache_control": {"type": "ephemeral"},
                },
            ],
        }

    async def complete(self, messages: list[dict], max_searches: int = 0) -> str:
        """Run one chat completion, allowing up to max_searches web searches, and return the reply text."""
        # OpenRouter-only fields: think at medium effort, and leave the reasoning out of the response.
        extra_body: dict = {"reasoning": {"effort": "medium", "exclude": True}}
        kwargs = {}
        if max_searches:
            kwargs["tools"] = [WEB_SEARCH_TOOL]
            extra_body["max_tool_calls"] = max_searches
        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=16000,
            messages=messages,
            extra_body=extra_body,
            **kwargs,
        )

        choice = response.choices[0]
        if choice.finish_reason == "content_filter" or choice.message.refusal:
            return "Sorry, I can't help with that one."
        return (choice.message.content or "").strip()

    async def ask(self, question: str, history: Sequence[dict] = ()) -> str:
        """Answer a question, following on from history: earlier {"role", "content"} messages, oldest first."""
        earlier = [{"role": m["role"], "content": m["content"]} for m in history[-MAX_HISTORY_MESSAGES:]]
        # Trimming can cut a question from its answer; the conversation should resume on a question.
        while earlier and earlier[0]["role"] != "user":
            earlier.pop(0)
        messages = [self.system, *earlier, {"role": "user", "content": question}]
        searches = MAX_SEARCHES if self.web_search else 0
        return await self.complete(messages, max_searches=searches)
