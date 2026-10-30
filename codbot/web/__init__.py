"""Web front end: a single chat page that posts questions to `/ask` and browses saved conversations."""

import logging
import os
from pathlib import Path

from aiohttp import web
from dotenv import load_dotenv

from codbot.chat import Chat

log = logging.getLogger("codbot")
INDEX = Path(__file__).resolve().parent / "index.html"
MAX_QUESTION = 2000


async def index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(INDEX)


async def ask(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        question = str(body.get("question", "")).strip()
        conversation_id = str(body.get("conversation_id") or "") or None
    except (ValueError, AttributeError):
        raise web.HTTPBadRequest(text="Expected a JSON body like {\"question\": \"...\", \"conversation_id\": \"...\"}")
    if not question:
        raise web.HTTPBadRequest(text="Ask me something about the knowledge base!")
    if len(question) > MAX_QUESTION:
        raise web.HTTPBadRequest(text=f"Keep questions under {MAX_QUESTION} characters.")
    try:
        conversation_id, answer = await request.app["chat"].send(question, conversation_id)
    except KeyError:
        raise web.HTTPNotFound(text="That conversation no longer exists. Start a new chat.")
    except Exception:
        log.exception("Answering failed")
        raise web.HTTPBadGateway(text="The model call failed. Check the server logs.")
    return web.json_response({"answer": answer, "conversation_id": conversation_id})


async def list_conversations(request: web.Request) -> web.Response:
    return web.json_response(request.app["chat"].history.list())


async def get_conversation(request: web.Request) -> web.Response:
    conversation = request.app["chat"].history.get(request.match_info["id"])
    if not conversation:
        raise web.HTTPNotFound(text="No such conversation.")
    return web.json_response(conversation)


async def delete_conversation(request: web.Request) -> web.Response:
    if not request.app["chat"].history.delete(request.match_info["id"]):
        raise web.HTTPNotFound(text="No such conversation.")
    return web.json_response({"ok": True})


async def reload(request: web.Request) -> web.Response:
    request.app["chat"].answerer.reload()
    return web.json_response({"ok": True})


def make_app() -> web.Application:
    app = web.Application()
    app["chat"] = Chat()
    app.router.add_get("/", index)
    app.router.add_post("/ask", ask)
    app.router.add_get("/conversations", list_conversations)
    app.router.add_get("/conversations/{id}", get_conversation)
    app.router.add_delete("/conversations/{id}", delete_conversation)
    app.router.add_post("/reload", reload)
    return app


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    # Localhost by default: anyone who can reach the server spends your OpenRouter credits and can read saved chats.
    host = os.environ.get("CODBOT_HOST", "127.0.0.1")
    port = int(os.environ.get("CODBOT_PORT", "8000"))
    web.run_app(make_app(), host=host, port=port)


if __name__ == "__main__":
    main()
