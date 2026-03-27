## 📁 `telegram_youtube_bot` - Complete Project Documentation

This document provides comprehensive documentation for the refactored Telegram YouTube Bot project.

---

## 🏗️ Architecture Overview

The project has been **refactored** with a clean, layered architecture following Domain-Driven Design (DDD) principles.

### Layered Architecture

```
┌─────────────────────────────────────────┐
│     PRESENTATION LAYER                  │
│  (Telegram Handlers & Commands)         │
│  → src/application/handlers/            │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│     APPLICATION LAYER                   │
│  (Business Services & Orchestration)    │
│  → src/application/services/            │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│     DOMAIN LAYER                        │
│  (Business Entities & Logic)            │
│  → src/domain/                          │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│     INFRASTRUCTURE LAYER                │
│  (External Services & Persistence)      │
│  → src/infrastructure/                  │
└─────────────────────────────────────────┘
```

### Design Patterns

- **Dependency Injection**: Centralized component management via `container.py`
- **Repository Pattern**: Data access abstraction for users, videos, and authorization
- **Command Pattern**: User operations encapsulated in handler functions
- **State Pattern**: Download task state management with `DownloadStatus` value object
- **Strategy Pattern**: Quality selection strategies for different platforms

---

## 📁 Project Structure

```
python-telegram-youtube-bot/
├── src/                              # Main source code
│   ├── core/                         # Core infrastructure
│   │   ├── config.py                 # Configuration management
│   │   ├── exceptions.py             # Custom exception hierarchy
│   │   ├── logging_config.py         # Logging with rotation
│   │   └── container.py              # Dependency injection container
│   │
│   ├── domain/                       # Business domain layer
│   │   ├── entities/                 # Domain entities
│   │   │   ├── user.py               # User entity
│   │   │   ├── video.py              # Video entity
│   │   │   └── download_task.py      # DownloadTask entity
│   │   ├── value_objects/            # Immutable value objects
│   │   │   ├── video_quality.py      # Quality enum
│   │   │   └── download_status.py    # Status enum
│   │   └── services/                 # Domain service interfaces
│   │
│   ├── application/                  # Application layer
│   │   ├── handlers/                 # Telegram command/callback handlers
│   │   │   ├── commands.py           # /start, /download, /status commands
│   │   │   ├── callbacks.py          # Callback query handlers
│   │   │   ├── inline.py             # Inline keyboard handlers
│   │   │   └── registration.py       # Handler registration
│   │   └── services/                 # Application services
│   │       ├── youtube_service.py    # YouTube metadata & download
│   │       ├── cache_service.py      # File caching logic
│   │       ├── download_service.py   # Download orchestration
│   │       ├── queue_service.py      # Download queue management
│   │       └── telegram_service.py   # Telegram messaging
│   │
│   ├── infrastructure/               # Infrastructure layer
│   │   ├── persistence/              # Database & repositories
│   │   │   ├── database.py           # SQLite connection management
│   │   │   ├── base_repository.py    # Base repository class
│   │   │   ├── user_repository.py    # User data access
│   │   │   ├── video_repository.py   # Video cache data access
│   │   │   └── authorization_repository.py  # Authorization data access
│   │   ├── external/                 # External integrations
│   │   │   ├── youtube/              # YouTube API wrapper
│   │   │   │   └── quality_selector.py
│   │   │   └── telegram/             # Telegram Bot API
│   │   └── utils/                    # Utility functions
│   │       ├── file_utils.py         # File operations
│   │       ├── sanitizers.py         # Input sanitization
│   │       ├── url_parser.py         # URL parsing utilities
│   │       └── metadata_probe.py     # Media metadata extraction
│   │
│   └── tests/                        # Test suite
│       ├── unit/                     # Unit tests (70%+ coverage)
│       │   ├── test_domain_entities.py
│       │   ├── test_services.py
│       │   ├── test_handlers.py
│       │   └── test_authorization_flow.py
│       └── integration/              # Integration tests
│
├── config/                           # Configuration files
│   └── config.yaml                   # Application configuration
│
├── docker/                           # Docker deployment
│   ├── Dockerfile                    # Container image definition
│   └── docker-compose.yml            # Multi-container orchestration
│
├── examples/                         # Usage examples
│   └── phase2_usage_example.py
│
├── extractors/                       # Custom extractors
│   └── archive_ragtag.py             # archive.ragtag.moe extractor
│
├── docs/                             # Additional documentation
│
├── .gitignore                        # Git ignore rules
├── pyproject.toml                    # Python project configuration
├── requirements.txt                  # Production dependencies
├── requirements-dev.txt              # Development dependencies
├── README.md                         # This file
└── TROUBLESHOOTING_NETWORK.md        # Network troubleshooting guide
```

---

## 🇬🇧 English

### 1. Project Overview

The **Telegram YouTube Bot** is an asynchronous Telegram bot written in Python that allows users to download videos and audio from YouTube and other supported platforms (like `archive.ragtag.moe`). It leverages **yt-dlp** for media fetching, **ffmpeg** for media processing, and **python-telegram-bot** for Telegram interaction.

### 2. Key Features

