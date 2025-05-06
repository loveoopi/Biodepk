import os
import re
import sqlite3
import logging
from datetime import datetime
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import BadRequest
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
    try:
        os.makedirs('user_data', exist_ok=True)
        conn = sqlite3.connect(
            'user_data/bio_links.db',
            timeout=30,
            check_same_thread=False
        )
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        
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
        conn.commit()
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise

# Initialize database
db_conn = init_db()

# Bot client with optimized settings
app = Client(
    "bio_link_protector",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=4,
    sleep_threshold=30,
    in_memory=True
)

# Store enabled groups
enabled_groups = set()

def has_links(text: str) -> bool:
    """Enhanced link detection"""
    if not text:
        return False
    patterns = [
        r'https?://[^\s]+',
        r't\.me/[a-zA-Z0-9_]+',
        r'@[a-zA-Z0-9_]+',
        r'[a-zA-Z0-9-]+\.(com|net|org|io|me)\b'
    ]
    text = text.lower()
    return any(re.search(pattern, text) for pattern in patterns)

async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Check admin status with cache"""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except Exception as e:
        logger.error(f"Admin check error: {e}")
        return False

@app.on_message(filters.command("start") & filters.private)
async def start(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Developer", url=f"https://t.me/{DEVELOPER.lstrip('@')}")],
            [InlineKeyboardButton("Add to Group", 
             url=f"https://t.me/{(await client.get_me()).username}?startgroup=true&admin=delete_messages")]
        ]
    )
    await message.reply_text(
        f"Hi, I'm {BOT_NAME}. Add me to groups with Delete Messages permission.",
        reply_markup=keyboard
    )

@app.on_message(filters.command("enable") & filters.group)
async def enable_protection(client: Client, message: Message):
    if await is_admin(client, message.chat.id, message.from_user.id):
        enabled_groups.add(message.chat.id)
        await message.reply("✅ Protection enabled! I'll delete messages from users with links in bios.")
    else:
        await message.reply("⚠️ You need admin rights for this command.")

@app.on_message(filters.command("disable") & filters.group)
async def disable_protection(client: Client, message: Message):
    if await is_admin(client, message.chat.id, message.from_user.id):
        enabled_groups.discard(message.chat.id)
        await message.reply("❌ Protection disabled.")
    else:
        await message.reply("⚠️ You need admin rights for this command.")

@app.on_message(filters.group & ~filters.service)
async def check_messages(client: Client, message: Message):
    if message.chat.id not in enabled_groups:
        return
    
    try:
        # Skip if message is from admin
        if await is_admin(client, message.chat.id, message.from_user.id):
            return
            
        user = await client.get_users(message.from_user.id)
        bio_text = getattr(user, 'bio', '')
        
        if has_links(bio_text):
            try:
                await message.delete()
                logger.info(f"Deleted message from {user.id} in chat {message.chat.id}")
                
                # Update database
                cursor = db_conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, username, has_link, bio_text, last_checked)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user.id, user.username, 1, bio_text, datetime.now().isoformat()))
                db_conn.commit()
                
            except BadRequest as e:
                logger.error(f"Delete failed: {e}")
                # Try to notify admins about missing permissions
                try:
                    await client.send_message(
                        message.chat.id,
                        "⚠️ I need Delete Messages permission to work properly!",
                        reply_to_message_id=message.id
                    )
                except:
                    pass
                
    except Exception as e:
        logger.error(f"Error processing message: {e}")

if __name__ == "__main__":
    logger.info("Starting bot...")
    try:
        app.start()
        bot_me = app.get_me()
        logger.info(f"Bot @{bot_me.username} started successfully!")
        idle()
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
    finally:
        app.stop()
        db_conn.close()
        logger.info("Bot stopped")
