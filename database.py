from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

engine = create_async_engine('sqlite+aiosqlite:///bot.db')
Session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Spammers(Base):
    __tablename__ = 'spam_users'
    user_id: Mapped[int] = mapped_column('id', primary_key=True)
    spam_level: Mapped[int] = mapped_column('spam_level')


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def add_spam_user(user_id: int, level: int = 1):
    async with Session() as s:
        s.add(Spammers(user_id=user_id, spam_level=level))
        await s.commit()


async def replace_spam_user(user_id: int, level: int):
    async with Session() as s:
        user = await s.scalar(select(Spammers).where(Spammers.user_id == user_id))
        user.spam_level = level
        await s.commit()


async def is_spam_user(user_id: int) -> bool:
    async with Session() as s:
        user = await s.scalar(select(Spammers).where(Spammers.user_id == user_id))
        return user is not None


async def get_spammers_list_id() -> list[int]:
    async with Session() as s:
        result = await s.scalars(select(Spammers.user_id))
        return result.all()


async def delete_spammer(user_id: int):
    async with Session() as s:
        user = await s.get(Spammers, user_id)
        if user is not None:
            await s.delete(user)
            await s.commit()
