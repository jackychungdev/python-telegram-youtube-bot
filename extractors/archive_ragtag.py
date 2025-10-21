import os
import subprocess
import tempfile
import logging
import yt_dlp
from urllib.parse import urlparse

def download_and_merge(url, video_id, temp_dir, progress_hook=None):
    """
    Скачивает видео и аудио с archive.ragtag.moe и объединяет их в один mp4 файл.
    Возвращает путь к итоговому файлу и информацию о видео.
    """
    # Настройки для yt-dlp
    ydl_opts = {
        'outtmpl': os.path.join(temp_dir, f"video_{video_id}.%(id)s.%(ext)s"),
        'quiet': False,
        'no_warnings': False,
        'verbose': True,
        'merge_output_format': None,  # Отключаем автоматическое слияние в yt-dlp
        'keepvideo': True,  # Сохраняем промежуточные файлы
    }
    if progress_hook:
        ydl_opts['progress_hooks'] = [progress_hook]  # Добавляем прогресс-хук

    # Скачиваем с yt-dlp
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if info is None:
            raise yt_dlp.utils.DownloadError("Не удалось получить информацию о видео")

    # Ищем скачанные файлы
    video_file = None
    audio_file = None
    for file in os.listdir(temp_dir):
        if file.startswith(f"video_{video_id}") and file.endswith('.mp4'):
            video_file = os.path.join(temp_dir, file)
        elif file.startswith(f"video_{video_id}") and file.endswith('.webm'):
            audio_file = os.path.join(temp_dir, file)

    if not video_file or not audio_file:
        raise FileNotFoundError(f"Не удалось найти видео ({video_file}) или аудио ({audio_file}) после скачивания")

    # Объединяем через ffmpeg
    output_file = os.path.join(temp_dir, f"video_{video_id}_merged.mp4")
    ffmpeg_cmd = [
        'ffmpeg', '-y',
        '-i', video_file,
        '-i', audio_file,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-map', '0:v:0',
        '-map', '1:a:0',
        output_file
    ]

    try:
        result = subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
        logging.info(f"FFmpeg output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Ошибка FFmpeg: {e.stderr}")
        raise RuntimeError(f"Не удалось объединить файлы: {e.stderr}")

    if not os.path.exists(output_file):
        raise FileNotFoundError(f"Итоговый файл {output_file} не был создан")

    # Удаляем промежуточные файлы
    os.remove(video_file)
    os.remove(audio_file)

    return output_file, info

def is_archive_ragtag_url(url):
    """Проверяет, является ли URL ссылкой на archive.ragtag.moe."""
    parsed_url = urlparse(url)
    return parsed_url.netloc in ['archive.ragtag.moe', 'www.archive.ragtag.moe']