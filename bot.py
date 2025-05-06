# bot.py - Full implementation
import os
import sqlite3
import logging
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from config import API_ID, API_HASH, BOT_TOKEN

# Setup directories
os.makedirs('user_data', exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database initialization
def init_db():
    try:
        conn = sqlite3.connect(
            'user_data/bio_links.db',
            timeout=10,
            check_same_thread=False
        )
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                has_link INTEGER DEFAULT 0,
                last_checked TEXT,
                bio_text TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS deleted_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                timestamp TEXT
            )
        ''')
        
        conn.commit()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database error: {e}")
    finally:
        conn.close()

# Initialize the bot
app = Client(
    "bio_protector",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Initialize database when bot starts
init_db()

# Your bot handlers here (keep your existing message handlers)
# ...

if __name__ == "__main__":
    app.run()
