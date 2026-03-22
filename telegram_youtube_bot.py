import os
import re
import sqlite3
import yaml
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, InlineQueryHandler
from telegram.ext import filters
from telegram.request import HTTPXRequest
import yt_dlp
from yt_dlp.utils import DownloadError
import asyncio
import ffmpeg
import httpx
from PIL import Image
from io import BytesIO
import aiosqlite
import sys
import tempfile
import shutil
import logging
from telegram import InlineQueryResultsButton
from urllib.parse import urlparse
from aiocache import cached, caches
import subprocess
from extractors.archive_ragtag import download_and_merge, is_archive_ragtag_url
from file_uploader import get_cached_file_id, save_file_id, send_file_with_progress, download_thumbnail, get_media_metadata
from download_manager import (
    init_download_module, extract_video_id, is_valid_youtube_url, 
    get_available_qualities, execute_download
)
from telegram_handlers import (
    init_telegram_module, start_command_handler, handle_link_message, 
    lang_command_handler, download_command_handler, handle_auth_callback,
    handle_language_selection, inline_query_handler, update_user, 
    get_user_language, is_user_authorized
)

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Load configuration from config.yaml
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

config = load_config()

# --- Global queue for all downloads ---
download_queue = asyncio.Queue()

# Global variables
progress_message_ids = {}
progress_tasks = {}
downloads = {}
active_downloads = {}
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(config['download']['DOWNLOAD_SEMAPHORE'])

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Constants from config
TOKEN = config['bot']['TOKEN']
LOCAL_API_URL = config['bot']['LOCAL_API_URL']
ADMIN_CHAT_ID = config['bot']['ADMIN_CHAT_ID']
ALLOWED_CHATS = set(config['bot']['ALLOWED_CHATS'])
READ_TIMEOUT = config['download']['READ_TIMEOUT']
WRITE_TIMEOUT = config['download']['WRITE_TIMEOUT']
TEST_MODE = config['features']['TEST_MODE']
DOWNLOAD_LIMIT_PER_HOUR = config['download']['DOWNLOAD_LIMIT_PER_HOUR']
LOG_FILE = config['logging']['LOG_FILE']
MAX_LOG_SIZE = config['logging']['LOG_MAX_SIZE_MB'] * 1024 * 1024
COOKIE_FILE = config['download'].get('COOKIE_FILE')
OUTPUT_FOLDER = config['download'].get('OUTPUT_FOLDER', './downloads')
KEEP_FILES = config['download'].get('KEEP_FILES', True)

# --- Available languages ---
AVAILABLE_LANGUAGES = [
    {'code': 'en', 'name': 'English', 'flag': '🇺🇸'},
    {'code': 'ru', 'name': 'Russian', 'flag': '🇷🇺'},
    {'code': 'de', 'name': 'Deutsch', 'flag': '🇩🇪'}
]

# --- Available languages ---
AVAILABLE_LANGUAGES = [
    {'code': 'en', 'name': 'English', 'flag': '🇺🇸'},
    {'code': 'ru', 'name': 'Russian', 'flag': '🇷🇺'},
    {'code': 'de', 'name': 'Deutsch', 'flag': '🇩🇪'}
]

QUALITY_FORMATS = {
    '144': {'video_priority': ['avc1', 'vp9', 'av01'], 'max_height': 144},
    '240': {'video_priority': ['avc1', 'vp9', 'av01'], 'max_height': 240},
    '360': {'video_priority': ['avc1', 'vp9', 'av01'], 'max_height': 360},
    '480': {'video_priority': ['avc1', 'vp9', 'av01'], 'max_height': 480},
    '720': {'video_priority': ['avc1', 'vp9', 'av01'], 'max_height': 720},
    '1080': {'video_priority': ['avc1', 'vp9', 'av01'], 'max_height': 1080},
    '1440': {'video_priority': ['avc1', 'vp9', 'av01'], 'max_height': 1440},
    '2160': {'video_priority': ['avc1', 'vp9', 'av01'], 'max_height': 2160},
    'audio': {'extra': '--embed-thumbnail --add-metadata'}
}

BASE_YTDL_OPTS = {
    'force_ipv4': True,
    'nooverwrites': True,
    'concurrent_fragments': 5,
    'outtmpl': '%(upload_date)s - %(uploader)s - %(title)s [%(id)s].%(ext)s',
    'merge_output_format': 'mp4',
    'sponsorblock_remove': 'default',
    'match_filters': {'is_live': False},
    'writethumbnail': True,
}

