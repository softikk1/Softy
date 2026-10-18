import random
from typing import Any

from config import prompt, smiles, bot_name
from tools.get_dialog import get_dialogs
from tools.get_messages_chat_by_id import get_messages_chat_by_id
from tools.send_message_by_chat_id import send_message_by_chat_id


async def get_tools(event, response, tg_client, llm_client, cache):
    if response.message.tool_calls:
        for call in response.message.tool_calls:
            result: Any = None
            args = dict(call.function.arguments)
            del args['tg_client']
            if call.function.name == 'get_dialogs':
                result = await get_dialogs(tg_client, **args)
            elif call.function.name == 'send_message_by_chat_id':
                await send_message_by_chat_id(tg_client, **args)
            elif call.function.name == 'get_messages_chat_by_id':
                result = await get_messages_chat_by_id(tg_client, **args)
            cache.new_message({'role': 'tool', 'tool_name': call.function.name, 'content': str(result)})
        final = await llm_client.chat(
            model='gemma4:cloud',
            messages=[{'role': 'system', 'content': prompt}, *cache.get_messages()],
            tools=[get_dialogs, send_message_by_chat_id, get_messages_chat_by_id],
            stream=False)
        cache.new_message(final.message)
        if final.message.content:
            await event.reply(f'`{random.choice(smiles)} {bot_name}`\n' + final.message.content)
