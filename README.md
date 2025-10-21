## 📁 `telegram_youtube_bot` README

This document provides an overview, setup instructions, and usage guide for the `telegram_youtube_bot`.

## 🇬🇧 English

### 1\. Project Overview

The **Telegram YouTube Bot** is an asynchronous Telegram bot written in Python that allows users to download videos and audio from YouTube and other supported platforms (like `archive.ragtag.moe`, as indicated in the source code). It leverages **`yt-dlp`** for media fetching, **`ffmpeg`** for media processing (merging video/audio streams and extracting metadata), and **`python-telegram-bot`** for Telegram interaction.

### 2\. Key Features

  * **Asynchronous Processing:** Uses `asyncio` and `aiosqlite` for efficient concurrent handling of multiple user requests.
  * **Quality Selection:** Offers a menu to select the desired video quality (up to 2160p) or download as audio.
  * **Download Queue:** Implements a global download queue and a semaphore (`DOWNLOAD_SEMAPHORE`) to limit concurrent downloads, preventing resource exhaustion.
  * **Progress Updates:** Provides real-time download progress to the user.
  * **File Caching:** Caches uploaded videos (by `video_id` and `quality`) to Telegram, significantly reducing bandwidth and download time for repeat requests.
  * **Authorization System:** Includes an authorization mechanism where new users must be approved by the admin before using the download functionality.
  * **Language Preference:** Allows users to set a default language for the audio track selection.
  * **Local Bot API Support:** Configured to use a local Telegram Bot API server for potentially faster and more reliable file uploads (`LOCAL_API_URL = 'http://localhost:8081/bot'`).

### 3\. System Dependencies (Required for the Script)

Before running the Python script, the following external system dependencies must be installed and accessible in your system's PATH:

1.  **FFmpeg:**
      * **Purpose:** Essential for merging separately downloaded video and audio streams (`yt-dlp` often requires this for high-quality downloads) and for extracting media metadata (duration, resolution).
      * **Installation:** Download and install FFmpeg from their official website. Ensure the `ffmpeg` executable is in your system's PATH.
2.  **yt-dlp:**
      * **Purpose:** The core tool for fetching video information and downloading media from various sites.
      * **Installation:** Usually installed via `pip`, but the script uses it as a Python module (`import yt_dlp`).

### 4\. Python Dependencies

The following Python packages are required and can be installed using `pip`:

```bash
pip install python-telegram-bot httpx yt-dlp aiosqlite Pillow aiocache ffmpeg-python
```

### 5\. Configuration

Modify the following constants at the beginning of the `telegram_youtube_bot.py` script:

| Constant | Description | Example Value |
| :--- | :--- | :--- |
| `TOKEN` | Your Telegram Bot Token. | `'YOUR_BOT_TOKEN'` |
| `LOCAL_API_URL` | URL of your local Telegram Bot API server (or leave as is if you run one). | `'http://localhost:8081/bot'` |
| `ADMIN_CHAT_ID` | Your Telegram User ID. This user receives authorization requests and logs. | `123456789` |
| `ALLOWED_CHATS` | A set of allowed group/channel IDs if the bot is used outside of private chat. | `{-1001234567890}` |
| `DOWNLOAD_SEMAPHORE` | Controls the maximum number of simultaneous downloads. | `asyncio.Semaphore(5)` |

### 6\. Usage

#### 6.1. Running the Bot

1.  Ensure all system and Python dependencies are installed.

2.  Configure the constants in the script.

3.  Run the script:

    ```bash
    python telegram_youtube_bot.py
    ```

#### 6.2. In Telegram

1.  **Start:** Send the `/start` command to the bot.
2.  **Language Selection:** The bot will prompt you to set your default language preference for audio tracks.
3.  **Authorization:** If you are not the `ADMIN_CHAT_ID`, you'll be prompted to wait for the admin's authorization.
4.  **Download:**
      * **Method 1 (Direct Link):** Send a valid video link (e.g., from YouTube) directly to the bot.
      * **Method 2 (Command):** Use `/download <link>`.
5.  **Select Quality:** The bot will display a list of available resolutions or an "Audio" option. Select the desired format to start the download.

-----

## 🇷🇺 Русский

### 1\. Обзор Проекта

**Telegram YouTube Bot** — это асинхронный Telegram-бот, написанный на Python, который позволяет пользователям скачивать видео и аудио с YouTube и других поддерживаемых платформ (например, `archive.ragtag.moe`, как указано в коде). Бот использует **`yt-dlp`** для получения медиа, **`ffmpeg`** для обработки медиа (объединения видео/аудио потоков и извлечения метаданных) и библиотеку **`python-telegram-bot`** для взаимодействия с Telegram.

