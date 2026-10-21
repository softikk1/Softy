from config import bot_name


async def is_chat_bot(event, new_message) -> bool:
    reply_message_text = ''
    reply_message = await event.get_reply_message()
    if reply_message:
        reply_message_text = reply_message.raw_text
    # is_meridian = False
    # if bot_name not in reply_message_text:
    #     response_is_meridian = ollama.chat(
    #         model='gemma4:e2b',
    #         messages=[{'role': 'system', 'content': '''
    #                     Ты ИИ, которая просто пишет "да" или "нет" и все.
    #                     Если в n-ном сообщение есть обращение к Меридиане.
    #                     Даже если используются сокращения по типу:
    #                     "Ми", "Мерида", "Мандаринка", "Меридинка" и т.д,
    #                     то ты отвечаешь "да", если нет - "нет"
    #                     '''}, {'role': 'user', 'content': new_message}], think=False,
    #         keep_alive=-1,
    #         options={
    #             'temperature': 0,
    #             'num_predict': 3,
    #             'num_ctx': 512
    #         },
    #     )
    #     is_meridian = 'да' in response_is_meridian.message.content.lower()
    # return bot_name in reply_message_text or is_meridian
    return bot_name in reply_message_text or 'мирида' in new_message.lower()
