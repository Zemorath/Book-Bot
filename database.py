import sqlite3

def connect_db():
    return sqlite3.connect('book_bot.db')

def create_tables():
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_books (
                user_id INTEGER,
                title TEXT,
                isbn TEXT,
                PRIMARY KEY (user_id, isbn)
            )
        ''')
        conn.commit()

def add_book(user_id, title, isbn):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO user_books (user_id, title, isbn) 
            VALUES (?, ?, ?)
        ''', (user_id, title, isbn))
        conn.commit()

def remove_book(user_id, isbn):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM user_books 
            WHERE user_id = ? AND isbn = ?
        ''', (user_id, isbn))
        conn.commit()

def list_books(user_id):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT title, isbn FROM user_books 
            WHERE user_id = ?
        ''', (user_id,))
        return cursor.fetchall()