ALLOWED_DOMAINS = [
    'youtube.com', 'www.youtube.com',
    'youtu.be', 'www.youtu.be',
    'youtube-nocookie.com', 'www.youtube-nocookie.com',
    'archive.ragtag.moe', 'www.archive.ragtag.moe'
]

YOUTUBE_DOMAINS = {
    'youtube.com', 'www.youtube.com',
    'youtu.be', 'www.youtu.be',
    'youtube-nocookie.com', 'www.youtube-nocookie.com'
}

# Initialize file_uploader module with required variables and shared state
from file_uploader import init_uploader_module, progress_message_ids as uploader_progress_msg_ids, progress_tasks as uploader_progress_tasks
init_uploader_module(LOCAL_API_URL, WRITE_TIMEOUT)
# Share global state
import file_uploader
file_uploader.progress_message_ids = progress_message_ids
file_uploader.progress_tasks = progress_tasks

# Initialize download_manager module
init_download_module(
    DOWNLOAD_SEMAPHORE, OUTPUT_FOLDER, KEEP_FILES, COOKIE_FILE,
    QUALITY_FORMATS, BASE_YTDL_OPTS
)

# Initialize telegram_handlers module
init_telegram_module(
    AVAILABLE_LANGUAGES, ADMIN_CHAT_ID, TEST_MODE, ALLOWED_CHATS, DOWNLOAD_LIMIT_PER_HOUR
)

def setup_cache():
    caches.set_config({
        'default': {
            'cache': "aiocache.SimpleMemoryCache",
            'serializer': {'class': "aiocache.serializers.PickleSerializer"},
            'ttl': 3600
        }
    })

def trim_log_file(file_path, max_size):
    if not os.path.exists(file_path):
        return
    
    file_size = os.path.getsize(file_path)
    if file_size <= max_size:
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    target_size = max_size * 0.8
    current_size = 0
    keep_lines = []

    for line in reversed(lines):
        line_size = len(line.encode('utf-8'))
        if current_size + line_size <= target_size:
            keep_lines.append(line)
            current_size += line_size
        else:
            break

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(reversed(keep_lines))

    logging.info(f"Лог-файл обрезан до {os.path.getsize(file_path) / 1024:.2f} KB")

