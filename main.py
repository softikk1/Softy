import asyncio
from typing import Any

from ollama import AsyncClient
from telethon import TelegramClient

from chat.chat_events import chat_events
from config import tg_api_key, tg_api_hash, llm_api_key
from database.database import init_db


class MemoryCache:
    def __init__(self):
        self._messages: list[Any] = []
        self._spam_messages: list[Any] = []

    async def new_message(self, message):
        if len(self._messages) > 20:
            self._messages.remove(self._messages[0])
        self._messages.append(message)

    async def get_messages(self) -> list[Any]:
        return self._messages

    async def add_spam_messages(self, message):
        self._spam_messages.append(message)

    async def get_spam_messages(self) -> list[Any]:
        return self._spam_messages

    async def clear_spam_messages(self, user_id):
        self._spam_messages = [message for message in self._spam_messages if message.sender_id != user_id]


def startup():
    print('Hello, my name is Меридиана')


async def main():
    startup()
    await init_db()
    async with TelegramClient(session='client', api_id=tg_api_key, api_hash=tg_api_hash) as tg_client, \
            AsyncClient(host="https://ollama.com", headers={"Authorization": "Bearer " + llm_api_key}) as llm_client:
        cache = MemoryCache()

        await chat_events(tg_client, llm_client, cache)

        await tg_client.disconnected


if __name__ == '__main__':
    asyncio.run(main())
