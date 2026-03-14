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
            link TEXT,
            video_url TEXT,
            awaiting_link INTEGER DEFAULT 0,
            download_count INTEGER DEFAULT 0,
            last_download_time INTEGER DEFAULT 0
        )''')
        await conn.commit()
    
    # authorized_users table
    async with aiosqlite.connect('users.db') as conn:
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

async def get_cached_file_id(video_id: str, quality: str) -> tuple:
    async with aiosqlite.connect('users.db') as conn:
        c = await conn.cursor()
        await c.execute('SELECT file_id, title, channel_username, channel_url FROM uploaded_videos WHERE video_id = ? AND quality = ?', (video_id, quality))
        result = await c.fetchone()
        if result:
            return result
        return None, None, None, None

async def save_file_id(video_id: str, quality: str, file_id: str, file_size: int, title: str = None, channel_username: str = None, channel_url: str = None):
    async with aiosqlite.connect('users.db') as conn:
        upload_date = datetime.now().isoformat()
        await conn.execute('''INSERT OR REPLACE INTO uploaded_videos 
                           (video_id, quality, file_id, upload_date, file_size, title, channel_username, channel_url) 
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                        (video_id, quality, file_id, upload_date, file_size, title, channel_username, channel_url))
        await conn.commit()

async def handle_uploaded_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Logic for processing uploaded media (if needed)
    message = update.message
    if not message or (not message.video and not message.audio):
        return
    chat_id = message.chat_id
    if chat_id in progress_message_ids:
        progress_msg_id = progress_message_ids[chat_id]
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=progress_msg_id, text="Upload complete (100%)")
            if chat_id in progress_tasks:
                progress_tasks[chat_id].cancel()
                del progress_tasks[chat_id]
            del progress_message_ids[chat_id]
        except Exception as e:
            logging.error(f"Error processing uploaded media: {e}")

async def send_file_with_progress(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, filename: str, 
                                 media_type: str, title: str, width=None, height=None, duration=None, 
                                 thumbnail=None, caption=None):
    # File sending logic with progress
    url = f"{LOCAL_API_URL}{context.bot.token}/{'sendVideo' if media_type == 'video' else 'sendAudio'}"
    total_size = os.path.getsize(filename)
    logging.info(f"Starting file upload: {filename}, size: {total_size / (1024 * 1024):.2f} MiB")

    files = {}
    thumb_file = None

    try:
        if media_type == 'video':
            with open(filename, 'rb') as f:
                files['video'] = (os.path.basename(filename), f, 'video/mp4')
                
                if thumbnail and os.path.exists(thumbnail):
                    thumb_file = open(thumbnail, 'rb')
                    files['thumb'] = ('thumbnail.jpg', thumb_file, 'image/jpeg')

                data = {'chat_id': chat_id, 'caption': caption, 'parse_mode': 'HTML'}
                if width and height and duration:
                    data.update({'width': width, 'height': height, 'duration': int(duration), 'supports_streaming': 'true'})
                
                async with httpx.AsyncClient(timeout=httpx.Timeout(WRITE_TIMEOUT)) as client:
                    response = await client.post(url, data=data, files=files)
                    response.raise_for_status()
                    message_data = response.json()
                    file_id = message_data['result']['video']['file_id']
        else: # Audio
            with open(filename, 'rb') as audio_file:
                thumb = open(thumbnail, 'rb') if thumbnail and os.path.exists(thumbnail) else None
                try:
                    sent_message = await context.bot.send_audio(
                        chat_id=chat_id, audio=audio_file, caption=caption, parse_mode='HTML',
                        duration=int(duration) if duration else None, title=title or 'Unknown Title', thumbnail=thumb)
                    file_id = sent_message.audio.file_id
                finally:
                    if thumb: thumb.close()

        if thumb_file: thumb_file.close()
        if thumbnail and os.path.exists(thumbnail): os.remove(thumbnail)
        return file_id

    except Exception as e:
        logging.error(f"Ошибка при отправке файла: {e}", exc_info=True)
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"Error: {str(e)}")

async def update_user(user_id, username, video_url=None, awaiting_link=None, increment_download=False):
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
    async with aiosqlite.connect('users.db') as conn:
        c = await conn.cursor()
        await c.execute('SELECT awaiting_link FROM users WHERE user_id = ?', (user_id,))
        result = await c.fetchone()
        return result[0] if result else 0