### 2\. Ключевые Возможности

  * **Асинхронная Обработка:** Использует `asyncio` и `aiosqlite` для эффективной одновременной обработки множества запросов пользователей.
  * **Выбор Качества:** Предоставляет меню для выбора желаемого качества видео (до 2160p) или скачивания только аудиодорожки.
  * **Очередь Загрузок:** Реализована глобальная очередь загрузок и семафор (`DOWNLOAD_SEMAPHORE`) для ограничения одновременных загрузок, предотвращая перегрузку ресурсов.
  * **Обновление Прогресса:** Отображает пользователю прогресс скачивания в реальном времени.
  * **Кэширование Файлов:** Кэширует загруженные видео (по `video_id` и `quality`) в Telegram, значительно сокращая трафик и время при повторных запросах.
  * **Система Авторизации:** Включает механизм авторизации, при котором новые пользователи должны быть одобрены администратором перед использованием функционала скачивания.
  * **Настройка Языка:** Пользователь может установить предпочтительный язык по умолчанию для аудиодорожки.
  * **Поддержка Локального API:** Настроен на использование локального сервера Telegram Bot API для потенциально более быстрой и надёжной загрузки файлов (`LOCAL_API_URL = 'http://localhost:8081/bot'`).

### 3\. Системные Зависимости (Необходимы для работы скрипта)

Перед запуском Python-скрипта необходимо установить и обеспечить доступность в системном PATH следующим внешним системным зависимостям:

1.  **FFmpeg:**
      * **Назначение:** Критически важен для объединения раздельно скачанных видео- и аудиопотоков (`yt-dlp` часто требует этого для высокого качества) и для извлечения метаданных медиа (длительность, разрешение).
      * **Установка:** Скачайте и установите FFmpeg с их официального сайта. Убедитесь, что исполняемый файл `ffmpeg` находится в вашем системном PATH.
2.  **yt-dlp:**
      * **Назначение:** Основной инструмент для получения информации о видео и скачивания медиа с различных сайтов.
      * **Установка:** Обычно устанавливается через `pip`, но скрипт использует его как Python-модуль (`import yt_dlp`).

### 4\. Python Зависимости

Требуются следующие Python-пакеты, которые можно установить с помощью `pip`:

```bash
pip install python-telegram-bot httpx yt-dlp aiosqlite Pillow aiocache ffmpeg-python
```

### 5\. Конфигурация

Необходимо изменить следующие константы в начале файла `telegram_youtube_bot.py`:

| Константа | Описание | Пример Значения |
| :--- | :--- | :--- |
| `TOKEN` | Ваш токен Telegram-бота. | `'ВАШ_ТОКЕН_БОТА'` |
| `LOCAL_API_URL` | URL вашего локального сервера Telegram Bot API (или оставьте как есть, если вы его запускаете). | `'http://localhost:8081/bot'` |
| `ADMIN_CHAT_ID` | Ваш ID пользователя Telegram. Этот пользователь получает запросы на авторизацию и уведомления о загрузках. | `123456789` |
| `ALLOWED_CHATS` | Набор разрешенных ID групп/каналов, если бот используется вне личного чата. | `{-1001234567890}` |
| `DOWNLOAD_SEMAPHORE` | Контролирует максимальное количество одновременных загрузок. | `asyncio.Semaphore(5)` |

### 6\. Использование

#### 6.1. Запуск Бота

1.  Убедитесь, что все системные и Python-зависимости установлены.

2.  Сконфигурируйте константы в скрипте.

3.  Запустите скрипт:

    ```bash
    python telegram_youtube_bot.py
    ```

#### 6.2. В Telegram

1.  **Старт:** Отправьте боту команду `/start`.
2.  **Выбор Языка:** Бот предложит вам установить язык по умолчанию для аудиодорожек.
3.  **Авторизация:** Если вы не являетесь `ADMIN_CHAT_ID`, вам нужно будет дождаться авторизации от администратора.
4.  **Скачивание:**
      * **Метод 1 (Прямая Ссылка):** Отправьте боту действительную ссылку на видео (например, с YouTube).
      * **Метод 2 (Команда):** Используйте `/download <ссылка>`.
5.  **Выбор Качества:** Бот отобразит список доступных разрешений или опцию "Audio". Выберите нужный формат для начала загрузки.