import time
import asyncio
import ntplib
from datetime import datetime
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
             url=f"https://t.me/{bot_username}?startgroup=true&admin=delete_messages")]
        ]
    )

async def handle_flood_wait(e):
    wait_time = e.value + 5  # Add 5 second buffer
    print(f"FloodWait: Sleeping for {wait_time} seconds")
    time.sleep(wait_time)
    return True

async def main():
    # Initialize client with retry logic
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            app = Client(
                "bio_link_protector",
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=BOT_TOKEN,
                in_memory=True,
                workers=2,  # Reduced workers to prevent flooding
                sleep_threshold=30
            )
            
            await app.start()
            bot_username = await get_bot_username(app)
            print(f"{datetime.now()} - Bot @{bot_username} started successfully!")
            
            @app.on_message(filters.command("start") & filters.private)
            async def start(client, message: Message):
                keyboard = create_start_keyboard(bot_username, DEVELOPER.lstrip('@'))
                await message.reply_text(
                    f"Hi, I am {BOT_NAME}. I need 'Delete Messages' permission to work properly.",
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

            @app.on_message(filters.command("enable") & filters.group)
            async def enable_protection(client, message: Message):
                if message.chat.id not in enabled_groups:
                    enabled_groups.add(message.chat.id)
                    await message.reply("✅ Bio link protection enabled!")
                else:
                    await message.reply("ℹ️ Protection is already enabled")

            @app.on_message(filters.command("disable") & filters.group)
            async def disable_protection(client, message: Message):
                if message.chat.id in enabled_groups:
                    enabled_groups.discard(message.chat.id)
                    await message.reply("❌ Bio link protection disabled!")
                else:
                    await message.reply("ℹ️ Protection is already disabled")

            @app.on_message(filters.group & ~filters.service)
            async def check_bio_links(client, message: Message):
                if message.chat.id not in enabled_groups:
                    return
                    
                try:
                    user = await client.get_users(message.from_user.id)
                    if user.bio and any(
                        x in user.bio.lower() 
                        for x in ["http://", "https://", "t.me/", ".com"]
                    ):
                        try:
                            await message.delete()
                            print(f"Deleted message from {user.id} in {message.chat.id}")
                        except BadRequest as e:
                            print(f"Delete failed (missing permissions?): {e}")
                except FloodWait as e:
                    await handle_flood_wait(e)
                except Exception as e:
                    print(f"Error checking bio: {e}")

            await idle()
            break
            
        except FloodWait as e:
            retry_count += 1
            if not await handle_flood_wait(e) or retry_count >= max_retries:
                print("Max retries reached, exiting...")
                break
        except Exception as e:
            print(f"Unexpected error: {e}")
            break
        finally:
            try:
                await app.stop()
            except:
                pass

if __name__ == "__main__":
    try:
        import uvloop
        uvloop.install()
    except ImportError:
        pass
        
    asyncio.run(main())