@cached(ttl=3600)
async def is_user_authorized(user_id):
    async with aiosqlite.connect('authorized_users.db') as conn:
        c = await conn.cursor()
        await c.execute('SELECT user_id FROM authorized_users WHERE user_id = ?', (user_id,))
        return await c.fetchone() is not None

async def add_authorized_user(user_id):
    async with aiosqlite.connect('authorized_users.db') as conn:
        await conn.execute('INSERT OR IGNORE INTO authorized_users (user_id) VALUES (?)', (user_id,))
        await conn.commit()
    await caches.get('default').delete(f"is_user_authorized:{user_id}")

async def remove_authorized_user(user_id):
    async with aiosqlite.connect('authorized_users.db') as conn:
        await conn.execute('DELETE FROM authorized_users WHERE user_id = ?', (user_id,))
        await conn.commit()
    await caches.get('default').delete(f"is_user_authorized:{user_id}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Log /start command
    logging.info(f"🚀 /start command from @{user.username} (ID: {user.id})")
    await update_user(user.id, user.username)
    
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
        await update_user(user.id, user.username, video_url=url, awaiting_link=0)
        context.bot_data.setdefault('pending_downloads', {})[user.id] = {'url': url}
        
        if user.id == ADMIN_CHAT_ID or await is_user_authorized(user.id):
            await process_download(update, context, url, user.id, user.username)
        else:
            await update.message.reply_text('Hello! To use the bot, please wait for authorization from the admin.')
            await request_authorization(update, context, user.id, user.username)
    else:
        text = 'Hello, admin! Send a link.' if user.id == ADMIN_CHAT_ID else 'Hello! Authorization is required to use the bot.'
        await update.message.reply_text(text)

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

def is_valid_youtube_url(url):
    parsed = urlparse(url)
    return parsed.scheme in ('http', 'https') and parsed.netloc in ALLOWED_DOMAINS

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    url = message.text
    
    # Log received messages
    logging.info(f"📨 Message received from @{user.username} (ID: {user.id}): {url}")
    
    if message.chat.type != 'private' and message.chat.id not in ALLOWED_CHATS:
        return

    if not await get_user_language(user.id):
        await update.message.reply_text("Please select your default language first using the /lang command or the button in /start.")
        return

    if not await request_authorization(update, context, user.id, user.username):
        await message.reply_text('Waiting for admin confirmation.')
        return

    if not is_valid_youtube_url(url):
        await message.reply_text('Please send a valid link.')
        return

    await update_user(user.id, user.username, url)
    context.bot_data.setdefault('pending_messages', {})[user.id] = {'link_message_id': message.message_id}
    await process_download(update, context, url, user.id, user.username)

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Select your **default audio language**:",
        reply_markup=select_language_menu(),
        parse_mode='Markdown'
    )

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    
    # Log /download command
    logging.info(f"📥 /download command from @{user.username} (ID: {user.id}), args: {context.args}")

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
    if not is_valid_youtube_url(url):
        await message.reply_text('Please provide a valid link.')
        return

    await update_user(user.id, user.username, url)
    await process_download(update, context, url, user.id, user.username)

async def process_download(update: Update, context: ContextTypes.DEFAULT_TYPE, url, user_id, username):
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

    quality_msg = await message.reply_text('Getting information about available video formats...')
    ydl_opts = {'quiet': True, 'force_ipv4': True}
    if COOKIE_FILE:
        ydl_opts['cookiefile'] = COOKIE_FILE
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=False)
        formats = info.get('formats', [])
    except Exception as e:
        await quality_msg.edit_text(f"Failed to get video information: {e}")
        return

    available_qualities = set()
    for f in formats:
        if f.get('vcodec') != 'none' and f.get('height'):
            height = f.get('height')
            if height >= 2160: available_qualities.add('2160')
            elif height >= 1440: available_qualities.add('1440')
            elif height >= 1080: available_qualities.add('1080')
            elif height >= 720: available_qualities.add('720')
            elif height >= 480: available_qualities.add('480')
            elif height >= 360: available_qualities.add('360')
            elif height >= 240: available_qualities.add('240')
            elif height >= 144: available_qualities.add('144')
    
    has_audio = any(f.get('acodec') != 'none' for f in formats)
    
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

