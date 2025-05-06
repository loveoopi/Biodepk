import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from config import API_ID, API_HASH, BOT_TOKEN, DEVELOPER, BOT_NAME

# Initialize the bot
app = Client(
    "bio_link_protector",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Database to store enabled groups
enabled_groups = set()

# Helper function to check if bio contains links
def has_link_in_bio(user):
    if user.bio:
        # Regex pattern to detect URLs
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        return bool(url_pattern.search(user.bio))
    return False

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

# Callback query handler
@app.on_callback_query()
async def callback_handler(client, callback_query):
    data = callback_query.data
    
    if data == "help":
        help_text = """
**Available Commands:**
- /start - Start the bot
- /enable - Enable bio link protection in this group
- /disable - Disable bio link protection in this group

**Note:** To work properly, I need:
- Delete messages permission
- Ban users permission (optional but recommended)
"""
        await callback_query.message.edit_text(help_text)
        await callback_query.answer()

# Enable command handler
@app.on_message(filters.command("enable") & filters.group)
async def enable_protection(client, message: Message):
    chat_id = message.chat.id
    if message.from_user and (await client.get_chat_member(chat_id, message.from_user.id)).status in ["creator", "administrator"]:
        enabled_groups.add(chat_id)
        await message.reply_text("✅ Bio link protection enabled. I will now delete messages from users with links in their bio.")
    else:
        await message.reply_text("⚠️ You need to be an admin to use this command.")

# Disable command handler
@app.on_message(filters.command("disable") & filters.group)
async def disable_protection(client, message: Message):
    chat_id = message.chat.id
    if message.from_user and (await client.get_chat_member(chat_id, message.from_user.id)).status in ["creator", "administrator"]:
        enabled_groups.discard(chat_id)
        await message.reply_text("❌ Bio link protection disabled. I will no longer delete messages based on user bios.")
    else:
        await message.reply_text("⚠️ You need to be an admin to use this command.")

# Message handler to check for links in bio
@app.on_message(filters.group)
async def check_bio_links(client, message: Message):
    chat_id = message.chat.id
    
    if chat_id not in enabled_groups:
        return
    
    if not message.from_user:
        return
    
    try:
        user = await client.get_users(message.from_user.id)
        if has_link_in_bio(user):
            try:
                await message.delete()
                # Optional: You can also ban the user
                # await client.ban_chat_member(chat_id, user.id)
            except Exception as e:
                print(f"Couldn't delete message: {e}")
    except Exception as e:
        print(f"Error checking user bio: {e}")

# Run the bot
print("Bot is running...")
app.run()
