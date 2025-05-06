import time
import ntplib
from datetime import datetime
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import API_ID, API_HASH, BOT_TOKEN, DEVELOPER, BOT_NAME

# Time synchronization function
def sync_time():
    try:
        client = ntplib.NTPClient()
        response = client.request('pool.ntp.org')
        print(f"Time synchronized to: {datetime.fromtimestamp(response.tx_time)}")
    except Exception as e:
        print(f"Time sync failed: {e}")

# Sync time before starting
print("Syncing time with NTP server...")
sync_time()
time.sleep(5)  # Additional delay

# Initialize client with proper settings
app = Client(
    name="bio_link_protector",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=4,
    sleep_threshold=60,
    in_memory=True,
    no_updates=True
)

# Store enabled groups (in production, use a database)
enabled_groups = set()

# Start command
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

# Ping command to check time sync
@app.on_message(filters.command("ping"))
async def ping(client, message):
    await message.reply(f"Pong! Current server time: {datetime.now()}")

# Enable/disable commands and message handler remain the same as your original code
# ...

if __name__ == "__main__":
    print("Starting bot with proper time synchronization...")
    try:
        app.start()
        print("Bot started successfully!")
        idle()
    except Exception as e:
        print(f"Bot failed to start: {e}")
        # Attempt restart after delay
        time.sleep(15)
        app.start()
        idle()
    finally:
        app.stop()
