"""Web front end: a single page that posts questions to `/ask`."""

import logging
import os
from pathlib import Path

from aiohttp import web
from dotenv import load_dotenv

from codbot.answer import Answerer

log = logging.getLogger("codbot")
INDEX = Path(__file__).resolve().parent / "index.html"
MAX_QUESTION = 2000


async def index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(INDEX)


async def ask(request: web.Request) -> web.Response:
    try:
        question = str((await request.json()).get("question", "")).strip()
    except (ValueError, AttributeError):
        raise web.HTTPBadRequest(text="Expected a JSON body like {\"question\": \"...\"}")
    if not question:
        raise web.HTTPBadRequest(text="Ask me something about the knowledge base!")
    if len(question) > MAX_QUESTION:
        raise web.HTTPBadRequest(text=f"Keep questions under {MAX_QUESTION} characters.")
    try:
        answer = await request.app["answerer"].ask(question)
    except Exception:
        log.exception("Answering failed")
        raise web.HTTPBadGateway(text="The model call failed. Check the server logs.")
    return web.json_response({"answer": answer})


async def reload(request: web.Request) -> web.Response:
    request.app["answerer"].reload()
    return web.json_response({"ok": True})


def make_app() -> web.Application:
    app = web.Application()
    app["answerer"] = Answerer()
    app.router.add_get("/", index)
    app.router.add_post("/ask", ask)
    app.router.add_post("/reload", reload)
    return app


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    # Localhost by default: anyone who can reach the server spends your OpenRouter credits.
    host = os.environ.get("CODBOT_HOST", "127.0.0.1")
    port = int(os.environ.get("CODBOT_PORT", "8000"))
    web.run_app(make_app(), host=host, port=port)


if __name__ == "__main__":
    main()
