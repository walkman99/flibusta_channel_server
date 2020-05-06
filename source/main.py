from aiohttp import web
import asyncpg
from telethon import TelegramClient

import platform

from config import Config
from db import FlibustaChannelDB


class FlibustaChannel:
    client: TelegramClient

    @classmethod
    async def prepare(cls):
        cls.client = TelegramClient(Config.SESSION, Config.APP_ID, Config.API_HASH)

        await cls.client.start()

        if not await cls.client.is_user_authorized():
            print("Not autorized!")
            exit(-1)

    @classmethod
    async def set_message_id(cls, request: web.Request):
        book_id = int(request.match_info.get("book_id", None))
        file_type = request.match_info.get("file_type", None)
        message_id = int(request.match_info.get("message_id", None))

        await FlibustaChannelDB.set_message_id(book_id, file_type, message_id)

        return web.Response()

    @classmethod
    async def get_message_id(cls, request: web.Request):
        book_id = int(request.match_info.get("book_id", None))
        file_type = request.match_info.get("file_type", None)

        message_id = await FlibustaChannelDB.get_message_id(book_id, file_type)
        
        if message_id is None:
            return web.json_response(None)

        return web.json_response({"message_id": message_id, "channel_id": Config.CHANNEL_ID})
    
    @classmethod
    async def download(cls, request: web.Request):
        book_id = int(request.match_info.get("book_id", None))
        file_type = request.match_info.get("file_type", None)

        message_id = await FlibustaChannelDB.get_message_id(book_id, file_type)

        if message_id is None:
            return web.Response(status=204)

        message = await cls.client.get_messages(Config.CHANNEL_ID, ids=[message_id])

        if message:
            message = message[0]

        file_data = await cls.client.download_file(message.media)

        return web.Response(body=file_data)


async def prepare(*args, **kwargs):
    await FlibustaChannelDB.prepare(*args, **kwargs)
    await FlibustaChannel.prepare()


if __name__ == "__main__":
    if platform.system() == "Linux":
        try:
            import uvloop

            uvloop.install()
        except ImportError:
            print("Install uvloop for best speed!")

    app = web.Application()

    app.on_startup.append(prepare)

    app.add_routes((
        web.get("/set_message_id/{book_id}/{file_type}/{message_id}", FlibustaChannel.set_message_id),
        web.get("/get_message_id/{book_id}/{file_type}", FlibustaChannel.get_message_id),
        web.get("/download/{book_id}/{file_type}", FlibustaChannel.download)
    ))

    web.run_app(app, host=Config.HOST, port=Config.PORT)
