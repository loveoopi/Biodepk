import os
import re
import sqlite3
import logging
from datetime import datetime
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import FloodWait, BadRequest
from config import API_ID, API_HASH, BOT_TOKEN, DEVELOPER, BOT_NAME

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
DB_PATH = 'user_data/bio_links.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  has_link INTEGER DEFAULT 0,
                  last_checked TEXT,
                  bio_text TEXT)''')
    
    # Deleted messages log
    c.execute('''CREATE TABLE IF NOT EXISTS deleted_messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  chat_id INTEGER,
                  timestamp TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(user_id))''')
    
    conn.commit()
    conn.close()

init_db()

class LinkDetector:
    @staticmethod
    def has_links(text):
        """Check for multiple types of links in text"""
        if not text:
            return False
            
        patterns = [
            # Standard URLs
            r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+',
            # Telegram links
            r't\.me/\w+',
            r'@\w+',
            # Common domains
            r'\w+\.(com|net|org|io|me|info|xyz)\b',
            # IP addresses
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
        ]
        
        text = text.lower()
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

def db_execute(query, params=()):
    """Helper function for database operations"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

def db_fetch(query, params=()):
    """Helper function to fetch data"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    result = c.fetchall()
    conn.close()
    return result

# Rest of your bot implementation...
# [Keep your existing start, enable, disable commands]

@app.on_message(filters.group & ~filters.service)
async def check_messages(client, message: Message):
    if message.chat.id not in enabled_groups:
        return

    try:
        user = await client.get_users(message.from_user.id)
        
        # Check cache first
        cached_data = db_fetch('SELECT has_link, bio_text FROM users WHERE user_id = ?', (user.id,))
        
        if cached_data:
            has_link, bio_text = cached_data[0]
        else:
            # Get fresh data if not cached
            bio_text = getattr(user, 'bio', '')
            has_link = LinkDetector.has_links(bio_text)
            
            # Store in database
            db_execute('''INSERT INTO users 
                         (user_id, username, has_link, last_checked, bio_text)
                         VALUES (?, ?, ?, ?, ?)''',
                      (user.id, user.username, int(has_link), datetime.now().isoformat(), bio_text))

        if has_link:
            try:
                await message.delete()
                logger.info(f"Deleted message from {user.id} in {message.chat.id}")
                
                # Log deletion
                db_execute('''INSERT INTO deleted_messages
                             (user_id, chat_id, timestamp)
                             VALUES (?, ?, ?)''',
                          (user.id, message.chat.id, datetime.now().isoformat()))
                
            except BadRequest as e:
                logger.error(f"Delete failed: {e}")

    except Exception as e:
        logger.error(f"Error processing message: {e}")

# [Rest of your existing bot code]