def get_media_metadata(file_path):
    try:
        probe = ffmpeg.probe(file_path)
        video = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        audio = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
        if video:
            return 'video', int(video['width']), int(video['height']), float(video.get('duration', 0))
        if audio:
            duration = float(audio.get('duration', 0)) or float(probe.get('format', {}).get('duration', 0))
            return 'audio', None, None, duration
    except Exception as e:
        logging.error(f"Error getting metadata: {e}")
        return None, None, None, None

def download_thumbnail(url, video_id):
    if not url: return None
    try:
        with httpx.Client(verify=True) as client:
            response = client.get(url, timeout=30)
            response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert('RGB')
        path = f"thumbnail_{video_id}.jpg"
        img.save(path, 'JPEG')
        return path
    except Exception as e:
        logging.error(f"Error downloading thumbnail: {e}")
        return None

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
    await update_user(user_id, username, url, increment_download=True)

    cached_file, title, ch_user, ch_url = await get_cached_file_id(video_id, quality)
    if cached_file:
        caption = f"{title}\nSource: <a href=\"{ch_url}\">{ch_user}</a>"
        try:
            if quality == "audio":
                await application.bot.send_audio(chat_id, cached_file, caption=caption, parse_mode='HTML')
            else:
                await application.bot.send_video(chat_id, cached_file, caption=caption, parse_mode='HTML')
            await application.bot.delete_message(chat_id, progress_message_id)
            if start_message_id:
                try:
                    await application.bot.delete_message(chat_id, start_message_id)
                except Exception: pass
            return
        except Exception as e:
            logging.warning(f"Error sending from cache: {e}")

    preferred_lang = await get_user_language(user_id)
    lang_preference = [f'lang:{preferred_lang or "en"}'] # Default 'en'

    active_downloads[chat_id] = user_id
    application.bot_data['download_info'] = {'chat_id': chat_id, 'message_id': progress_message_id, 'is_downloading': True}
    progress_tasks[chat_id] = asyncio.create_task(update_progress_task(application, chat_id, progress_message_id))

    # Use configured output folder instead of temp directory
    output_dir = OUTPUT_FOLDER if KEEP_FILES else tempfile.mkdtemp()
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        ydl_opts = BASE_YTDL_OPTS.copy()
        ydl_opts.update({
            'outtmpl': os.path.join(output_dir, f"%(upload_date)s - %(uploader)s - %(title)s [{video_id}].%(ext)s"),
            'quiet': True,
            'progress_hooks': [lambda d: download_progress_hook(d, application)],
        })
        if COOKIE_FILE:
            ydl_opts['cookiefile'] = COOKIE_FILE
        
        quality_key = quality if quality != 'audio' else 'audio'
        if quality_key in QUALITY_FORMATS:
            settings = QUALITY_FORMATS[quality_key]
            if quality != "audio":
                ydl_opts['format'] = f'bestvideo[height<={settings["max_height"]}]+bestaudio/best'
                ydl_opts['format_sort'] = lang_preference + settings.get('video_priority', []) + ['height', 'tbr']
            else: # audio
                ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio[ext=webm]'
                ydl_opts['format_sort'] = lang_preference + ['acodec:mp4a.40.2', 'acodec:opus', 'abr']
        else: # Fallback for non-YouTube or other cases
            ydl_opts['format'] = 'bestvideo+bestaudio/best'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            filename = ydl.prepare_filename(info)
        
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File was not created: {filename}")

        # --- Extract metadata ---
        file_size = os.path.getsize(filename)
        media_type, width, height, duration = get_media_metadata(filename)
        thumb = download_thumbnail(info.get('thumbnail'), video_id)
        
        title = info.get('title', 'Untitled')
        uploader = info.get('uploader', 'Unknown')
        uploader_url = info.get('channel_url') or info.get('webpage_url', url)

        # --- Form user caption (with resolution) ---
        if quality != 'audio':
            # Add resolution to title for videos
            user_caption = f"{title} ({quality}p)\nSource: <a href=\"{uploader_url}\">{uploader}</a>"
        else:
            # For audio only title and source
            user_caption = f"{title}\nSource: <a href=\"{uploader_url}\">{uploader}</a>"
            
        file_id = await send_file_with_progress(application, chat_id, progress_message_id, filename, media_type, title, width, height, duration, thumb, user_caption)
        
        # --- ADMIN NOTIFICATION ---
        if user_id != ADMIN_CHAT_ID:
            quality_text = f"({quality}p)" if quality != 'audio' else "(Audio)"
            
            admin_caption = (
                f"**🚀 NEW DOWNLOAD**\n"
                f"**User:** @{username} (ID: <code>{user_id}</code>)\n\n"
                f"{title} {quality_text}\n"
                f"**Source:** <a href=\"{uploader_url}\">{uploader}</a>"
            )
            
            try:
                # Send media file to admin by file_id
                if media_type == "audio":
                    await application.bot.send_audio(
                        ADMIN_CHAT_ID, 
                        file_id, 
                        caption=admin_caption, 
                        parse_mode='HTML', 
                        duration=int(duration) if duration else None, 
                        title=title
                    )
                elif media_type == "video":
                    await application.bot.send_video(
                        ADMIN_CHAT_ID, 
                        file_id, 
                        caption=admin_caption, 
                        parse_mode='HTML', 
                        duration=int(duration) if duration else None, 
                        width=width, 
                        height=height, 
                        supports_streaming=True
                    )
            except Exception as e:
                logging.error(f"Error sending media to admin: {e}")
        # --- END ADMIN NOTIFICATION ---

        await save_file_id(video_id, quality, file_id, file_size, title, uploader, info.get('channel_url'))
        logging.info(f"Deleting progress message {progress_message_id} for chat {chat_id}")
        await application.bot.delete_message(chat_id, progress_message_id)
        if start_message_id:
            logging.info(f"Deleting start message {start_message_id} for chat {chat_id}")
            try:
                await application.bot.delete_message(chat_id, start_message_id)
            except Exception as e:
                logging.error(f"Failed to delete start message: {e}")
    
    except Exception as e:
        logging.error(f"Error executing download: {e}", exc_info=True)
        await application.bot.edit_message_text(chat_id, progress_message_id, f'An error occurred: {e}')
        if start_message_id:
            try:
                await application.bot.delete_message(chat_id, start_message_id)
            except Exception: pass
    finally:
        # Clean up temp directory only if KEEP_FILES is False
        if not KEEP_FILES:
            shutil.rmtree(output_dir, ignore_errors=True)
        if chat_id in active_downloads: del active_downloads[chat_id]
        if chat_id in progress_tasks:
            progress_tasks[chat_id].cancel()
            del progress_tasks[chat_id]
        if 'download_info' in application.bot_data: del application.bot_data['download_info']

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
    query = update.callback_query
    await query.answer()
    
    action, user_id_str = query.data.split('_', 1)
    user_id = int(user_id_str)
    
    if query.from_user.id != ADMIN_CHAT_ID: return
    
    if action == 'allow':
        await add_authorized_user(user_id)
        await context.bot.send_message(user_id, 'The admin has allowed you to use the bot!')
        await query.edit_message_text(f'Access for ID {user_id} granted.')
    elif action == 'deny':
        await remove_authorized_user(user_id)
        await context.bot.send_message(user_id, 'The admin has denied your access to the bot.')
        await query.edit_message_text(f'Access for ID {user_id} denied.')

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.inline_query.from_user.id
    if not await is_user_authorized(user_id):
        await update.inline_query.answer([], button=InlineQueryResultsButton(text="Authorization required", start_parameter="auth"))
        return

    query = update.inline_query.query.strip()
    if is_valid_youtube_url(query):
        video_id = extract_video_id(query)
        results = [InlineQueryResultArticle(
            id=f"download_{video_id}", title="Download video",
            input_message_content=InputTextMessageContent(f"Downloading: {query}"),
            button=InlineQueryResultsButton(text="Select quality in bot", start_parameter=f"download_{video_id}")
        )]
        await update.inline_query.answer(results, cache_time=60)

async def post_init(application: Application):
    """Starts background tasks after the event loop has been created."""
    await init_db()
    init_uploaded_videos_db()
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