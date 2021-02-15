from typing import Optional

import asyncpg

from config import Config


class FlibustaChannelDB:
    pool: asyncpg.pool.Pool

    @classmethod
    async def prepare(cls, app):
        cls.pool = await asyncpg.create_pool(
            user=Config.DB_USER, password=Config.DB_PASSWORD,
            host=Config.DB_HOST, database=Config.DB_DATABASE
        )
        
        await cls.create_table()

    @classmethod
    async def create_table(cls):
        await cls.pool.execute(
            f"""
CREATE TABLE IF NOT EXISTS messages 
(
    book_id INTEGER NOT NULL,
    file_type VARCHAR(7) NOT NULL,
    message_id BIGINT NOT NULL,
    PRIMARY KEY (book_id, file_type)
);
""")

    @classmethod
    async def set_message_id(cls, book_id: int, file_type: str, 
                             message_id: int):
        await cls.pool.execute(
            "INSERT INTO messages (book_id, file_type, message_id) VALUES ($1, CAST($2 AS VARCHAR), $3) "
            "ON CONFLICT (book_id, file_type) DO UPDATE SET message_id = EXCLUDED.message_id", 
            book_id, file_type, message_id
        )

    @classmethod
    async def get_message_id(cls, book_id: int, file_type: str) -> Optional[int]:
        rows = await cls.pool.fetch(
            "SELECT message_id FROM messages WHERE book_id = $1 AND file_type = CAST($2 AS VARCHAR)",
            book_id, file_type
        )
        if rows:
            return rows[0]["message_id"]
        return None

    @classmethod
    async def delete_message_id(cls, message_id: int):
        await cls.pool.execute(
            "DELETE FROM messages WHERE message_id = $1", message_id
        )

    @classmethod
    async def get_book_by_message_id(cls, message_id: int) -> Optional[int]:
        rows = await cls.pool.fetch(
            "SELECT book_id FROM messages WHERE message_id = $1", message_id
        )
        if rows:
            return rows[0]["book_id"]
        return None
