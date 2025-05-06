import time
import asyncio
import re
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.errors import FloodWait, BadRequest
from config import API_ID, API_HASH, BOT_TOKEN, DEVELOPER, BOT_NAME

# Database to store enabled groups
enabled_groups = set()

async def get_bot_username(client):
    me = await client.get_me()
    return me.username

def create_start_keyboard(bot_username, developer_username):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Developer", url=f"https://t.me/{developer_username}"),
                InlineKeyboardButton("Help", callback_data="help")
            ],
            [InlineKeyboardButton("Add me to group", 
             url=f"https://t.me/{bot_username}?startgroup=true&admin=delete_messages+restrict_members")]
        ]
    )

async def has_link_in_bio(client, user_id):
    try:
        # Get full user info including bio
        user = await client.get_users(user_id)
        if hasattr(user, 'bio') and user.bio:
            # Check for links in bio
            return bool(re.search(
                r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', 
                user.bio
            ))
        return False
    except Exception as e:
        print(f"Error checking bio for {user_id}: {e}")
        return False

async def main():
    app = Client(
        "bio_link_protector",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=True,
        workers=2
    )

    try:
        await app.start()
        bot_username = await get_bot_username(app)
        print(f"Bot @{bot_username} started successfully!")

        @app.on_message(filters.command("start") & filters.private)
        async def start(client, message: Message):
            keyboard = create_start_keyboard(bot_username, DEVELOPER.lstrip('@'))
            await message.reply_text(
                f"Hi, I am {BOT_NAME}. Please make me admin with 'Delete Messages' and 'Restrict Members' permissions.",
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

**Requirements:**
- Admin with 'Delete Messages' permission
- 'Restrict Members' permission recommended
"""
                await callback_query.message.edit_text(help_text)

        @app.on_message(filters.command("enable") & filters.group)
        async def enable_protection(client, message: Message):
            try:
                member = await client.get_chat_member(message.chat.id, message.from_user.id)
                if member.status in ["creator", "administrator"]:
                    enabled_groups.add(message.chat.id)
                    await message.reply("✅ Bio link protection enabled!")
                else:
                    await message.reply("⚠️ You need admin rights to use this command.")
            except Exception as e:
                await message.reply(f"❌ Error: {str(e)}")

        @app.on_message(filters.command("disable") & filters.group)
        async def disable_protection(client, message: Message):
            try:
                member = await client.get_chat_member(message.chat.id, message.from_user.id)
                if member.status in ["creator", "administrator"]:
                    enabled_groups.discard(message.chat.id)
                    await message.reply("❌ Bio link protection disabled!")
                else:
                    await message.reply("⚠️ You need admin rights to use this command.")
            except Exception as e:
                await message.reply(f"❌ Error: {str(e)}")

        @app.on_message(filters.group & ~filters.service)
        async def check_messages(client, message: Message):
            if message.chat.id not in enabled_groups:
                return

            try:
                if await has_link_in_bio(client, message.from_user.id):
                    try:
                        await message.delete()
                        print(f"Deleted message from {message.from_user.id} in {message.chat.id}")
                    except BadRequest as e:
                        print(f"Delete failed (missing permissions?): {e}")
            except Exception as e:
                print(f"Error processing message: {e}")

        await idle()

    except FloodWait as e:
        print(f"FloodWait: Need to wait {e.value} seconds")
        time.sleep(e.value)
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        await app.stop()

if __name__ == "__main__":
    try:
        import uvloop
        uvloop.install()
    except ImportError:
        pass
        
    asyncio.run(main())
