import os
import re
import sqlite3
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

# --- Глобальная очередь для всех загрузок ---
download_queue = asyncio.Queue()

# Глобальные переменные
progress_message_ids = {}
progress_tasks = {}
downloads = {}
active_downloads = {}
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(5)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Константы
TOKEN = ''
LOCAL_API_URL = 'http://localhost:8081/bot'
ADMIN_CHAT_ID = 
ALLOWED_CHATS = {}
READ_TIMEOUT = 1800
WRITE_TIMEOUT = 1800
TEST_MODE = False
DOWNLOAD_LIMIT_PER_HOUR = 3
LOG_FILE = "telegram_youtube_bot_err.log"
MAX_LOG_SIZE = 1 * 1024 * 1024

# --- Доступные языки ---
AVAILABLE_LANGUAGES = [
    {'code': 'ru', 'name': 'Русский', 'flag': '🇷🇺'},
    {'code': 'en', 'name': 'English', 'flag': '🇬🇧'},
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

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Таблица users
    c.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='users' ''')
    table_exists = c.fetchone()[0] == 1
    if not table_exists:
        c.execute('''CREATE TABLE users 
                     (user_id INTEGER PRIMARY KEY, username TEXT, last_video_url TEXT, 
                      last_online TEXT, awaiting_link INTEGER DEFAULT 0, 
                      downloads_in_hour INTEGER DEFAULT 0, last_download_time TEXT)''')
    else:
        c.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in c.fetchall()]
        if 'downloads_in_hour' not in columns:
            c.execute('ALTER TABLE users ADD COLUMN downloads_in_hour INTEGER DEFAULT 0')
        if 'last_download_time' not in columns:
            c.execute('ALTER TABLE users ADD COLUMN last_download_time TEXT')

    # Таблица authorized_users
    conn_auth = sqlite3.connect('authorized_users.db')
    c_auth = conn_auth.cursor()
    c_auth.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='authorized_users' ''')
    table_exists = c_auth.fetchone()[0] == 1
    if not table_exists:
        c_auth.execute('''CREATE TABLE authorized_users 
                     (user_id INTEGER PRIMARY KEY)''')
    conn_auth.commit()
    conn_auth.close()

    # Таблица user_languages
    c.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='user_languages' ''')
    table_exists = c.fetchone()[0] == 1
    if not table_exists:
        c.execute('''CREATE TABLE user_languages 
                     (user_id INTEGER PRIMARY KEY, language_code TEXT DEFAULT 'ru')''')
        logging.info("Таблица user_languages создана")
    
    conn.commit()
    conn.close()

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
    """Получает сохраненный язык пользователя."""
    async with aiosqlite.connect('users.db') as conn:
        c = await conn.cursor()
        await c.execute('SELECT language_code FROM user_languages WHERE user_id = ?', (user_id,))
        result = await c.fetchone()
        return result[0] if result else None

async def set_user_language(user_id: int, lang_code: str):
    """Сохраняет выбранный язык пользователя."""
    async with aiosqlite.connect('users.db') as conn:
        await conn.execute('''INSERT OR REPLACE INTO user_languages 
                           (user_id, language_code) VALUES (?, ?)''', 
                        (user_id, lang_code))
        await conn.commit()

def select_language_menu():
    """Генерирует InlineKeyboardMarkup для выбора языка."""
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
    # Логика обработки загруженного медиа (если нужно)
    message = update.message
    if not message or (not message.video and not message.audio):
        return
    chat_id = message.chat_id
    if chat_id in progress_message_ids:
        progress_msg_id = progress_message_ids[chat_id]
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=progress_msg_id, text="Отправка завершена (100%)")
            if chat_id in progress_tasks:
                progress_tasks[chat_id].cancel()
                del progress_tasks[chat_id]
            del progress_message_ids[chat_id]
        except Exception as e:
            logging.error(f"Ошибка обработки загруженного медиа: {e}")

async def send_file_with_progress(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, filename: str, 
                                 media_type: str, title: str, width=None, height=None, duration=None, 
                                 thumbnail=None, caption=None):
    # Логика отправки файла с прогрессом
    url = f"{LOCAL_API_URL}{context.bot.token}/{'sendVideo' if media_type == 'video' else 'sendAudio'}"
    total_size = os.path.getsize(filename)
    logging.info(f"Начинаем отправку файла: {filename}, размер: {total_size / (1024 * 1024):.2f} MiB")

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
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"Ошибка: {str(e)}")
        raise

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
    await update_user(user.id, user.username)
    
    user_lang = await get_user_language(user.id)
    if not user_lang:
        await update.message.reply_text(
            "Добро пожаловать! Пожалуйста, выберите **язык аудиодорожки по умолчанию**:",
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
            await update.message.reply_text('Привет! Чтобы использовать бота, дождись авторизации от админа.')
            await request_authorization(update, context, user.id, user.username)
    else:
        text = 'Привет, админ! Отправляй ссылку.' if user.id == ADMIN_CHAT_ID else 'Привет! Для использования бота нужна авторизация.'
        await update.message.reply_text(text)

async def request_authorization(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, username):
    if not TEST_MODE and user_id == ADMIN_CHAT_ID:
        await add_authorized_user(user_id)
        return True
    
    if await is_user_authorized(user_id):
        return True
    
    keyboard = [[InlineKeyboardButton("Разрешить", callback_data=f'allow_{user_id}'),
                 InlineKeyboardButton("Запретить", callback_data=f'deny_{user_id}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"Пользователь {username} (ID: {user_id}) хочет использовать бота. Разрешить?",
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
    
    if message.chat.type != 'private' and message.chat.id not in ALLOWED_CHATS:
        return

    if not await get_user_language(user.id):
        await update.message.reply_text("Пожалуйста, сначала выберите язык по умолчанию через команду /lang или нажав кнопку в /start.")
        return

    if not await request_authorization(update, context, user.id, user.username):
        await message.reply_text('Ожидайте подтверждения от админа.')
        return

    if not is_valid_youtube_url(url):
        await message.reply_text('Пожалуйста, отправь валидную ссылку.')
        return

    await update_user(user.id, user.username, url)
    context.bot_data.setdefault('pending_messages', {})[user.id] = {'link_message_id': message.message_id}
    await process_download(update, context, url, user.id, user.username)

async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите **язык аудиодорожки по умолчанию**:",
        reply_markup=select_language_menu(),
        parse_mode='Markdown'
    )

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if not await request_authorization(update, context, user.id, user.username):
        await message.reply_text('Ожидайте подтверждения от админа.')
        return
    
    if not await get_user_language(user.id):
        await update.message.reply_text("Пожалуйста, сначала выберите язык по умолчанию через команду /lang или нажав кнопку в /start.")
        return

    if not context.args:
        await message.reply_text('Пожалуйста, отправьте ссылку на YouTube в следующем сообщении.')
        await update_user(user.id, user.username, awaiting_link=1)
        return
    
    url = context.args[0]
    if not is_valid_youtube_url(url):
        await message.reply_text('Пожалуйста, укажи валидную ссылку.')
        return

    await update_user(user.id, user.username, url)
    await process_download(update, context, url, user.id, user.username)

async def process_download(update: Update, context: ContextTypes.DEFAULT_TYPE, url, user_id, username):
    message = update.effective_message
    video_id = extract_video_id(url)
    if not video_id:
        await message.reply_text('Ошибка: не удалось извлечь ID видео из ссылки.')
        return

    context.bot_data.setdefault('pending_downloads', {})[user_id] = {'url': url}
    
    parsed_url = urlparse(url)
    if parsed_url.netloc not in YOUTUBE_DOMAINS:
        keyboard = [[InlineKeyboardButton("Начать скачивание", callback_data=f'download|{video_id}|{user_id}')]]
        await message.reply_text(f'Видео с {parsed_url.netloc}: нажмите, чтобы скачать.', reply_markup=InlineKeyboardMarkup(keyboard))
        return

    quality_msg = await message.reply_text('Получаем информацию о доступных форматах видео...')
    ydl_opts = {'quiet': True, 'force_ipv4': True, 'cookiefile': (r'C:\Soft\!!python_scripts\cookies.txt')}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=False)
        formats = info.get('formats', [])
    except Exception as e:
        await quality_msg.edit_text(f"Не удалось получить информацию о видео: {e}")
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
        await quality_msg.edit_text("Для этого видео не найдено доступных форматов для скачивания.")
        return
        
    await quality_msg.edit_text('Выберите качество видео или аудио:', reply_markup=InlineKeyboardMarkup(keyboard))

def download_progress_hook(d, context):
    chat_id = context.bot_data.get('download_info', {}).get('chat_id')
    message_id = context.bot_data.get('download_info', {}).get('message_id')
    if not chat_id or not message_id: return
    
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        if total > 0:
            percent = int(d['downloaded_bytes'] / total * 100)
            text = f"Скачивание: {percent}%..."
            downloads[chat_id] = {'percent': percent, 'text': text}
    elif d['status'] == 'finished':
        downloads[chat_id] = {'percent': 100, 'text': 'Скачивание завершено, обработка...'}

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
        logging.error(f"Ошибка получения метаданных: {e}")
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
        logging.error(f"Ошибка скачивания миниатюры: {e}")
        return None

async def update_progress_task(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    while context.bot_data.get('download_info', {}).get('is_downloading', False):
        data = downloads.get(chat_id, {})
        if 'text' in data and data.get('last_percent', -1) != data['percent']:
            try:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=data['text'])
                data['last_percent'] = data['percent']
            except Exception: pass
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
        await query.message.reply_text("Эта кнопка для другого пользователя.")
        return

    url = context.bot_data.get('pending_downloads', {}).get(user_id, {}).get('url') or f"https://youtu.be/{video_id}"
    await download_queue.put((query.message.chat_id, user_id, query.from_user.username, url, quality, video_id, query.message.message_id))
    
    await query.edit_message_text(
        text=f"✅ Запрос принят. Позиция в очереди: **{download_queue.qsize()}**.",
        reply_markup=None,
        parse_mode='Markdown'
    )

async def _execute_download(application: Application, chat_id, user_id, username, url, quality, video_id, progress_message_id):
    await update_user(user_id, username, url, increment_download=True)

    cached_file, title, ch_user, ch_url = await get_cached_file_id(video_id, quality)
    if cached_file:
        caption = f"{title}\nИсточник: <a href=\"{ch_url}\">{ch_user}</a>"
        try:
            if quality == "audio":
                await application.bot.send_audio(chat_id, cached_file, caption=caption, parse_mode='HTML')
            else:
                await application.bot.send_video(chat_id, cached_file, caption=caption, parse_mode='HTML')
            await application.bot.delete_message(chat_id, progress_message_id)
            return
        except Exception as e:
            logging.warning(f"Ошибка отправки из кэша: {e}")

    preferred_lang = await get_user_language(user_id)
    lang_preference = [f'lang:{preferred_lang or "ru"}'] # По умолчанию 'ru'

    active_downloads[chat_id] = user_id
    application.bot_data['download_info'] = {'chat_id': chat_id, 'message_id': progress_message_id, 'is_downloading': True}
    progress_tasks[chat_id] = asyncio.create_task(update_progress_task(application, chat_id, progress_message_id))

    temp_dir = tempfile.mkdtemp()
    try:
        ydl_opts = BASE_YTDL_OPTS.copy()
        ydl_opts.update({
            'outtmpl': os.path.join(temp_dir, f"video_{video_id}.%(ext)s"),
            'quiet': True,
            'progress_hooks': [lambda d: download_progress_hook(d, application)],
            'cookiefile': (r'C:\Soft\!!python_scripts\cookies.txt'),
        })
        
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
            raise FileNotFoundError(f"Файл не был создан: {filename}")

        # --- Извлечение метаданных ---
        file_size = os.path.getsize(filename)
        media_type, width, height, duration = get_media_metadata(filename)
        thumb = download_thumbnail(info.get('thumbnail'), video_id)
        
        title = info.get('title', 'Без названия')
        uploader = info.get('uploader', 'Неизвестно')
        uploader_url = info.get('channel_url') or info.get('webpage_url', url)

        # --- Формирование подписи для пользователя (с разрешением) ---
        if quality != 'audio':
            # Добавляем разрешение к названию для видео
            user_caption = f"{title} ({quality}p)\nИсточник: <a href=\"{uploader_url}\">{uploader}</a>"
        else:
            # Для аудио только название и источник
            user_caption = f"{title}\nИсточник: <a href=\"{uploader_url}\">{uploader}</a>"
            
        file_id = await send_file_with_progress(application, chat_id, progress_message_id, filename, media_type, title, width, height, duration, thumb, user_caption)
        
        # --- УВЕДОМЛЕНИЕ АДМИНА ---
        if user_id != ADMIN_CHAT_ID:
            quality_text = f"({quality}p)" if quality != 'audio' else "(Audio)"
            
            admin_caption = (
                f"**🚀 НОВАЯ ЗАГРУЗКА**\n"
                f"**Пользователь:** @{username} (ID: <code>{user_id}</code>)\n\n"
                f"{title} {quality_text}\n"
                f"**Источник:** <a href=\"{uploader_url}\">{uploader}</a>"
            )
            
            try:
                # Отправка медиафайла админу по file_id
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
                logging.error(f"Ошибка отправки медиа админу: {e}")
        # --- КОНЕЦ УВЕДОМЛЕНИЯ АДМИНА ---

        await save_file_id(video_id, quality, file_id, file_size, title, uploader, info.get('channel_url'))
        await application.bot.delete_message(chat_id, progress_message_id)
    
    except Exception as e:
        logging.error(f"Ошибка при выполнении загрузки: {e}", exc_info=True)
        await application.bot.edit_message_text(chat_id, progress_message_id, f'Произошла ошибка: {e}')
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        if chat_id in active_downloads: del active_downloads[chat_id]
        if chat_id in progress_tasks:
            progress_tasks[chat_id].cancel()
            del progress_tasks[chat_id]
        if 'download_info' in application.bot_data: del application.bot_data['download_info']

async def queue_processor(application: Application):
    logging.info("Обработчик очереди запущен.")
    while True:
        try:
            chat_id, user_id, username, url, quality, video_id, original_msg_id = await download_queue.get()
            
            async with DOWNLOAD_SEMAPHORE:
                logging.info(f"Начинаем обработку для user_id={user_id}. В очереди: {download_queue.qsize()}")
                await application.bot.send_message(chat_id, "⏳ Ваша очередь подошла, начинаю загрузку...")
                if original_msg_id:
                    try: await application.bot.delete_message(chat_id, original_msg_id)
                    except Exception: pass

                progress_msg = await application.bot.send_message(chat_id, "Скачивание: 0%")
                
                await _execute_download(application, chat_id, user_id, username, url, quality, video_id, progress_msg.message_id)
            download_queue.task_done()
        except Exception as e:
            logging.error(f"Ошибка в обработчике очереди: {e}", exc_info=True)

async def handle_auth_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action, user_id_str = query.data.split('_', 1)
    user_id = int(user_id_str)
    
    if query.from_user.id != ADMIN_CHAT_ID: return
    
    if action == 'allow':
        await add_authorized_user(user_id)
        await context.bot.send_message(user_id, 'Админ разрешил вам использовать бота!')
        await query.edit_message_text(f'Доступ для ID {user_id} разрешён.')
    elif action == 'deny':
        await remove_authorized_user(user_id)
        await context.bot.send_message(user_id, 'Админ запретил вам использовать бота.')
        await query.edit_message_text(f'Доступ для ID {user_id} запрещён.')

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    lang_code = query.data.split('_')[1]
    user_id = query.from_user.id
    
    if lang_code not in [lang['code'] for lang in AVAILABLE_LANGUAGES]:
        await query.edit_message_text("Неизвестный язык.")
        return

    await set_user_language(user_id, lang_code)
    
    selected_lang_info = next(lang for lang in AVAILABLE_LANGUAGES if lang['code'] == lang_code)
    
    if update.callback_query.message.text.startswith("Добро пожаловать"):
         text = 'Привет, админ! Отправляй ссылку.' if user_id == ADMIN_CHAT_ID else 'Привет! Для использования бота нужна авторизация.'
         await query.edit_message_text(
            text=f"✅ Язык по умолчанию установлен: **{selected_lang_info['flag']} {selected_lang_info['name']}**.\n\n"
                 f"{text}",
            parse_mode='Markdown',
            reply_markup=None
        )
         if user_id != ADMIN_CHAT_ID and not await is_user_authorized(user_id):
             await request_authorization(update, context, user_id, query.from_user.username)
    else:
        await query.edit_message_text(
            text=f"✅ Язык по умолчанию установлен: **{selected_lang_info['flag']} {selected_lang_info['name']}**.\n"
                 "Бот будет стараться выбирать аудиодорожку на этом языке.",
            parse_mode='Markdown',
            reply_markup=None
        )

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.inline_query.from_user.id
    if not await is_user_authorized(user_id):
        await update.inline_query.answer([], button=InlineQueryResultsButton(text="Требуется авторизация", start_parameter="auth"))
        return

    query = update.inline_query.query.strip()
    if is_valid_youtube_url(query):
        video_id = extract_video_id(query)
        results = [InlineQueryResultArticle(
            id=f"download_{video_id}", title="Скачать видео",
            input_message_content=InputTextMessageContent(f"Скачиваю: {query}"),
            button=InlineQueryResultsButton(text="Выбрать качество в боте", start_parameter=f"download_{video_id}")
        )]
        await update.inline_query.answer(results, cache_time=60)

async def post_init(application: Application):
    """Запускает фоновые задачи после того, как event loop был создан."""
    asyncio.create_task(queue_processor(application))

def main():
    setup_cache()
    init_db()
    init_uploaded_videos_db()
    
    application = (
        Application.builder()
        .token(TOKEN)
        .base_url(LOCAL_API_URL)
        .request(HTTPXRequest(connect_timeout=30, read_timeout=1800))
        .post_init(post_init)
        .build()
    )
    
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