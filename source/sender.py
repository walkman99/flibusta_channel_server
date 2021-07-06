from asyncio import run, gather, PriorityQueue
from asyncio import TimeoutError as ATimeoutError

from alchemysession import AlchemySessionContainer

from io import BytesIO

import aiogram
from aiohttp import request, ClientSession, ClientTimeout
from telethon import TelegramClient, errors
import transliterate
import asyncpg

from dataclasses import dataclass, field
from typing import Any

from config import Config
from db import FlibustaChannelDB


class NoContent(Exception):
    pass


@dataclass(order=True)
class PrioritizedItem:
    priority: int
    item: Any=field(compare=False)


# remove chars that don't accept in Telegram Bot API
async def normalize(book: "Book", file_type: str) -> str:
    filename = '_'.join([a.short for a in book.authors]) + \
        '_-_' if book.authors else ''
    filename += book.title if book.title[-1] != ' ' else book.title[:-1]
    filename = transliterate.translit(filename, 'ru', reversed=True)

    for c in "(),….’!\"?»«':":
        filename = filename.replace(c, '')

    for c, r in (('—', '-'), ('/', '_'), ('№', 'N'), (' ', '_'), ('–', '-'),
                 ('á', 'a'), (' ', '_')):
        filename = filename.replace(c, r)

    right_part = f'.{str(book.id)}.{file_type}'

    return filename[:64 - len(right_part)] + right_part



class Author:
    def __init__(self, obj: dict):
        self.count = obj.get("count", None)

        if obj.get("result", None) is None:
            self.obj = obj
        else:
            self.obj = obj["result"]

    def __del__(self):
        del self.obj

    def __bool__(self):
        return self.count != 0

    @property
    def id(self):
        return self.obj["id"]

    @property
    def first_name(self):
        return self.obj["first_name"]

    @property
    def last_name(self):
        return self.obj["last_name"]

    @property
    def middle_name(self):
        return self.obj["middle_name"]

    @property
    def annotation_exists(self):
        return self.obj["annotation_exists"]

    @property
    def books(self):
        return [Book(x) for x in self.obj["books"]] \
            if self.obj.get("books", None) else []

    @property
    def normal_name(self) -> str:
        temp = ''
        if self.last_name:
            temp = self.last_name
        if self.first_name:
            if temp:
                temp += " "
            temp += self.first_name
        if self.middle_name:
            if temp:
                temp += " "
            temp += self.middle_name
        return temp

    @property
    def short(self) -> str:
        temp = ''
        if self.last_name:
            temp += self.last_name
        if self.first_name:
            if temp:
                temp += " "
            temp += self.first_name[0]
        if self.middle_name:
            if temp:
                temp += " "
            temp += self.middle_name[0]
        return temp


class Book:
    def __init__(self, obj: dict):
        self.obj = obj

    def __del__(self):
        del self.obj

    @property
    def id(self):
        return self.obj["id"]

    @property
    def title(self):
        return self.obj["title"]

    @property
    def lang(self):
        return self.obj["lang"]

    @property
    def file_type(self):
        return self.obj["file_type"]

    @property
    def annotation_exists(self):
        return self.obj["annotation_exists"]

    @property
    def authors(self):
        return [Author(a) for a in self.obj["authors"]] \
            if self.obj.get("authors", None) else None

    @property
    def caption(self) -> str:
        if not self.authors:
            return "📖 " + self.title

        result = "📖 " + self.title + '\n\n' + \
            '\n'.join(["👤 " + author.normal_name for author in self.authors])

        if len(result) <= 1024:
            return result

        i = len(self.authors)
        while len(result) > 1024:
            i -= 1
            result = "📖 " + self.title + '\n\n' + \
                '\n'.join(
                    ["👤 " + author.normal_name for author in self.authors[:i]]
                ) + "\n и т.д."
        return result

    @staticmethod
    async def get_by_id(book_id: int) -> "Book":
        async with request(
            "GET",
            f"{Config.FLIBUSTA_SERVER_HOST}/book/{book_id}"
        ) as response:
            if response.status == 204:
                raise NoContent
            return Book(await response.json())


