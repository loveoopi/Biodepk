import os
import sqlite3
import logging
from datetime import datetime
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import BadRequest, FloodWait
from config import API_ID, API_HASH, BOT_TOKEN, DEVELOPER, BOT_NAME

# Setup logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database setup
def init_db():
    """Initialize SQLite database with proper settings for Heroku"""
    try:
        conn = sqlite3.connect(
            'file:bio_links.db?mode=memory&cache=shared',
            uri=True,
            timeout=20,
            check_same_thread=False
        )
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                has_link INTEGER DEFAULT 0,
                last_checked TEXT,
                bio_text TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deleted_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                timestamp TEXT
            )
        ''')
        conn.commit()
        logger.info("Database initialized successfully")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database initialization failed: {e}")
        raise

# Initialize database
db_conn = init_db()

# Bot setup
app = Client(
    "bio_link_protector",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True
)

# Store enabled groups
enabled_groups = set()

# Helper functions
def has_links(text: str) -> bool:
    """Check for multiple types of links in text"""
    if not text:
        return False
        
    patterns = [
        r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+',
        r't\.me/\w+',
        r'@\w+',
        r'\w+\.(com|net|org|io|me)\b'
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if user is admin or owner"""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except Exception as e:
        logger.error(f"Admin check error: {e}")
        return False

# Command handlers
@app.on_message(filters.command("start") & filters.private)
async def start(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Developer", url=f"https://t.me/{DEVELOPER.lstrip('@')}"),
                InlineKeyboardButton("Help", callback_data="help")
            ],
            [InlineKeyboardButton("Add me to group", 
             url=f"https://t.me/{(await client.get_me()).username}?startgroup=true&admin=delete_messages")]
        ]
    )
    await message.reply_text(
        f"Hi, I am {BOT_NAME}. Add me to groups with Delete Messages permission.",
        reply_markup=keyboard
    )

@app.on_message(filters.command("enable") & filters.group)
async def enable_protection(client: Client, message: Message):
    if await is_admin(client, message.chat.id, message.from_user.id):
        enabled_groups.add(message.chat.id)
        await message.reply("✅ Bio link protection enabled!")
    else:
        await message.reply("⚠️ You need admin rights to use this command.")

@app.on_message(filters.command("disable") & filters.group)
async def disable_protection(client: Client, message: Message):
    if await is_admin(client, message.chat.id, message.from_user.id):
        enabled_groups.discard(message.chat.id)
        await message.reply("❌ Bio link protection disabled!")
    else:
        await message.reply("⚠️ You need admin rights to use this command.")

# Message handler
@app.on_message(filters.group & ~filters.service)
async def check_messages(client: Client, message: Message):
    if message.chat.id not in enabled_groups:
        return

    try:
        user = await client.get_users(message.from_user.id)
        cursor = db_conn.cursor()
        
        # Check cache first
        cursor.execute('SELECT has_link, bio_text FROM users WHERE user_id = ?', (user.id,))
        result = cursor.fetchone()
        
        if result:
            has_link, bio_text = result
        else:
            # Get fresh data
            bio_text = getattr(user, 'bio', '')
            has_link = has_links(bio_text)
            
            # Store in database
            cursor.execute('''
                INSERT INTO users (user_id, username, has_link, bio_text, last_checked)
                VALUES (?, ?, ?, ?, ?)
            ''', (user.id, user.username, int(has_link), bio_text, datetime.now().isoformat()))
            db_conn.commit()

        if has_link:
            try:
                await message.delete()
                cursor.execute('''
                    INSERT INTO deleted_messages (user_id, chat_id, timestamp)
                    VALUES (?, ?, ?)
                ''', (user.id, message.chat.id, datetime.now().isoformat()))
                db_conn.commit()
                logger.info(f"Deleted message from {user.id} in {message.chat.id}")
            except BadRequest as e:
                logger.error(f"Delete failed: {e}")

    except Exception as e:
        logger.error(f"Error processing message: {e}")

# Start the bot
if __name__ == "__main__":
    logger.info("Starting bot...")
    try:
        app.run()
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
    finally:
        db_conn.close()
        logger.info("Bot stopped")
