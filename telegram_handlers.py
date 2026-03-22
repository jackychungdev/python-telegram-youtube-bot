"""
Telegram Handlers Module

This module handles all Telegram bot interactions and commands.
It provides functionality for:
- Command handlers (/start, /lang, /download)
- Message handlers (link processing)
- Callback query handlers (button clicks)
- Inline query handlers
- User authorization and language selection

Usage:
    Import handlers and register them with your Application builder.
    
Author: Python Telegram YouTube Bot
Created: 2026-03-22
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ContextTypes, filters
from telegram import InlineQueryResultsButton
from urllib.parse import urlparse
import aiosqlite
from aiocache import cached, caches

logger = logging.getLogger(__name__)

# Global variables (will be initialized)
AVAILABLE_LANGUAGES = None
ADMIN_CHAT_ID = None
TEST_MODE = None
ALLOWED_CHATS = None
DOWNLOAD_LIMIT_PER_HOUR = None

def init_telegram_module(available_languages, admin_chat_id, test_mode, allowed_chats, download_limit):
    """Initialize the Telegram module with required configuration."""
    global AVAILABLE_LANGUAGES, ADMIN_CHAT_ID, TEST_MODE, ALLOWED_CHATS, DOWNLOAD_LIMIT_PER_HOUR
    AVAILABLE_LANGUAGES = available_languages
    ADMIN_CHAT_ID = admin_chat_id
    TEST_MODE = test_mode
    ALLOWED_CHATS = allowed_chats
    DOWNLOAD_LIMIT_PER_HOUR = download_limit

async def get_user_language(user_id: int) -> str | None:
    """Gets the user's saved language."""
    async with aiosqlite.connect('users.db') as conn:
        c = await conn.cursor()
        await c.execute('SELECT language_code FROM user_languages WHERE user_id = ?', (user_id,))
        result = await c.fetchone()
        return result[0] if result else None

async def set_user_language(user_id: int, lang_code: str):
    """Saves the user's selected language."""
    async with aiosqlite.connect('users.db') as conn:
        await conn.execute('''INSERT OR REPLACE INTO user_languages 
                           (user_id, language_code) VALUES (?, ?)''', 
                        (user_id, lang_code))
        await conn.commit()

def select_language_menu():
    """Generates InlineKeyboardMarkup for language selection."""
    keyboard = [[InlineKeyboardButton(f"{lang['flag']} {lang['name']}", callback_data=f'lang_{lang["code"]}')]
                for lang in AVAILABLE_LANGUAGES]
    return InlineKeyboardMarkup(keyboard)

