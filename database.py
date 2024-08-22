import aiosqlite

class Database:
    def __init__(self, db_path="library.db"):
        self.db_path = db_path

    async def connect(self):
        self.conn = await aiosqlite.connect(self.db_path)
        await self.create_tables()

    async def create_tables(self):
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE
            )
        """)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                isbn TEXT UNIQUE,
                title TEXT,
                author TEXT,
                image_url TEXT
            )
        """)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user_books (
                user_id INTEGER,
                book_id INTEGER,
                rating INTEGER,
                top_ten BOOLEAN DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(book_id) REFERENCES books(id),
                PRIMARY KEY (user_id, book_id)
            )
        """)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS designated_channels (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
        """)
        await self.conn.commit()

    async def close(self):
        await self.conn.close()

    async def execute(self, query, params=()):
        async with self.conn.execute(query, params) as cursor:
            await self.conn.commit()
            return cursor

    async def fetchone(self, query, params=()):
        async with self.conn.execute(query, params) as cursor:
            return await cursor.fetchone()

    async def fetchall(self, query, params=()):
        async with self.conn.execute(query, params) as cursor:
            return await cursor.fetchall()

db = Database()

async def add_user(user_id):
    await db.execute("""
        INSERT OR IGNORE INTO users (user_id) VALUES (?)
    """, (user_id,))

async def add_book(user_id, title, author, isbn, image_url=None, rating=None):
    await db.execute("""
        INSERT OR IGNORE INTO books (isbn, title, author, image_url) VALUES (?, ?, ?, ?)
    """, (isbn, title, author, image_url))
    book_id = (await db.fetchone("SELECT id FROM books WHERE isbn = ?", (isbn,)))[0]
    
    await add_user(user_id)
    user_db_id = (await db.fetchone("SELECT id FROM users WHERE user_id = ?", (user_id,)))[0]

    await db.execute("""
        INSERT OR REPLACE INTO user_books (user_id, book_id, rating, top_ten) 
        VALUES (?, ?, ?, (SELECT top_ten FROM user_books WHERE user_id = ? AND book_id = ?))
    """, (user_db_id, book_id, rating, user_db_id, book_id))

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
        SELECT books.title, books.author, books.isbn, user_books.rating 
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

async def mark_top_ten(user_id, isbn, top_ten):
    book_id = (await db.fetchone("SELECT id FROM books WHERE isbn = ?", (isbn,)))[0]
    user_db_id = (await db.fetchone("SELECT id FROM users WHERE user_id = ?", (user_id,)))[0]
    await db.execute("""
        UPDATE user_books SET top_ten = ? WHERE user_id = ? AND book_id = ?
    """, (top_ten, user_db_id, book_id))

async def list_top_ten(user_id):
    user_db_id = await db.fetchone("SELECT id FROM users WHERE user_id = ?", (user_id,))
    if user_db_id is None:
        await add_user(user_id)
        user_db_id = await db.fetchone("SELECT id FROM users WHERE user_id = ?", (user_id,))
    user_db_id = user_db_id[0]
    return await db.fetchall("""
        SELECT books.title, books.author, books.isbn, user_books.rating 
        FROM books 
        JOIN user_books ON books.id = user_books.book_id 
        WHERE user_books.user_id = ? AND user_books.top_ten = 1
        ORDER BY user_books.rating DESC, books.title
        LIMIT 10
    """, (user_db_id,))

async def list_books_by_author(user_id, author):
    user_db_id = await db.fetchone("SELECT id FROM users WHERE user_id = ?", (user_id,))
    if user_db_id is None:
        await add_user(user_id)
        user_db_id = await db.fetchone("SELECT id FROM users WHERE user_id = ?", (user_id,))
    user_db_id = user_db_id[0]
    return await db.fetchall("""
        SELECT books.title, books.isbn, user_books.rating 
        FROM books 
        JOIN user_books ON books.id = user_books.book_id 
        WHERE user_books.user_id = ? AND books.author LIKE ?
    """, (user_db_id, f"%{author}%"))

async def list_books_by_rating(user_id, min_rating):
    user_db_id = await db.fetchone("SELECT id FROM users WHERE user_id = ?", (user_id,))
    if user_db_id is None:
        await add_user(user_id)
        user_db_id = await db.fetchone("SELECT id FROM users WHERE user_id = ?", (user_id,))
    user_db_id = user_db_id[0]
    return await db.fetchall("""
        SELECT books.title, books.author, books.isbn, user_books.rating 
        FROM books 
        JOIN user_books ON books.id = user_books.book_id 
        WHERE user_books.user_id = ? AND user_books.rating >= ?
    """, (user_db_id, min_rating))

async def list_books_by_title(user_id, title_part):
    user_db_id = await db.fetchone("SELECT id FROM users WHERE user_id = ?", (user_id,))
    if user_db_id is None:
        await add_user(user_id)
        user_db_id = await db.fetchone("SELECT id FROM users WHERE user_id = ?", (user_id,))
    user_db_id = user_db_id[0]
    return await db.fetchall("""
        SELECT books.title, books.author, books.isbn, user_books.rating 
        FROM books 
        JOIN user_books ON books.id = user_books.book_id 
        WHERE user_books.user_id = ? AND books.title LIKE ?
    """, (user_db_id, f"%{title_part}%"))

async def set_designated_channel(guild_id, channel_id):
    await db.execute("""
        INSERT OR REPLACE INTO designated_channels (guild_id, channel_id) 
        VALUES (?, ?)
    """, (guild_id, channel_id))
    await db.conn.commit()

async def get_designated_channel(guild_id):
    row = await db.fetchone("""
        SELECT channel_id FROM designated_channels WHERE guild_id = ?
    """, (guild_id,))
    return row[0] if row else None
