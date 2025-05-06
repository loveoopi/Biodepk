import time
import ntplib
import asyncio
from datetime import datetime
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import API_ID, API_HASH, BOT_TOKEN, DEVELOPER, BOT_NAME

# Enhanced time synchronization
def sync_time():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client = ntplib.NTPClient()
            response = client.request('pool.ntp.org', timeout=5)
            synced_time = datetime.fromtimestamp(response.tx_time)
            print(f"Time synchronized (attempt {attempt+1}): {synced_time}")
            return True
        except Exception as e:
            print(f"Time sync failed (attempt {attempt+1}): {e}")
            time.sleep(2)
    return False

async def main():
    # Sync time before starting
    print("Initializing time synchronization...")
    if not sync_time():
        print("Warning: Time synchronization failed, continuing anyway")
    
    # Initialize client with enhanced settings
    app = Client(
        name="bio_link_protector",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        workers=4,
        sleep_threshold=60,
        in_memory=True,
        no_updates=False  # Changed to False to receive updates
    )

    # Store enabled groups
    enabled_groups = set()

    # Start command handler
    @app.on_message(filters.command("start") & filters.private)
    async def start(client, message: Message):
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Developer", url=f"tg://user?id={DEVELOPER}"),
                    InlineKeyboardButton("Help", callback_data="help")
                ],
                [InlineKeyboardButton("Add me to group", url=f"http://t.me/{BOT_NAME}?startgroup=true")]
            ]
        )
        await message.reply_text(
            f"Hi, I am {BOT_NAME}. Give me ban and delete messages permission to work properly.",
            reply_markup=keyboard
        )

    # Callback handler
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

    # Ping command for testing
    @app.on_message(filters.command("ping"))
    async def ping(client, message):
        await message.reply(f"✅ Bot is alive! Server time: {datetime.now()}")

    # Start the bot with error handling
    try:
        print("Starting bot...")
        await app.start()
        bot_info = await app.get_me()
        print(f"Bot @{bot_info.username} is now running!")
        
        # Keep the bot running
        await idle()
        
    except Exception as e:
        print(f"Bot crashed: {str(e)}")
    finally:
        print("Stopping bot...")
        await app.stop()
        print("Bot stopped successfully")

if __name__ == "__main__":
    # Set event loop policy for Heroku
    try:
        import uvloop
        uvloop.install()
    except ImportError:
        print("uvloop not available, using default asyncio")

    # Run the bot with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            asyncio.run(main())
            break
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {str(e)}")
            if attempt < max_retries - 1:
                print("Restarting in 5 seconds...")
                time.sleep(5)
            else:
                print("Max retries reached, giving up")
