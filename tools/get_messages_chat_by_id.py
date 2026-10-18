async def get_messages_chat_by_id(tg_client, chat_id: int, limit: int = 50):
    """
    Функция используется для получения сообщений из чата по id чата.
    Также можно указать количество последних сообщений чата.
    :param tg_client:
    :param chat_id:
    :param limit:
    :return:
    """
    return await tg_client.get_messages(chat_id, limit=limit)