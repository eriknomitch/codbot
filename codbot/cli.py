"""Ask the knowledge base from the terminal.

    codbot "your question"         ask in a new conversation
    codbot                         chat back and forth in a new conversation
    codbot -c ["follow-up"]        continue the most recent conversation
    codbot -r ID ["follow-up"]     continue conversation ID
    codbot --list                  list saved conversations
    codbot --show ID               print a saved conversation
    codbot --delete ID             delete a saved conversation
"""

import argparse
import asyncio
import sys

from dotenv import load_dotenv

from codbot.chat import Chat
from codbot.history import History

EXIT_WORDS = {"exit", "quit", ":q"}


def print_messages(messages: list[dict]) -> None:
    for message in messages:
        print(f"{'you' if message['role'] == 'user' else 'codbot'}> {message['content']}\n")


async def interactive(chat: Chat, conversation_id: str | None) -> None:
    if conversation_id:
        print_messages(chat.history.messages(conversation_id))
    print("Chatting with codbot. Ctrl-D or 'exit' to quit.\n", file=sys.stderr)
    while True:
        try:
            question = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(file=sys.stderr)
            break
        if question.lower() in EXIT_WORDS:
            break
        if not question:
            continue
        conversation_id, answer = await chat.send(question, conversation_id)
        print(f"\ncodbot> {answer}\n")
    if conversation_id:
        print(f"Saved as conversation {conversation_id}. Resume it with `codbot -r {conversation_id}`.", file=sys.stderr)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        prog="codbot", description="Ask the knowledge base. Conversations are saved so you can follow up."
    )
    parser.add_argument("question", nargs="*", help="what to ask; leave out to chat interactively")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-c", "--continue", dest="latest", action="store_true", help="continue the most recent conversation")
    group.add_argument("-r", "--resume", metavar="ID", help="continue conversation ID")
    group.add_argument("--list", action="store_true", help="list saved conversations")
    group.add_argument("--show", metavar="ID", help="print a saved conversation")
    group.add_argument("--delete", metavar="ID", help="delete a saved conversation")
    args = parser.parse_args()

    history = History()
    if args.list:
        for conversation in history.list():
            print(f"{conversation['id']}  {conversation['updated_at']}  {conversation['title']}")
        return
    if args.show:
        if not history.exists(args.show):
            sys.exit(f"No conversation {args.show}")
        print_messages(history.messages(args.show))
        return
    if args.delete:
        if not history.delete(args.delete):
            sys.exit(f"No conversation {args.delete}")
        return

    conversation_id = args.resume
    if args.latest:
        conversation_id = history.latest()
        if not conversation_id:
            sys.exit("No saved conversations yet.")
    if conversation_id and not history.exists(conversation_id):
        sys.exit(f"No conversation {conversation_id}")

    chat = Chat(history=history)
    if not args.question:
        asyncio.run(interactive(chat, conversation_id))
        return
    conversation_id, answer = asyncio.run(chat.send(" ".join(args.question), conversation_id))
    print(answer)
    print(f"\n(conversation {conversation_id}; follow up with `codbot -c \"...\"`)", file=sys.stderr)


if __name__ == "__main__":
    main()
