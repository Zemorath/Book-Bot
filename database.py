import sqlite3

def create_tables():
    with sqlite3.connect("library.db") as conn:
        cursor = conn.cursor()
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE
            )
        """)
        
        # Create books table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                isbn TEXT UNIQUE,
                title TEXT,
                image_url TEXT
            )
        """)
        
        # Create user_books table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_books (
                user_id INTEGER,
                book_id INTEGER,
                rating INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(book_id) REFERENCES books(id),
                PRIMARY KEY (user_id, book_id)
            )
        """)
        conn.commit()

def add_user(user_id):
    with sqlite3.connect("library.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id) VALUES (?)
        """, (user_id,))
        conn.commit()

def add_book(user_id, title, isbn, image_url=None, rating=None):
    with sqlite3.connect("library.db") as conn:
        cursor = conn.cursor()
        # Add book to books table
        cursor.execute("""
            INSERT OR IGNORE INTO books (isbn, title, image_url) VALUES (?, ?, ?)
        """, (isbn, title, image_url))
        cursor.execute("SELECT id FROM books WHERE isbn = ?", (isbn,))
        book_id = cursor.fetchone()[0]
        
        # Add user to users table
        add_user(user_id)
        cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
        user_db_id = cursor.fetchone()[0]

        # Add entry to user_books table
        cursor.execute("""
            INSERT OR REPLACE INTO user_books (user_id, book_id, rating) VALUES (?, ?, ?)
        """, (user_db_id, book_id, rating))
        conn.commit()

def remove_book(user_id, isbn):
    with sqlite3.connect("library.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM books WHERE isbn = ?", (isbn,))
        book_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
        user_db_id = cursor.fetchone()[0]
        cursor.execute("""
            DELETE FROM user_books WHERE user_id = ? AND book_id = ?
        """, (user_db_id, book_id))
        conn.commit()

def list_books(user_id):
    with sqlite3.connect("library.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
        user_db_id = cursor.fetchone()[0]
        cursor.execute("""
            SELECT books.title, books.isbn, user_books.rating 
            FROM books 
            JOIN user_books ON books.id = user_books.book_id 
            WHERE user_books.user_id = ?
        """, (user_db_id,))
        return cursor.fetchall()

def update_rating(user_id, isbn, rating):
    with sqlite3.connect("library.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM books WHERE isbn = ?", (isbn,))
        book_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
        user_db_id = cursor.fetchone()[0]
        cursor.execute("""
            UPDATE user_books SET rating = ? WHERE user_id = ? AND book_id = ?
        """, (rating, user_db_id, book_id))
        conn.commit()
