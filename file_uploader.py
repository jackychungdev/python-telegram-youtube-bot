"""
File Uploader Module

This module handles all file upload operations for the Telegram YouTube bot.
It provides functionality for:
- Caching file information in the database
- Sending files (video/audio) to Telegram with progress tracking
- Downloading and processing thumbnails
- Extracting media metadata using ffprobe

Usage:
    The module is initialized by the main bot script which sets up required global variables.
    
Author: Python Telegram YouTube Bot
Created: 2026-03-22
"""

import os
import logging
import httpx
import ffmpeg
from datetime import datetime
from PIL import Image
from io import BytesIO
import aiosqlite
from telegram import Update
from telegram.ext import ContextTypes

# These globals will be set by init_uploader_module() function
LOCAL_API_URL = None
WRITE_TIMEOUT = None
progress_message_ids = {}
progress_tasks = {}

logger = logging.getLogger(__name__)

def init_uploader_module(local_api_url, write_timeout):
    """Initialize the uploader module with required global variables."""
    global LOCAL_API_URL, WRITE_TIMEOUT
    LOCAL_API_URL = local_api_url
    WRITE_TIMEOUT = write_timeout

async def get_cached_file_id(video_id: str, quality: str) -> tuple:
    """Retrieve cached file information from database."""
    async with aiosqlite.connect('users.db') as conn:
        c = await conn.cursor()
        await c.execute('SELECT file_id, title, channel_username, channel_url FROM uploaded_videos WHERE video_id = ? AND quality = ?', (video_id, quality))
        result = await c.fetchone()
        if result:
            return result
        return None, None, None, None

async def save_file_id(video_id: str, quality: str, file_id: str, file_size: int, 
                      title: str = None, channel_username: str = None, 
                      channel_url: str = None):
    """Save file information to database for caching."""
    async with aiosqlite.connect('users.db') as conn:
        upload_date = datetime.now().isoformat()
        await conn.execute('''INSERT OR REPLACE INTO uploaded_videos 
                           (video_id, quality, file_id, upload_date, file_size, title, channel_username, channel_url) 
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                        (video_id, quality, file_id, upload_date, file_size, title, channel_username, channel_url))
        await conn.commit()

def download_thumbnail(url, video_id):
    """Download and save video thumbnail."""
    if not url:
        return None
    try:
        with httpx.Client(verify=True) as client:
            response = client.get(url, timeout=30)
            response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert('RGB')
        path = f"thumbnail_{video_id}.jpg"
        img.save(path, 'JPEG')
        return path
    except Exception as e:
        logger.error(f"Error downloading thumbnail: {e}")
        return None

def get_media_metadata(file_path):
    """Extract media metadata using ffprobe."""
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
        logger.error(f"Error getting metadata: {e}")
        return None, None, None, None

async def send_file_with_progress(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, 
                                 filename: str, media_type: str, title: str, 
                                 width=None, height=None, duration=None, 
                                 thumbnail=None, caption=None):
    """Send file to Telegram with progress tracking."""
    url = f"{LOCAL_API_URL}{context.bot.token}/{'sendVideo' if media_type == 'video' else 'sendAudio'}"
    total_size = os.path.getsize(filename)
    logger.info(f"Starting file upload: {filename}, size: {total_size / (1024 * 1024):.2f} MiB")

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
        else:  # Audio
            with open(filename, 'rb') as audio_file:
                thumb = open(thumbnail, 'rb') if thumbnail and os.path.exists(thumbnail) else None
                try:
                    sent_message = await context.bot.send_audio(
                        chat_id=chat_id, audio=audio_file, caption=caption, parse_mode='HTML',
                        duration=int(duration) if duration else None, title=title or 'Unknown Title', thumbnail=thumb)
                    file_id = sent_message.audio.file_id
                finally:
                    if thumb:
                        thumb.close()

        if thumb_file:
            thumb_file.close()
        if thumbnail and os.path.exists(thumbnail):
            os.remove(thumbnail)
        return file_id

    except Exception as e:
        logger.error(f"Ошибка при отправке файла: {e}", exc_info=True)
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"Error: {str(e)}")

async def handle_uploaded_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded media messages from users."""
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
            logger.error(f"Error processing uploaded media: {e}")