async def update_user(user_id, username, video_url=None, awaiting_link=None, increment_download=False):
    """Update user information in database."""
    async with aiosqlite.connect('users.db') as conn:
        c = await conn.cursor()
        last_online = datetime.now().isoformat()
        
        if increment_download:
            now = datetime.now()
            await c.execute('SELECT downloads_in_hour, last_download_time FROM users WHERE user_id = ?', (user_id,))
            result = await c.fetchone()
            downloads, last_time_str = result if result else (0, None)
            if last_time_str and (now - datetime.fromisoformat(last_time_str)).total_seconds() > 3600:
                downloads = 0
            downloads += 1
            await c.execute('''INSERT OR REPLACE INTO users 
                         (user_id, username, last_video_url, last_online, awaiting_link, downloads_in_hour, last_download_time) 
                         VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                         (user_id, username, video_url, last_online, awaiting_link or 0, downloads, now.isoformat()))
        else:
            await c.execute('''
                INSERT INTO users (user_id, username, last_video_url, last_online, awaiting_link, downloads_in_hour)
                VALUES (?, ?, ?, ?, ?, 0)
                ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                last_video_url = excluded.last_video_url,
                last_online = excluded.last_online,
                awaiting_link = excluded.awaiting_link
            ''', (user_id, username, video_url, last_online, awaiting_link or 0))

        await conn.commit()

@cached(ttl=60)
async def is_awaiting_link(user_id):
    """Check if user is awaiting link input."""
    async with aiosqlite.connect('users.db') as conn:
        c = await conn.cursor()
        await c.execute('SELECT awaiting_link FROM users WHERE user_id = ?', (user_id,))
        result = await c.fetchone()
        return result[0] if result else 0

@cached(ttl=3600)
async def is_user_authorized(user_id):
    """Check if user is authorized to use the bot."""
    async with aiosqlite.connect('authorized_users.db') as conn:
        c = await conn.cursor()
        await c.execute('SELECT user_id FROM authorized_users WHERE user_id = ?', (user_id,))
        return await c.fetchone() is not None

async def add_authorized_user(user_id):
    """Add authorized user."""
    async with aiosqlite.connect('authorized_users.db') as conn:
        await conn.execute('INSERT OR IGNORE INTO authorized_users (user_id) VALUES (?)', (user_id,))
        await conn.commit()
    await caches.get('default').delete(f"is_user_authorized:{user_id}")

async def remove_authorized_user(user_id):
    """Remove authorized user."""
    async with aiosqlite.connect('authorized_users.db') as conn:
        await conn.execute('DELETE FROM authorized_users WHERE user_id = ?', (user_id,))
        await conn.commit()
    await caches.get('default').delete(f"is_user_authorized:{user_id}")

async def request_authorization(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, username):
    """Request admin authorization for user."""
    if not TEST_MODE and user_id == ADMIN_CHAT_ID:
        await add_authorized_user(user_id)
        return True
    
    if await is_user_authorized(user_id):
        return True
    
    keyboard = [[InlineKeyboardButton("Allow", callback_data=f'allow_{user_id}'),
                 InlineKeyboardButton("Deny", callback_data=f'deny_{user_id}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"User {username} (ID: {user_id}) wants to use the bot. Allow?",
        reply_markup=reply_markup
    )
    return False

async def start_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                process_download_callback=None):
    """Handle /start command."""
    user = update.effective_user
    logger.info(f"🚀 /start command from @{user.username} (ID: {user.id})")
    
    if process_download_callback:
        await process_download_callback(user.id, user.username)
    
    user_lang = await get_user_language(user.id)
    if not user_lang:
        await update.message.reply_text(
            "Welcome! Please select your **default audio language**:",
            reply_markup=select_language_menu(),
            parse_mode='Markdown'
        )
        return
    
    args = context.args
    if args and args[0].startswith("download_"):
        video_id = args[0].split("_")[1]
        url = f"https://www.youtube.com/watch?v={video_id}"
        if process_download_callback:
            await process_download_callback(user.id, user.username, url)
        
        context.bot_data.setdefault('pending_downloads', {})[user.id] = {'url': url}
        
        if user.id == ADMIN_CHAT_ID or await is_user_authorized(user.id):
            if process_download_callback:
                await process_download_callback(user.id, user.username, url, update, context)
        else:
            await update.message.reply_text('Hello! To use the bot, please wait for authorization from the admin.')
            await request_authorization(update, context, user.id, user.username)
    else:
        text = 'Hello, admin! Send a link.' if user.id == ADMIN_CHAT_ID else 'Hello! Authorization is required to use the bot.'
        await update.message.reply_text(text)

async def handle_link_message(update: Update, context: ContextTypes.DEFAULT_TYPE,
                              is_valid_youtube_url_callback=None,
                              process_download_callback=None):
    """Handle incoming link messages."""
    message = update.effective_message
    user = update.effective_user
    url = message.text
    
    logger.info(f"📨 Message received from @{user.username} (ID: {user.id}): {url}")
    
    if message.chat.type != 'private' and message.chat.id not in ALLOWED_CHATS:
        return

    if not await get_user_language(user.id):
        await update.message.reply_text("Please select your default language first using the /lang command or the button in /start.")
        return

    if not await request_authorization(update, context, user.id, user.username):
        await message.reply_text('Waiting for admin confirmation.')
        return

    if is_valid_youtube_url_callback and not is_valid_youtube_url_callback(url):
        await message.reply_text('Please send a valid link.')
        return

    if process_download_callback:
        await process_download_callback(user.id, user.username, url, update, context)

async def lang_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /lang command."""
    await update.message.reply_text(
        "Select your **default audio language**:",
        reply_markup=select_language_menu(),
        parse_mode='Markdown'
    )

async def download_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   is_valid_youtube_url_callback=None,
                                   process_download_callback=None):
    """Handle /download command."""
    message = update.effective_message
    user = update.effective_user
    
    logger.info(f"📥 /download command from @{user.username} (ID: {user.id}), args: {context.args}")

    if not await request_authorization(update, context, user.id, user.username):
        await message.reply_text('Waiting for admin confirmation.')
        return
    
    if not await get_user_language(user.id):
        await update.message.reply_text("Please select your default language first using the /lang command or the button in /start.")
        return

    if not context.args:
        await message.reply_text('Please send a YouTube link in the next message.')
        await update_user(user.id, user.username, awaiting_link=1)
        return
    
    url = context.args[0]
    if is_valid_youtube_url_callback and not is_valid_youtube_url_callback(url):
        await message.reply_text('Please provide a valid link.')
        return

    if process_download_callback:
        await process_download_callback(user.id, user.username, url, update, context)

async def handle_auth_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle authorization callback buttons."""
    query = update.callback_query
    await query.answer()
    
    action, user_id_str = query.data.split('_', 1)
    user_id = int(user_id_str)
    
    if query.from_user.id != ADMIN_CHAT_ID:
        return
    
    if action == 'allow':
        await add_authorized_user(user_id)
        await context.bot.send_message(user_id, 'The admin has allowed you to use the bot!')
        await query.edit_message_text(f'Access for ID {user_id} granted.')
    elif action == 'deny':
        await remove_authorized_user(user_id)
        await context.bot.send_message(user_id, 'The admin has denied your access to the bot.')
        await query.edit_message_text(f'Access for ID {user_id} denied.')

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection callback."""
    query = update.callback_query
    await query.answer()

    lang_code = query.data.split('_')[1]
    user_id = query.from_user.id
    
    if lang_code not in [lang['code'] for lang in AVAILABLE_LANGUAGES]:
        await query.edit_message_text("Unknown language.")
        return

    await set_user_language(user_id, lang_code)
    
    selected_lang_info = next(lang for lang in AVAILABLE_LANGUAGES if lang['code'] == lang_code)
    
    if update.callback_query.message.text.startswith("Welcome"):
         text = 'Hello, admin! Send a link.' if user_id == ADMIN_CHAT_ID else 'Hello! Authorization is required to use the bot.'
         await query.edit_message_text(
            text=f"✅ Default language set: **{selected_lang_info['flag']} {selected_lang_info['name']}**.\n\n"
                 f"{text}",
            parse_mode='Markdown',
            reply_markup=None
        )
         if user_id != ADMIN_CHAT_ID and not await is_user_authorized(user_id):
             await request_authorization(update, context, user_id, query.from_user.username)
    else:
        await query.edit_message_text(
            text=f"✅ Default language set: **{selected_lang_info['flag']} {selected_lang_info['name']}**.\n"
                 "The bot will try to select audio tracks in this language.",
            parse_mode='Markdown',
            reply_markup=None
        )

async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE,
                               is_valid_youtube_url_callback=None,
                               extract_video_id_callback=None):
    """Handle inline queries."""
    user_id = update.inline_query.from_user.id
    if not await is_user_authorized(user_id):
        await update.inline_query.answer([], button=InlineQueryResultsButton(text="Authorization required", start_parameter="auth"))
        return

    query = update.inline_query.query.strip()
    if is_valid_youtube_url_callback and is_valid_youtube_url_callback(query):
        if extract_video_id_callback:
            video_id = extract_video_id_callback(query)
            results = [InlineQueryResultArticle(
                id=f"download_{video_id}", title="Download video",
                input_message_content=InputTextMessageContent(f"Downloading: {query}"),
                button=InlineQueryResultsButton(text="Select quality in bot", start_parameter=f"download_{video_id}")
            )]
            await update.inline_query.answer(results, cache_time=60)
