import aiosqlite
import asyncio

class Database:
    def __init__(self, db_path="library.db"):
        self.db_path = db_path
        self.pool = None

    async def connect(self):
        if self.pool is None:
            self.pool = await aiosqlite.connect(self.db_path)

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def execute(self, query, params=()):
        async with self.pool.execute(query, params) as cursor:
            await self.pool.commit()
            return cursor

    async def fetchone(self, query, params=()):
        async with self.pool.execute(query, params) as cursor:
            return await cursor.fetchone()

    async def fetchall(self, query, params=()):
        async with self.pool.execute(query, params) as cursor:
            return await cursor.fetchall()

db = Database()

async def create_tables():
    await db.connect()
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isbn TEXT UNIQUE,
            title TEXT,
            image_url TEXT
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS user_books (
            user_id INTEGER,
            book_id INTEGER,
            rating INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(book_id) REFERENCES books(id),
            PRIMARY KEY (user_id, book_id)
        )
    """)

async def add_user(user_id):
    await db.execute("""
        INSERT OR IGNORE INTO users (user_id) VALUES (?)
    """, (user_id,))

async def add_book(user_id, title, isbn, image_url=None, rating=None):
    await db.execute("""
        INSERT OR IGNORE INTO books (isbn, title, image_url) VALUES (?, ?, ?)
    """, (isbn, title, image_url))
    book_id = (await db.fetchone("SELECT id FROM books WHERE isbn = ?", (isbn,)))[0]
    
    await add_user(user_id)
    user_db_id = (await db.fetchone("SELECT id FROM users WHERE user_id = ?", (user_id,)))[0]

    await db.execute("""
        INSERT OR REPLACE INTO user_books (user_id, book_id, rating) VALUES (?, ?, ?)
    """, (user_db_id, book_id, rating))

async def remove_book(user_id, isbn):
    book_id = (await db.fetchone("SELECT id FROM books WHERE isbn = ?", (isbn,)))[0]
    user_db_id = (await db.fetchone("SELECT id FROM users WHERE user_id = ?", (user_id,)))[0]
    await db.execute("""
        DELETE FROM user_books WHERE user_id = ? AND book_id = ?
    """, (user_db_id, book_id))

async def list_books(user_id):
    user_db_id = await db.fetchone("SELECT id FROM users WHERE user_id = ?", (user_id,))
    if user_db_id is None:
        await add_user(user_id)
        user_db_id = await db.fetchone("SELECT id FROM users WHERE user_id = ?", (user_id,))
    user_db_id = user_db_id[0]
    return await db.fetchall("""
        SELECT books.title, books.isbn, user_books.rating 
        FROM books 
        JOIN user_books ON books.id = user_books.book_id 
        WHERE user_books.user_id = ?
    """, (user_db_id,))

async def update_rating(user_id, isbn, rating):
    book_id = (await db.fetchone("SELECT id FROM books WHERE isbn = ?", (isbn,)))[0]
    user_db_id = (await db.fetchone("SELECT id FROM users WHERE user_id = ?", (user_id,)))[0]
    await db.execute("""
        UPDATE user_books SET rating = ? WHERE user_id = ? AND book_id = ?
    """, (rating, user_db_id, book_id))