async def init_db():
    # users table
    async with aiosqlite.connect('users.db') as conn:
        await conn.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            last_video_url TEXT,
            last_online TEXT,
            awaiting_link INTEGER DEFAULT 0,
            downloads_in_hour INTEGER DEFAULT 0,
            last_download_time TEXT
        )''')
        
        # Add migration for existing databases - add missing columns if they don't exist
        try:
            await conn.execute('ALTER TABLE users ADD COLUMN last_video_url TEXT')
        except aiosqlite.OperationalError:
            pass  # Column already exists
        
        try:
            await conn.execute('ALTER TABLE users ADD COLUMN last_online TEXT')
        except aiosqlite.OperationalError:
            pass  # Column already exists
            
        try:
            await conn.execute('ALTER TABLE users ADD COLUMN downloads_in_hour INTEGER DEFAULT 0')
        except aiosqlite.OperationalError:
            pass  # Column already exists
            
        try:
            await conn.execute('ALTER TABLE users ADD COLUMN last_download_time TEXT')
        except aiosqlite.OperationalError:
            pass  # Column already exists
            
        await conn.commit()
        logging.info("users table initialized/migrated")
    
    # authorized_users table
    async with aiosqlite.connect('authorized_users.db') as conn:
        await conn.execute('CREATE TABLE IF NOT EXISTS authorized_users (user_id INTEGER PRIMARY KEY)')
        await conn.commit()
    
    # user_languages table
    async with aiosqlite.connect('users.db') as conn:
        await conn.execute('''CREATE TABLE IF NOT EXISTS user_languages (
            user_id INTEGER PRIMARY KEY,
            language_code TEXT
        )''')
        await conn.commit()
        logging.info("user_languages table created")

    # uploaded_videos table
    async with aiosqlite.connect('users.db') as conn:
        await conn.execute('''CREATE TABLE IF NOT EXISTS uploaded_videos (
            video_id TEXT,
            quality TEXT,
            file_id TEXT PRIMARY KEY,
            upload_date TEXT,
            file_size INTEGER,
            title TEXT,
            channel_username TEXT,
            channel_url TEXT
        )''')
        await conn.commit()
        logging.info("uploaded_videos table created with new fields")

def init_uploaded_videos_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute('''SELECT count(name) FROM sqlite_master WHERE type='table' AND name='uploaded_videos' ''')
    table_exists = c.fetchone()[0] == 1
    
    if not table_exists:
        c.execute('''CREATE TABLE uploaded_videos 
                     (video_id TEXT, quality TEXT, file_id TEXT, upload_date TEXT, 
                      file_size INTEGER, title TEXT, channel_username TEXT, channel_url TEXT,
                      PRIMARY KEY (video_id, quality))''')
        logging.info("Таблица uploaded_videos создана с новыми полями")
    else:
        c.execute("PRAGMA table_info(uploaded_videos)")
        columns = [col[1] for col in c.fetchall()]
        if 'title' not in columns:
            c.execute('ALTER TABLE uploaded_videos ADD COLUMN title TEXT')
        if 'channel_username' not in columns:
            c.execute('ALTER TABLE uploaded_videos ADD COLUMN channel_username TEXT')
        if 'channel_url' not in columns:
            c.execute('ALTER TABLE uploaded_videos ADD COLUMN channel_url TEXT')
    
    conn.commit()
    conn.close()

# Import helper functions from modules
from telegram_handlers import (
    get_user_language, set_user_language, select_language_menu, update_user,
    is_awaiting_link, is_user_authorized, add_authorized_user, remove_authorized_user
)
from file_uploader import get_cached_file_id, save_file_id

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - wrapper for telegram_handlers module."""
    await start_command_handler(
        update, context,
        process_download_callback=lambda uid, uname, url=None, upd=None, ctx=None: 
            process_download(upd or update, ctx or context, url, uid, uname) if url else None
    )

async def request_authorization(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, username):
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

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming link messages - wrapper for telegram_handlers module."""
    await handle_link_message(
        update, context,
        is_valid_youtube_url_callback=is_valid_youtube_url,
        process_download_callback=lambda uid, uname, url, upd, ctx: process_download(upd, ctx, url, uid, uname)
    )

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /lang command - wrapper for telegram_handlers module."""
    await lang_command_handler(update, context)

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /download command - wrapper for telegram_handlers module."""
    await download_command_handler(
        update, context,
        is_valid_youtube_url_callback=is_valid_youtube_url,
        process_download_callback=lambda uid, uname, url, upd, ctx: process_download(upd, ctx, url, uid, uname)
    )

async def process_download(update: Update, context: ContextTypes.DEFAULT_TYPE, url, user_id, username):
    """Process download request - uses download_manager module."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    message = update.effective_message
    video_id = extract_video_id(url)
    if not video_id:
        await message.reply_text('Error: Could not extract video ID from the link.')
        return

    context.bot_data.setdefault('pending_downloads', {})[user_id] = {'url': url}
    
    parsed_url = urlparse(url)
    if parsed_url.netloc not in YOUTUBE_DOMAINS:
        keyboard = [[InlineKeyboardButton("Start Download", callback_data=f'download|{video_id}|{user_id}')]]
        await message.reply_text(f'Video from {parsed_url.netloc}: click to download.', reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Use download_manager to get available qualities
    quality_msg = await message.reply_text('Getting information about available video formats...')
    
    try:
        available_qualities, has_audio = await get_available_qualities(url, COOKIE_FILE)
    except Exception as e:
        await quality_msg.edit_text(f"Failed to get video information: {e}")
        return
    
    keyboard = [[InlineKeyboardButton(f"{q}p", callback_data=f'{q}|{video_id}|{user_id}')]
                for q in sorted(list(available_qualities), key=int, reverse=True)]
    if has_audio:
        keyboard.append([InlineKeyboardButton("Audio", callback_data=f'audio|{video_id}|{user_id}')])

    if not keyboard:
        await quality_msg.edit_text("No available formats found for download for this video.")
        return
        
    await quality_msg.edit_text('Select video quality or audio:', reply_markup=InlineKeyboardMarkup(keyboard))

def download_progress_hook(d, context):
    chat_id = context.bot_data.get('download_info', {}).get('chat_id')
    message_id = context.bot_data.get('download_info', {}).get('message_id')
    if not chat_id or not message_id: return
    
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        if total > 0:
            percent = int(d['downloaded_bytes'] / total * 100)
            text = f"Downloading: {percent}%..."
            downloads[chat_id] = {'percent': percent, 'text': text}
    elif d['status'] == 'finished':
        downloads[chat_id] = {'percent': 100, 'text': 'Download complete, processing...'}

async def update_progress_task(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    while context.bot_data.get('download_info', {}).get('is_downloading', False):
        data = downloads.get(chat_id, {})
        if 'text' in data and data.get('last_percent', -1) != data['percent']:
            try:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=data['text'])
                data['last_percent'] = data['percent']
            except Exception as e: pass
        await asyncio.sleep(2)

def extract_video_id(url):
    patterns = [
        r'(?:v=|\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle download button click - wrapper for download_manager."""
    query = update.callback_query
    await query.answer()

    quality, video_id, user_id_str = query.data.split('|')
    user_id = int(user_id_str)
    
    if query.from_user.id != user_id:
        await query.message.reply_text("This button is for another user.")
        return

    url = context.bot_data.get('pending_downloads', {}).get(user_id, {}).get('url') or f"https://youtu.be/{video_id}"
    await download_queue.put((query.message.chat_id, user_id, query.from_user.username, url, quality, video_id, query.message.message_id))
    
    await query.edit_message_text(
        text=f"✅ Request accepted. Queue position: **{download_queue.qsize()}**.",
        reply_markup=None,
        parse_mode='Markdown'
    )

async def _execute_download(application: Application, chat_id, user_id, username, url, quality, video_id, progress_message_id, start_message_id=None):
    """Execute download using download_manager module."""
    await execute_download(
        application, chat_id, user_id, username, url, quality, video_id, 
        progress_message_id, start_message_id,
        get_cached_file_id_callback=get_cached_file_id,
        save_file_id_callback=save_file_id,
        send_file_with_progress_callback=send_file_with_progress,
        download_thumbnail_callback=download_thumbnail,
        get_media_metadata_callback=get_media_metadata,
        get_user_language_callback=get_user_language,
        update_user_callback=update_user,
        admin_chat_id=ADMIN_CHAT_ID
    )

async def queue_processor(application: Application):
    logging.info("Queue processor started.")
    while True:
        try:
            chat_id, user_id, username, url, quality, video_id, original_msg_id = await download_queue.get()
            
            async with DOWNLOAD_SEMAPHORE:
                logging.info(f"Starting processing for user_id={user_id}. Queue: {download_queue.qsize()}")
                start_msg = await application.bot.send_message(chat_id, "⏳ Your turn has come, starting download...")
                if original_msg_id:
                    try: await application.bot.delete_message(chat_id, original_msg_id)
                    except Exception: pass

                progress_msg = await application.bot.send_message(chat_id, "Downloading: 0%")
                
                await _execute_download(application, chat_id, user_id, username, url, quality, video_id, progress_msg.message_id, start_msg.message_id)
            download_queue.task_done()
        except Exception as e:
            logging.error(f"Error in queue processor: {e}", exc_info=True)

async def handle_auth_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle authorization callback - wrapper for telegram_handlers module."""
    await handle_auth_callback(update, context)

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection - wrapper for telegram_handlers module."""
    await handle_language_selection(update, context)

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline query - wrapper for telegram_handlers module."""
    await inline_query_handler(
        update, context,
        is_valid_youtube_url_callback=is_valid_youtube_url,
        extract_video_id_callback=extract_video_id
    )

async def post_init(application: Application):
    """Starts background tasks after the event loop has been created."""
    # Initialize modules that depend on config and application context
    from file_uploader import init_uploader_module
    init_uploader_module(LOCAL_API_URL, WRITE_TIMEOUT)
    
    # Share global state with file_uploader
    import file_uploader
    file_uploader.progress_message_ids = progress_message_ids
    file_uploader.progress_tasks = progress_tasks
    
    # Initialize other modules
    init_download_module(
        DOWNLOAD_SEMAPHORE, OUTPUT_FOLDER, KEEP_FILES, COOKIE_FILE,
        QUALITY_FORMATS, BASE_YTDL_OPTS
    )
    
    init_telegram_module(
        AVAILABLE_LANGUAGES, ADMIN_CHAT_ID, TEST_MODE, ALLOWED_CHATS, DOWNLOAD_LIMIT_PER_HOUR
    )
    
    # Initialize database
    await init_db()
    init_uploaded_videos_db()
    
    # Start queue processor
    asyncio.create_task(queue_processor(application))

def main():
    setup_cache()
    
    application_builder = Application.builder().token(TOKEN).request(HTTPXRequest(connect_timeout=30, read_timeout=1800))
    
    if LOCAL_API_URL:
        application_builder = application_builder.base_url(LOCAL_API_URL)
    
    application = application_builder.post_init(post_init).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("lang", lang_command)) 
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    application.add_handler(CommandHandler("download", download_command))
    application.add_handler(CallbackQueryHandler(download_video, pattern=r'^(?:\w+|download)\|.+\|-?\d+$'))
    application.add_handler(CallbackQueryHandler(handle_auth_callback, pattern=r'^(allow|deny)_-?\d+$'))
    application.add_handler(CallbackQueryHandler(handle_language_selection, pattern=r'^lang_\w+$')) 
    application.add_handler(InlineQueryHandler(inline_query))
    
    application.run_polling()

if __name__ == '__main__':
    main()