class Sender:
    client: TelegramClient
    bot: aiogram.Bot
    tasks: PriorityQueue
    all_task_added: bool

    flibusta_channel_server_pool: asyncpg.pool.Pool

    def __init__(self):
        container = AlchemySessionContainer(
            f'postgresql://{Config.DB_USER}:'
            f'{Config.DB_PASSWORD}@{Config.DB_HOST}/{Config.DB_DATABASE}'
        )

        session = container.new_session(Config.SESSION)

        self.client = TelegramClient(
          session, Config.APP_ID, Config.API_HASH
        )

        self.bot = aiogram.Bot(token=Config.BOT_TOKEN)

    async def prepare(self):
        client = self.client

        await client.start()

        if not await client.is_user_authorized():
            await client.sign_in()
            try:
                await client.sign_in(code=input('Enter code: '))
            except errors.SessionPasswordNeededError:
                await client.sign_in(password=input("Enter password: "))

        self.channel_dialog = Config.CHANNEL_ID

        self.tasks = PriorityQueue(maxsize=10_000)

        self.all_task_added = False

        self.flibusta_server_pool = await asyncpg.create_pool(
            user=Config.FLIBUSTA_SERVER_DB_USER,
            password=Config.FLIBUSTA_SERVER_DB_PASSWORD,
            database=Config.FLIBUSTA_SERVER_DB_DATABASE,
            host=Config.FLIBUSTA_SERVER_DB_HOST
        )

        await FlibustaChannelDB.prepare(None)

    async def upload(
        self, book_id: int, file_type: str, retry: int = 0,
    ):
        if retry < 0:
            return

        async def create_retry_task():
            await self.tasks.put(
                PrioritizedItem(
                    0 if file_type == 'fb2' else 1,
                    self.upload(
                        book_id, file_type, retry - 1
                    )
                )
            )

        print(f"Download {book_id} {file_type}...")

        timeout = ClientTimeout(total=30 * 60)
        try:
            async with ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{Config.FLIBUSTA_SERVER_HOST}/book/download/"
                    f"{book_id}/{file_type}"
                ) as response:
                    if response.status != 200:
                        print(f"Download failed {book_id} {file_type}...")
                        return
                    content = await response.content.read()
        except ATimeoutError:
            await create_retry_task()
            print(f"Timeout {book_id} {file_type}!")
            return

        book_info: Book = await Book.get_by_id(book_id)
        data = BytesIO(content)
        data.name = await normalize(book_info, file_type.replace('+', '.'))

        print(f"Upload {book_id} {file_type}...")
        client = self.client

        book_msg = None

        if data.getbuffer().nbytes < 30 * 1_000_000:
            try:
                book_msg = await self.bot.send_document(
                    self.channel_dialog,
                    data,
                    caption=book_info.caption
                )

                await FlibustaChannelDB.set_message_id(
                    book_id,
                    file_type,
                    book_msg.message_id
                )
            except Exception:
                pass

        if book_msg is not None:
            return

        try:
            book_msg = await client.send_file(
                self.channel_dialog,
                file=data,
                caption=book_info.caption
            )

            await FlibustaChannelDB.set_message_id(
                book_id,
                file_type,
                book_msg.id
            )
        except (errors.FilePartsInvalidError, ValueError):
            await create_retry_task()

    async def tasks_add(self):
        book_rows = await self.flibusta_server_pool.fetch(
            "SELECT id, file_type FROM book ORDER BY id DESC;"
        )

        self.all_task_added = False

        for row in book_rows:
            book_id = row["id"]
            file_type = row["file_type"]

            if file_type != 'fb2':
                types = [file_type]
            else:
                types = ['fb2', 'fb2+zip', 'epub', 'mobi']

            for ttype in types:
                uploaded_row = await FlibustaChannelDB.get_message_id(
                    book_id, ttype
                )

                if not uploaded_row:
                    await self.tasks.put(
                        PrioritizedItem(
                            0 if ttype == 'fb2' else 1,
                            self.upload(book_id, ttype)
                        )
                    )

        self.all_task_added = True

    async def execute_tasks(self):
        while not self.all_task_added or not self.tasks.empty():
            task: PrioritizedItem = await self.tasks.get()

            try:
                await task.item
            except Exception as e:
                print(e)


async def main():
    sender = Sender()

    await sender.prepare()

    await gather(
        sender.tasks_add(),
        *[sender.execute_tasks() for _ in range(10)]
    )


if __name__ == "__main__":
    run(main())
