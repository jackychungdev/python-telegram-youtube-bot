"""
Download Manager Module

This module handles all YouTube download operations for the Telegram bot.
It provides functionality for:
- Downloading videos/audio from YouTube and other supported sites
- Managing download queue and progress tracking
- Extracting video information and available formats
- Processing downloads with quality selection

Usage:
    The module requires initialization with required global variables and callbacks.
    
Author: Python Telegram YouTube Bot
Created: 2026-03-22
"""

import os
import re
import asyncio
import logging
import tempfile
import shutil
from datetime import datetime
from urllib.parse import urlparse
import yt_dlp
from yt_dlp.utils import DownloadError

logger = logging.getLogger(__name__)

# Global variables (will be initialized by init_download_module)
DOWNLOAD_SEMAPHORE = None
OUTPUT_FOLDER = None
KEEP_FILES = None
COOKIE_FILE = None
QUALITY_FORMATS = None
BASE_YTDL_OPTS = None
downloads = {}
active_downloads = {}

def init_download_module(download_semaphore, output_folder, keep_files, cookie_file, 
                        quality_formats, base_ytdl_opts):
    """Initialize the download module with required configuration."""
    global DOWNLOAD_SEMAPHORE, OUTPUT_FOLDER, KEEP_FILES, COOKIE_FILE
    global QUALITY_FORMATS, BASE_YTDL_OPTS
    DOWNLOAD_SEMAPHORE = download_semaphore
    OUTPUT_FOLDER = output_folder
    KEEP_FILES = keep_files
    COOKIE_FILE = cookie_file
    QUALITY_FORMATS = quality_formats
    BASE_YTDL_OPTS = base_ytdl_opts

def extract_video_id(url):
    """Extract video ID from YouTube URL."""
    patterns = [
        r'(?:v=|\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def is_valid_youtube_url(url):
    """Validate YouTube URL."""
    ALLOWED_DOMAINS = [
        'youtube.com', 'www.youtube.com',
        'youtu.be', 'www.youtu.be',
        'youtube-nocookie.com', 'www.youtube-nocookie.com',
        'archive.ragtag.moe', 'www.archive.ragtag.moe'
    ]
    parsed = urlparse(url)
    return parsed.scheme in ('http', 'https') and parsed.netloc in ALLOWED_DOMAINS

def download_progress_hook(d, context):
    """Progress hook for yt-dlp downloads."""
    chat_id = context.bot_data.get('download_info', {}).get('chat_id')
    message_id = context.bot_data.get('download_info', {}).get('message_id')
    if not chat_id or not message_id:
        return
    
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        if total > 0:
            percent = int(d['downloaded_bytes'] / total * 100)
            text = f"Downloading: {percent}%..."
            downloads[chat_id] = {'percent': percent, 'text': text}
    elif d['status'] == 'finished':
        downloads[chat_id] = {'percent': 100, 'text': 'Download complete, processing...'}

async def update_progress_task(context, chat_id: int, message_id: int):
    """Update progress message during download."""
    while context.bot_data.get('download_info', {}).get('is_downloading', False):
        data = downloads.get(chat_id, {})
        if 'text' in data and data.get('last_percent', -1) != data['percent']:
            try:
                await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=data['text'])
                data['last_percent'] = data['percent']
            except Exception as e:
                pass
        await asyncio.sleep(2)

async def get_available_qualities(url, cookie_file=None):
    """Get available video qualities from URL."""
    ydl_opts = {'quiet': True, 'force_ipv4': True}
    if cookie_file:
        ydl_opts['cookiefile'] = cookie_file
    
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=False)
        formats = info.get('formats', [])
    except Exception as e:
        raise Exception(f"Failed to get video information: {e}")

    available_qualities = set()
    for f in formats:
        if f.get('vcodec') != 'none' and f.get('height'):
            height = f.get('height')
            if height >= 2160:
                available_qualities.add('2160')
            elif height >= 1440:
                available_qualities.add('1440')
            elif height >= 1080:
                available_qualities.add('1080')
            elif height >= 720:
                available_qualities.add('720')
            elif height >= 480:
                available_qualities.add('480')
            elif height >= 360:
                available_qualities.add('360')
            elif height >= 240:
                available_qualities.add('240')
            elif height >= 144:
                available_qualities.add('144')
    
    has_audio = any(f.get('acodec') != 'none' for f in formats)
    
    return available_qualities, has_audio

