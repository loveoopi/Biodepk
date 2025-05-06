import time
import ntplib
import asyncio
from datetime import datetime
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import API_ID, API_HASH, BOT_TOKEN, DEVELOPER, BOT_NAME

# Fix 1: Proper bot username handling
async def get_bot_username(client):
    me = await client.get_me()
    return me.username

# Fix 2: Correct button URLs
def create_start_keyboard(bot_username, developer_username):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Developer", url=f"https://t.me/{developer_username}"),
                InlineKeyboardButton("Help", callback_data="help")
            ],
            [InlineKeyboardButton("Add me to group", 
             url=f"https://t.me/{bot_username}?startgroup=true")]
        ]
    )

async def main():
    # Time synchronization
    print("Initializing time synchronization...")
    try:
        ntplib.NTPClient().request('pool.ntp.org')
    except Exception as e:
        print(f"Time sync warning: {e}")

    app = Client(
        "bio_link_protector",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=True
    )

    @app.on_message(filters.command("start") & filters.private)
    async def start(client, message: Message):
        bot_username = await get_bot_username(client)
        keyboard = create_start_keyboard(bot_username, DEVELOPER.lstrip('@'))
        
        await message.reply_text(
            f"Hi, I am {BOT_NAME}. Give me ban and delete messages permission to work properly.",
            reply_markup=keyboard
        )

    @app.on_callback_query()
    async def callback_handler(client, callback_query):
        if callback_query.data == "help":
            help_text = """
**Available Commands:**
- /start - Start the bot
- /enable - Enable bio link protection
- /disable - Disable protection
- /ping - Check if bot is alive
"""
            await callback_query.message.edit_text(help_text)

    @app.on_message(filters.command("ping"))
    async def ping(client, message):
        await message.reply("✅ Bot is alive and working!")

    try:
        await app.start()
        print("Bot started successfully!")
        await idle()
    finally:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
