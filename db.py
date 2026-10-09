import mysql.connector
from flask import g
from config import Config

def get_db():
    if 'db' not in g:
        try:
            g.db = mysql.connector.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME
            )
        except mysql.connector.Error as err:
            print(f"[DB ERROR] Connection failed: {err}")
            raise
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None and db.is_connected():
        db.close()