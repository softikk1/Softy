import asyncio
from typing import Any
from zoneinfo import ZoneInfo

from ollama import AsyncClient
from telethon import TelegramClient, events
from telethon.tl.functions.contacts import BlockRequest
from telethon.tl.functions.messages import ReportSpamRequest

from config import prompt, users, tg_api_key, tg_api_hash, llm_api_key, meridian_intro, prefix
from database import init_db, get_spammers_list_id, delete_spammer as delete_spammer_db, \
    add_or_refresh_spam_user, get_spam_level_user
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

            if max_streak >= 5:
                await add_or_refresh_spam_user(event.message.sender_id)
                spam_level = await get_spam_level_user(event.message.sender_id)
                _tg_client: TelegramClient = tg_client
                sender = await event.get_input_sender()
                match spam_level:
                    case 1:
                        await event.reply(
                            'Вы были занесены в список спамеров, если ваши действия продолжатся, придется принять меры.')
                    case 2:
                        await event.reply(
                            'Вы продолжаете спамить. Это последнее предупреждение, дальше последуют жалоба и блокировка.')
                    case 3:
                        await event.reply(
                            'Вы проигнорировали предупреждения. Я отправляю жалобу на спам в Telegram.')
                        await _tg_client(ReportSpamRequest(peer=sender))
                    case level if level >= 4:
                        await event.reply(
                            'Спам продолжается. Вы заблокированы.')
                        await _tg_client(ReportSpamRequest(peer=sender))
                        await _tg_client(BlockRequest(id=sender))
                await cache.clear_spam_messages(event.message.sender_id)

        @tg_client.on(events.NewMessage(pattern=f'{prefix}get_spammers', from_users=users))
        async def get_spammers(event):
            spammers = ', '.join([str(f'`{spammers.user_id}` - spam level: **{spammers.spam_level}**') for spammers in
                                  await get_spammers_list_id()])
            await event.reply(meridian_intro + f'В черном списке:\n{spammers}.')

        @tg_client.on(events.NewMessage(pattern=f'{prefix}delete_spammer', from_users=users))
        async def delete_spammer(event):
            user_id = int(event.raw_text.split()[-1])
            await delete_spammer_db(user_id)
            await event.reply(f'Пользователь `{user_id}` успешно удален.')

        @tg_client.on(events.NewMessage(from_users=users))
        async def chat(event):
            try:
                chat_messages = [
                    f'Datetime UTC+3 (МСК) {msg.date.astimezone(ZoneInfo('Europe/Moscow'))} - {getattr(await msg.get_sender(), 'username')} ({msg.sender_id}): {msg.text}'
                    for msg
                    in await tg_client.get_messages(event.chat_id, limit=20)]

                new_message: str = event.message.text
                await cache.new_message(
                    {'role': 'user', 'content': new_message} if event.message.photo is None else {'role': 'user',
                                                                                                  'content': new_message,
                                                                                                  'images': [
                                                                                                      await event.message.download_media(
                                                                                                          file="./images/")]})

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
ЭТО ПЕРВИЧНОЕ НА ЧТО ТЕБЕ НУЖНО СЕЙЧАС ОТВЕТИТЬ. САМОЕ ГЛАВНОЕ!!!
{reply_message_text}
''' if reply_message_text else '') + f'''

=== ЖЁСТКИЕ ПРАВИЛА ===
1. Ты — Меридиана. Отвечай коротко, живо, с характером.
2. Если пользователь пишет "мирида", "ответь", "напиши", "скажи", "отправь" и т.п. — это КОМАНДА, а не вопрос.
   - Не переспрашивай "а что именно ответить?".
   - Возьми контекст из истории выше.
   - Сразу придумай короткий естественный ответ и вызови tool send_message_by_chat_id.
3. Не задавай уточняющих вопросов, если в контексте уже есть достаточно информации.
4. Приоритет №1 — контекст чата. Не выдумывай то, чего там нет.
5. Если нужно больше истории — используй get_messages_chat_by_id. Не проси пользователя объяснить то, что уже написано.
6. Учитывай время сообщений в диалоге. Время всегда в 24-часовой системе и по часовому поясу UTC+3 (МСК).
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
