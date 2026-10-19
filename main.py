import asyncio
from typing import Any

from ollama import AsyncClient
from telethon import TelegramClient, events

from config import prompt, users, tg_api_key, tg_api_hash, llm_api_key, meridian_intro, prefix
from database import init_db, is_spam_user, add_spam_user, get_spammers_list_id, delete_spammer as delete_spammer_db
from get_tools import get_tools
from is_chat_bot import is_chat_bot
from tools.get_dialog import get_dialogs
from tools.get_messages_chat_by_id import get_messages_chat_by_id
from tools.send_message_by_chat_id import send_message_by_chat_id


class MemoryCache:
    def __init__(self):
        self._messages: list[Any] = []
        self._spam_messages: list[Any] = []

    def new_message(self, message):
        self._messages.append(message)

    def get_messages(self) -> list[Any]:
        return self._messages

    def add_spam_messages(self, message):
        self._spam_messages.append(message)

    def get_spam_messages(self) -> list[Any]:
        return self._spam_messages


def startup():
    print('Hello, my name is Меридиана')


async def main():
    startup()
    await init_db()
    async with TelegramClient(session='client', api_id=tg_api_key, api_hash=tg_api_hash) as tg_client, \
            AsyncClient(host="https://ollama.com", headers={"Authorization": "Bearer " + llm_api_key}) as llm_client:
        cache = MemoryCache()

        @tg_client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
        async def antispam(event):
            if await is_spam_user(event.message.sender_id):
                await event.reply('Вы в бане за спам.')
                await event.message.delete()

            users_ids = [int(msg.sender_id) for msg in cache.get_spam_messages()]
            if event.message.sender_id in users_ids:
                if event.message.text == cache.get_spam_messages()[users_ids.index(event.message.sender_id)].text:
                    cache.add_spam_messages(event.message)
                else:
                    cache.get_spam_messages()[users_ids.index(event.message.sender_id)] = event.message
            else:
                cache.add_spam_messages(event.message)
            if users_ids.count(event.message.sender_id) > 5 and not await is_spam_user(event.message.sender_id):
                await add_spam_user(event.message.sender_id)

        @tg_client.on(events.NewMessage(pattern=f'{prefix}get_spammers', from_users=users))
        async def get_spammers(event):
            spammers = ', '.join([str(f'`{_id}`') for _id in await get_spammers_list_id()])
            await event.reply(meridian_intro + f'В черном списке:\n{spammers}.')

        @tg_client.on(events.NewMessage(pattern=f'{prefix}delete_spammer', from_users=users))
        async def delete_spammer(event):
            user_id = int(event.raw_text.split()[-1])
            await delete_spammer_db(user_id)
            await event.reply(f'Пользователь `{user_id}` успешно удален.')

        @tg_client.on(events.NewMessage(from_users=users))
        async def chat(event):
            chat_messages = await tg_client.get_messages(event.chat_id, limit=20)

            new_message: str = event.message.text
            cache.new_message({'role': 'user', 'content': new_message})

            if await is_chat_bot(event=event, new_message=new_message):
                response = await llm_client.chat(
                    model='gemma4:cloud',
                    messages=[
                        {'role': 'system', 'content': prompt + f'\nАктуальные сообщения данного чата: {chat_messages}'},
                        *cache.get_messages()],
                    tools=[get_dialogs, send_message_by_chat_id, get_messages_chat_by_id],
                    think=False,
                    stream=False)
                if response.message.content:
                    await event.reply(
                        meridian_intro + response.message.content)
                cache.new_message(response.message)
                await get_tools(event, response, tg_client, llm_client, cache)

        await tg_client.disconnected


if __name__ == '__main__':
    asyncio.run(main())