- **Asynchronous Processing**: Uses `asyncio` and `aiosqlite` for efficient concurrent handling of multiple user requests
- **Quality Selection**: Offers a menu to select desired video quality (up to 2160p) or download as audio only
- **Download Queue**: Implements a global download queue with semaphore control (`DOWNLOAD_SEMAPHORE = 5`) to prevent resource exhaustion
- **Progress Updates**: Provides real-time download progress updates to users
- **File Caching**: Caches uploaded files by `video_id` and `quality` to avoid redundant downloads
- **Authorization System**: New users must be approved by admin before using download functionality
- **Language Preference**: Users can set default language preference for audio tracks
- **Local Bot API Support**: Configured to use local Telegram Bot API server for faster uploads

### 3. System Dependencies

Before running the bot, install these system-level dependencies:

#### FFmpeg
- **Purpose**: Merges video/audio streams and extracts metadata
- **Installation**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH

#### yt-dlp
- **Purpose**: Extracts video information and downloads media
- **Installation**: `pip install yt-dlp`

### 4. Python Dependencies

Install via pip:

```bash
pip install python-telegram-bot httpx yt-dlp aiosqlite Pillow aiocache ffmpeg-python
```

Or use requirements files:
```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies (includes pytest, mypy, etc.)
pip install -r requirements-dev.txt
```

### 5. Configuration

Create/edit `config/config.yaml`:

```yaml
bot:
  token: "YOUR_BOT_TOKEN_HERE"
  admin_chat_id: 123456789  # Your Telegram user ID
  
server:
  local_api_url: "http://localhost:8081/bot"  # Optional: local Bot API server
  
download:
  max_concurrent: 3  # Maximum simultaneous downloads
  max_queue_size: 100  # Maximum queued tasks
  
cache:
  enabled: true
  directory: "./downloads"
```

### 6. Usage

#### Running the Bot

```bash
# Ensure dependencies are installed
pip install -r requirements.txt

# Run the refactored version
python src/main.py
```

#### In Telegram

1. **Start**: Send `/start` to initialize
2. **Language Selection**: Choose default audio language preference
3. **Authorization**: Wait for admin approval if not authorized
4. **Download**: Send a video link or use `/download <link>`
5. **Select Quality**: Choose from available resolutions or "Audio" option

### 7. Testing

Run unit tests with coverage:

```bash
# Run all unit tests
python -m pytest src/tests/unit/ -v

# With coverage report
python -m pytest src/tests/unit/ --cov=src --cov-report=html

# Run specific test file
python -m pytest src/tests/unit/test_handlers.py -v
```

Coverage target: ≥70%

### 8. Deployment

#### Docker Deployment

```bash
# Build image
docker build -t telegram-youtube-bot .

# Run with docker-compose
cd docker
docker-compose up -d
```

#### Manual Deployment

1. Install Python 3.8+
2. Install FFmpeg
3. Clone repository
4. Create virtual environment
5. Install dependencies
6. Configure `config/config.yaml`
7. Run `python src/main.py`

---

## 🇷🇺 Русский

### 1. Обзор Проекта

**Telegram YouTube Bot** — это асинхронный Telegram-бот на Python для скачивания видео и аудио с YouTube и других платформ. Использует **yt-dlp** для загрузки, **ffmpeg** для обработки и **python-telegram-bot** для взаимодействия с Telegram.

### 2. Ключевые Возможности

- **Асинхронная обработка**: Эффективная обработка множества запросов
- **Выбор качества**: Меню выбора качества видео (до 2160p) или аудио
- **Очередь загрузок**: Ограничение одновременных загрузок для стабильности
- **Обновление прогресса**: Отображение прогресса в реальном времени
- **Кэширование**: Кэширование файлов для повторных запросов
- **Авторизация**: Требуется одобрение администратора
- **Настройка языка**: Выбор предпочтительного языка аудио

### 3. Запуск Бота

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск обновленной версии
python src/main.py
```

### 4. Тестирование

```bash
# Запуск тестов
python -m pytest src/tests/unit/ -v

# С отчетом о покрытии
python -m pytest src/tests/unit/ --cov=src --cov-report=html
```

---

## 🔧 Troubleshooting

### Common Issues

1. **"FFmpeg not found"**
   - Ensure FFmpeg is installed and in your system PATH
   - Restart your terminal after installation

2. **"Connection error" to Telegram**
   - Check your internet connection
   - Verify bot token is correct
   - If behind firewall, configure proxy in `config.yaml`

3. **Downloads failing**
   - Check available disk space
   - Verify yt-dlp is up to date: `pip install -U yt-dlp`
   - Some videos may have restrictions

See [TROUBLESHOOTING_NETWORK.md](TROUBLESHOOTING_NETWORK.md) for detailed network troubleshooting.

---

## 📊 Development Status

### Completed Phases

✅ **Phase 1**: Core Infrastructure (Config, Exceptions, Logging)  
✅ **Phase 2**: Domain Layer (Entities, Value Objects)  
✅ **Phase 3**: Infrastructure Layer (Repositories, Utils)  
✅ **Phase 4**: Application Layer (Services)  
✅ **Phase 5**: Presentation Layer (Handlers)  
✅ **Phase 6**: Testing & Integration (Unit Tests, Coverage)  
✅ **Phase 7**: Documentation & Cleanup ← **CURRENT**

### Future Enhancements

- [ ] Add integration tests for complete user workflows
- [ ] Implement multi-language support (i18n)
- [ ] Add rate limiting per user
- [ ] Support for additional video platforms
- [ ] Web dashboard for monitoring
- [ ] PostgreSQL support as alternative to SQLite

---

## 📝 License

This project is provided as-is for educational purposes.

## 👥 Authors

Developed and maintained by the Telegram YouTube Bot team.

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [ffmpeg](https://ffmpeg.org/)