async def execute_download(application, chat_id, user_id, username, url, quality, video_id, 
                          progress_message_id, start_message_id=None,
                          get_cached_file_id_callback=None, save_file_id_callback=None,
                          send_file_with_progress_callback=None, download_thumbnail_callback=None,
                          get_media_metadata_callback=None, get_user_language_callback=None,
                          update_user_callback=None, admin_chat_id=None):
    """Execute the actual download process."""
    # Import callbacks from main module
    from file_uploader import get_cached_file_id, save_file_id, send_file_with_progress, \
                             download_thumbnail, get_media_metadata
    
    if update_user_callback:
        await update_user_callback(user_id, username, url, increment_download=True)

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
                except Exception:
                    pass
            return
        except Exception as e:
            logger.warning(f"Error sending from cache: {e}")

    preferred_lang = await get_user_language_callback(user_id) if get_user_language_callback else None
    lang_preference = [f'lang:{preferred_lang or "en"}']

    active_downloads[chat_id] = user_id
    application.bot_data['download_info'] = {'chat_id': chat_id, 'message_id': progress_message_id, 'is_downloading': True}
    progress_tasks = application.bot_data.get('progress_tasks', {})
    progress_tasks[chat_id] = asyncio.create_task(update_progress_task(application, chat_id, progress_message_id))

    # Create output folder per username
    safe_username = re.sub(r'[^\w\-_]', '_', username or f'user_{user_id}')
    output_dir = os.path.join(OUTPUT_FOLDER, safe_username)
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
            else:
                ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio[ext=webm]'
                ydl_opts['format_sort'] = lang_preference + ['acodec:mp4a.40.2', 'acodec:opus', 'abr']
        else:
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
            user_caption = f"{title} ({quality}p)\nSource: <a href=\"{uploader_url}\">{uploader}</a>"
        else:
            user_caption = f"{title}\nSource: <a href=\"{uploader_url}\">{uploader}</a>"
            
        file_id = await send_file_with_progress(application, chat_id, progress_message_id, filename, 
                                               media_type, title, width, height, duration, thumb, user_caption)
        
        # --- ADMIN NOTIFICATION ---
        if user_id != admin_chat_id:
            quality_text = f"({quality}p)" if quality != 'audio' else "(Audio)"
            
            admin_caption = (
                f"**🚀 NEW DOWNLOAD**\n"
                f"**User:** @{username} (ID: <code>{user_id}</code>)\n\n"
                f"{title} {quality_text}\n"
                f"**Source:** <a href=\"{uploader_url}\">{uploader}</a>"
            )
            
            try:
                if media_type == "audio":
                    await application.bot.send_audio(
                        admin_chat_id, file_id, caption=admin_caption, parse_mode='HTML',
                        duration=int(duration) if duration else None, title=title
                    )
                elif media_type == "video":
                    await application.bot.send_video(
                        admin_chat_id, file_id, caption=admin_caption, parse_mode='HTML',
                        duration=int(duration) if duration else None, width=width, height=height,
                        supports_streaming=True
                    )
            except Exception as e:
                logger.error(f"Error sending media to admin: {e}")

        await save_file_id(video_id, quality, file_id, file_size, title, uploader, info.get('channel_url'))
        await application.bot.delete_message(chat_id, progress_message_id)
        if start_message_id:
            try:
                await application.bot.delete_message(chat_id, start_message_id)
            except Exception as e:
                logger.error(f"Failed to delete start message: {e}")
    
    except Exception as e:
        logger.error(f"Error executing download: {e}", exc_info=True)
        await application.bot.edit_message_text(chat_id, progress_message_id, f'An error occurred: {e}')
        if start_message_id:
            try:
                await application.bot.delete_message(chat_id, start_message_id)
            except Exception:
                pass
    finally:
        if not KEEP_FILES:
            shutil.rmtree(output_dir, ignore_errors=True)
        if chat_id in active_downloads:
            del active_downloads[chat_id]
        if chat_id in progress_tasks:
            progress_tasks[chat_id].cancel()
            del progress_tasks[chat_id]
        if 'download_info' in application.bot_data:
            del application.bot_data['download_info']
