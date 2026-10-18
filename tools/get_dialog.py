async def get_dialogs(tg_client, only_pinned: bool = False, limit: int = 20) -> list[str]:
    """
    Получить список чатов владельца Telegram-аккаунта (того, кто пишет боту).
    Используй, когда спрашивают про чаты, диалоги, закреплённых людей
    или о том, с кем общался владелец. Полную переписку не отдаёт
    и признак закрепа.
    :param tg_client:
    :param only_pinned:
    :param limit:
    :return:
    """
    dialogs = []

    async for d in tg_client.iter_dialogs(limit=limit):
        if only_pinned and not d.pinned:
            continue

        entity = d.entity

        if d.is_user:
            info = (f"Тип: Пользователь\n"
                    f"Имя: {entity.first_name or ''} {entity.last_name or ''}\n"
                    f"Юзернейм: @{entity.username if entity.username else 'нет'}\n"
                    f"ID: {entity.id}\n"
                    f"Телефон: {entity.phone or 'скрыт'}\n"
                    f"Бот: {'Да' if entity.bot else 'Нет'}\n"
                    f"Premium: {'Да' if getattr(entity, 'premium', False) else 'Нет'}\n"
                    f"Непрочитанных: {d.unread_count}")

        elif d.is_group:
            info = (f"Тип: Группа\n"
                    f"Название: {entity.title}\n"
                    f"ID: {entity.id}\n"
                    f"Юзернейм: @{getattr(entity, 'username', None) or 'нет'}\n"
                    f"Непрочитанных: {d.unread_count}")

        elif d.is_channel:
            info = (f"Тип: Канал\n"
                    f"Название: {entity.title}\n"
                    f"ID: {entity.id}\n"
                    f"Юзернейм: @{entity.username if entity.username else 'нет'}\n"
                    f"Непрочитанных: {d.unread_count}")

        else:
            info = f"Тип: Неизвестно\nНазвание: {d.name}\nID: {d.id}"

        dialogs.append(info)

    return dialogs
