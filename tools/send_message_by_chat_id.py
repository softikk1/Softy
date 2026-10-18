async def send_message_by_chat_id(tg_client, chat_id: int, message: str):
    """Написать пользователю, используя chat_id: int и message: str
    Используй, когда пользователь просит написать кому-то,
    чтобы написать кому-то, используй get_dialogs
    :param tg_client:
    :param chat_id:
    :param message:
    :return:
    """
    await tg_client.send_message(chat_id, message=message)