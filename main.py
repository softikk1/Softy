import asyncio
from typing import Any

from ollama import AsyncClient
from telethon import TelegramClient, events

from config import prompt, users, tg_api_key, tg_api_hash, llm_api_key, meridian_intro, prefix
from database import init_db, is_spam_user, get_spammers_list_id, delete_spammer as delete_spammer_db, add_spam_user
from get_tools import get_tools
from is_chat_bot import is_chat_bot
from tools.get_dialog import get_dialogs
from tools.get_messages_chat_by_id import get_messages_chat_by_id
from tools.send_message_by_chat_id import send_message_by_chat_id


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

        @tg_client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
        async def antispam(event):
            if await is_spam_user(event.message.sender_id):
                await event.reply('Вы в бане за спам.')
                await event.message.delete()
                return
            await cache.add_spam_messages(event.message)
            messages = await cache.get_spam_messages()
            max_streak = 1
            last_text = ''
            for text in [msg.text for msg in messages]:
                if last_text == text:
                    max_streak += 1
                else:
                    max_streak = 1
                last_text = text

            if max_streak >= 5 and not await is_spam_user(event.message.sender_id):
                await add_spam_user(event.message.sender_id)
                await cache.clear_spam_messages(event.message.sender_id)

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
            try:
                chat_messages = [f'{getattr(await msg.get_sender(), 'username')} ({msg.sender_id}): {msg.text}' for msg
                                 in await tg_client.get_messages(event.chat_id, limit=20)]

                new_message: str = event.message.text
                await cache.new_message({'role': 'user', 'content': new_message})

                reply_message_text = ''
                reply_message = await event.get_reply_message()
                if reply_message:
                    reply_message_text = reply_message.raw_text

                if await is_chat_bot(event=event, new_message=new_message):
                    response = await llm_client.chat(
                        model='gemma4:cloud',
                        messages=[
                            {'role': 'system',
                             'content': prompt + f'''

=== КОНТЕКСТ ЧАТА (самое важное) ===
{chat_messages}

Сообщения, начинающиеся с "{meridian_intro}" — это твои предыдущие ответы. Используй их как образец стиля.

''' + (f'''
=== СООБЩЕНИЕ, НА КОТОРОЕ СЕЙЧАС ИДЁТ REPLY ===
{reply_message_text}
''' if reply_message_text else '') + '''

=== ЖЁСТКИЕ ПРАВИЛА ===
1. Ты — Меридиана. Отвечай коротко, живо, с характером.
2. Если пользователь пишет "ответь", "напиши", "скажи", "отправь" и т.п. — это КОМАНДА, а не вопрос.
   - Не переспрашивай "а что именно ответить?".
   - Возьми контекст из истории выше.
   - Сразу придумай короткий естественный ответ и вызови tool send_message_by_chat_id.
3. Не задавай уточняющих вопросов, если в контексте уже есть достаточно информации.
4. Приоритет №1 — контекст чата. Не выдумывай то, чего там нет.
5. Если нужно больше истории — используй get_messages_chat_by_id. Не проси пользователя объяснить то, что уже написано.
'''
                             },
                            *(await cache.get_messages())],
                        tools=[get_dialogs, send_message_by_chat_id, get_messages_chat_by_id],
                        think=False,
                        stream=False)
                    if response.message.content:
                        await event.reply(
                            meridian_intro + response.message.content)
                    await cache.new_message(response.message)
                    await get_tools(event, response, tg_client, llm_client, cache)
            except Exception as e:
                await event.reply(f'Ошибка: {e}')

        await tg_client.disconnected


if __name__ == '__main__':
    asyncio.run(main())
