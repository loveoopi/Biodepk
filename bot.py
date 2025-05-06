import os
import re
import sqlite3
import logging
from datetime import datetime
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.enums import ChatMemberStatus, ParseMode
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
os.makedirs('user_data', exist_ok=True)
DB_PATH = 'user_data/bio_links.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  has_link INTEGER,
                  last_checked TEXT)''')
    conn.commit()
    conn.close()

init_db()

class UserBioChecker:
    @staticmethod
    def has_link_in_bio(bio_text: str) -> bool:
        """Check if bio contains any links"""
        patterns = [
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            r't\.me/[a-zA-Z0-9_]+',
            r'@[a-zA-Z0-9_]+',
            r'[a-zA-Z0-9-]+\.(com|net|org|io|me)'
        ]
        if not bio_text:
            return False
        return any(re.search(pattern, bio_text, re.IGNORECASE) for pattern in patterns)

    @staticmethod
    def update_user_data(user_id: int, has_link: bool):
        """Store user bio link status in database"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO users 
                     (user_id, has_link, last_checked) 
                     VALUES (?, ?, ?)''',
                  (user_id, int(has_link), datetime.now().isoformat()))
        conn.commit()
        conn.close()

    @staticmethod
    def get_user_data(user_id: int) -> tuple:
        """Retrieve user bio link status from database"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT has_link FROM users WHERE user_id = ?''', (user_id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if user is admin or owner"""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]
    except Exception as e:
        logger.error(f"Admin check error: {e}")
        return False

async def main():
    app = Client(
        "bio_link_protector",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=True
    )

    try:
        await app.start()
        bot_username = (await app.get_me()).username
        logger.info(f"Bot @{bot_username} started successfully!")

        @app.on_message(filters.command("start") & filters.private)
        async def start(client: Client, message: Message):
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Developer", url=f"https://t.me/{DEVELOPER.lstrip('@')}"),
                        InlineKeyboardButton("Help", callback_data="help")
                    ],
                    [InlineKeyboardButton("Add me to group", 
                     url=f"https://t.me/{bot_username}?startgroup=true&admin=delete_messages+restrict_members")]
                ]
            )
            await message.reply_text(
                f"Hi, I am {BOT_NAME}. Please make me admin with 'Delete Messages' permission.",
                reply_markup=keyboard
            )

        @app.on_message(filters.command(["enable", "disable"]) & filters.group)
        async def toggle_protection(client: Client, message: Message):
            if not await is_admin(client, message.chat.id, message.from_user.id):
                await message.reply("⚠️ You need admin rights to use this command.")
                return

            if "enable" in message.text.lower():
                enabled_groups.add(message.chat.id)
                await message.reply("✅ Bio link protection enabled!")
            else:
                enabled_groups.discard(message.chat.id)
                await message.reply("❌ Bio link protection disabled!")

        @app.on_message(filters.group & ~filters.service)
        async def check_messages(client: Client, message: Message):
            if message.chat.id not in enabled_groups:
                return

            try:
                # Get full user info including bio
                user = await client.get_users(message.from_user.id)
                
                # Check if we have cached bio data
                cached_status = UserBioChecker.get_user_data(user.id)
                
                if cached_status is not None:
                    has_link = bool(cached_status)
                else:
                    # Get fresh bio data if not cached
                    has_link = False
                    if hasattr(user, 'bio') and user.bio:
                        has_link = UserBioChecker.has_link_in_bio(user.bio)
                        UserBioChecker.update_user_data(user.id, has_link)
                
                if has_link:
                    try:
                        await message.delete()
                        logger.info(f"Deleted message from {user.id} in {message.chat.id}")
                    except BadRequest as e:
                        logger.error(f"Delete failed: {e}")
            except Exception as e:
                logger.error(f"Message processing error: {e}")

        await idle()

    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
