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
        INSERT OR REPLACE INTO user_books (user_id, book_id, rating, top_ten) VALUES (?, ?, ?, (SELECT top_ten FROM user_books WHERE user_id = ? AND book_id = ?))
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





# import psycopg2
# from psycopg2 import pool
# import os

# class Database:
#     def __init__(self):
#         self.db_pool = None

#     def connect(self):
#         if self.db_pool is None:
#             self.db_pool = psycopg2.pool.SimpleConnectionPool(
#                 1, 20,  # Adjust these numbers based on your needs
#                 dbname=os.getenv('DB_NAME'),
#                 user=os.getenv('DB_USER'),
#                 password=os.getenv('DB_PASSWORD'),
#                 host=os.getenv('DB_HOST'),
#                 port=os.getenv('DB_PORT')
#             )

#     def close(self):
#         if self.db_pool:
#             self.db_pool.closeall()
#             self.db_pool = None

#     def execute(self, query, params=()):
#         conn = self.db_pool.getconn()
#         try:
#             with conn.cursor() as cursor:
#                 cursor.execute(query, params)
#                 conn.commit()
#         finally:
#             self.db_pool.putconn(conn)

#     def fetchone(self, query, params=()):
#         conn = self.db_pool.getconn()
#         try:
#             with conn.cursor() as cursor:
#                 cursor.execute(query, params)
#                 return cursor.fetchone()
#         finally:
#             self.db_pool.putconn(conn)

#     def fetchall(self, query, params=()):
#         conn = self.db_pool.getconn()
#         try:
#             with conn.cursor() as cursor:
#                 cursor.execute(query, params)
#                 return cursor.fetchall()
#         finally:
#             self.db_pool.putconn(conn)

# db = Database()

# def create_tables():
#     db.connect()
#     db.execute("""
#         CREATE TABLE IF NOT EXISTS users (
#             id SERIAL PRIMARY KEY,
#             user_id BIGINT UNIQUE
#         )
#     """)
#     db.execute("""
#         CREATE TABLE IF NOT EXISTS books (
#             id SERIAL PRIMARY KEY,
#             isbn VARCHAR(13) UNIQUE,
#             title TEXT,
#             image_url TEXT
#         )
#     """)
#     db.execute("""
#         CREATE TABLE IF NOT EXISTS user_books (
#             user_id INTEGER REFERENCES users(id),
#             book_id INTEGER REFERENCES books(id),
#             rating INTEGER,
#             PRIMARY KEY (user_id, book_id)
#         )
#     """)

# def add_user(user_id):
#     db.execute("""
#         INSERT INTO users (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING
#     """, (user_id,))

# def add_book(user_id, title, isbn, image_url=None, rating=None):
#     db.execute("""
#         INSERT INTO books (isbn, title, image_url) VALUES (%s, %s, %s) ON CONFLICT (isbn) DO NOTHING
#     """, (isbn, title, image_url))
#     book_id = db.fetchone("SELECT id FROM books WHERE isbn = %s", (isbn,))[0]
    
#     add_user(user_id)
#     user_db_id = db.fetchone("SELECT id FROM users WHERE user_id = %s", (user_id,))[0]

#     db.execute("""
#         INSERT INTO user_books (user_id, book_id, rating) VALUES (%s, %s, %s)
#         ON CONFLICT (user_id, book_id) DO UPDATE SET rating = EXCLUDED.rating
#     """, (user_db_id, book_id, rating))

# def remove_book(user_id, isbn):
#     book_id = db.fetchone("SELECT id FROM books WHERE isbn = %s", (isbn,))[0]
#     user_db_id = db.fetchone("SELECT id FROM users WHERE user_id = %s", (user_id,))[0]
#     db.execute("""
#         DELETE FROM user_books WHERE user_id = %s AND book_id = %s
#     """, (user_db_id, book_id))

# def list_books(user_id):
#     user_db_id = db.fetchone("SELECT id FROM users WHERE user_id = %s", (user_id,))
#     if user_db_id is None:
#         add_user(user_id)
#         user_db_id = db.fetchone("SELECT id FROM users WHERE user_id = %s", (user_id,))
#     user_db_id = user_db_id[0]
#     return db.fetchall("""
#         SELECT books.title, books.isbn, user_books.rating 
#         FROM books 
#         JOIN user_books ON books.id = user_books.book_id 
#         WHERE user_books.user_id = %s
#     """, (user_db_id,))

# def update_rating(user_id, isbn, rating):
#     book_id = db.fetchone("SELECT id FROM books WHERE isbn = %s", (isbn,))[0]
#     user_db_id = db.fetchone("SELECT id FROM users WHERE user_id = %s", (user_id,))[0]
#     db.execute("""
#         UPDATE user_books SET rating = %s WHERE user_id = %s AND book_id = %s
#     """, (rating, user_db_id, book_id))

