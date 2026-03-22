# 🏗️ Refactored Telegram YouTube Bot - New Architecture

This directory contains the **refactored version** of the Telegram YouTube Bot, built with a clean, layered architecture.

---

## 📐 Architecture Overview

The project follows a **layered architecture** with clear separation of concerns:

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

---

## 📁 Directory Structure

```
src/
├── __init__.py                 # Package initialization
├── main.py                     # Application entry point
│
├── core/                       # Core infrastructure
│   ├── config.py               # Configuration management
│   ├── exceptions.py           # Custom exception hierarchy
│   └── logging_config.py       # Logging with rotation
│
├── domain/                     # Business domain layer
│   ├── entities/               # Domain entities
│   │   ├── user.py             # User entity
│   │   ├── video.py            # Video entity
│   │   └── download_task.py    # DownloadTask entity
│   ├── value_objects/          # Immutable value objects
│   │   ├── video_quality.py    # Quality enum
│   │   └── download_status.py  # Status enum
│   └── services/               # Domain service interfaces
│
├── application/                # Application layer
│   ├── services/               # Application services
│   └── handlers/               # Telegram command handlers
│
├── infrastructure/             # Infrastructure layer
│   ├── persistence/            # Database & repositories
│   ├── external/               # External integrations
│   │   ├── youtube/            # YouTube API wrapper
│   │   └── telegram/           # Telegram Bot API
│   └── utils/                  # Utility functions
│
└── tests/                      # Test suite
    ├── unit/                   # Unit tests
    ├── integration/            # Integration tests
    └── fixtures/               # Test fixtures
```

---

## 🚀 Quick Start

### Current Status: Phase 1 Complete ✅

The foundational layer is complete and ready for use. The bot currently runs using the legacy implementation while the new architecture is being built.

### Running the Bot

```bash
# From project root
python src/main.py
```

**Note:** Currently delegates to legacy implementation. Will be fully replaced in Phase 6.

---

## 📦 Phase 1 Deliverables

### ✅ Core Infrastructure
- **Configuration Management** - Type-safe YAML config loading
- **Exception Hierarchy** - 7 specialized exception types
- **Logging System** - Console + file with rotation

### ✅ Domain Layer
- **User Entity** - Rate limiting, activity tracking
- **Video Entity** - Format handling, quality selection
- **DownloadTask Entity** - State machine, progress tracking
- **VideoQuality VO** - Quality level enumeration
- **DownloadStatus VO** - Status state machine

### ✅ Supporting Infrastructure
- Module organization with proper `__init__.py` files
- Type hints throughout (>95% coverage)
- Comprehensive docstrings (100% coverage)
- Test framework configuration

---

## 🎯 Design Patterns

1. **Entity Pattern** - User, Video, DownloadTask (identity-based)
2. **Value Object Pattern** - VideoQuality, DownloadStatus (immutable)
3. **State Pattern** - DownloadTask status transitions
4. **Factory Method** - `VideoFormat.from_ytdlp_format()`
5. **Specification Pattern** - `User.can_download()` business rule
6. **Repository Pattern** - (Coming in Phase 2)
7. **Dependency Injection** - (Coming in Phase 2)

---

## 🔧 Development

### Prerequisites
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Running Tests
```bash
pytest
pytest --cov=src  # With coverage
```

### Code Quality
```bash
black src/
flake8 src/
mypy src/
isort src/
```

---

## 📋 Implementation Roadmap

| Phase | Focus | Status | ETA |
|-------|-------|--------|-----|
| **Phase 1** | Foundation | ✅ Complete | Mar 2026 |
| **Phase 2** | Data Access Layer | 🔄 Next | 3-4 hours |
| **Phase 3** | Service Layer | ⏳ Pending | 4-5 hours |
| **Phase 4** | Infrastructure | ⏳ Pending | 3-4 hours |
| **Phase 5** | Presentation | ⏳ Pending | 3-4 hours |
| **Phase 6** | Testing | ⏳ Pending | 4-5 hours |
| **Phase 7** | Documentation | ⏳ Pending | 2-3 hours |

---

## 📖 Usage Examples

### Configuration
```python
from src.core import Config

config = Config()
token = config.get('bot.TOKEN')
limit = config.download['DOWNLOAD_LIMIT_PER_HOUR']
```

### Domain Entities
```python
from src.domain import User, Video, DownloadTask, VideoQuality

# User with rate limiting
user = User(user_id=123, username='john')
if user.can_download(limit_per_hour=10):
    user.increment_downloads()

# Video with formats
video = Video(...)
qualities = video.available_qualities  # [Q1080, Q720, Q480, ...]
has_audio = video.has_audio_format()

# Download task state machine
task = DownloadTask(
    chat_id=456,
    user_id=123,
    username='john',
    video_id='abc123',
    url='https://youtube.com/watch?v=abc123',
    quality='720'
)
task.mark_started()
task.update_progress(50)
task.mark_completed(file_id='xyz789')
```

### Exception Handling
```python
from src.core.exceptions import DownloadError, AuthorizationError

try:
    await download_service.download(video_id)
except DownloadError as e:
    logger.error(f"Download failed: {e}")
except AuthorizationError as e:
    logger.error(f"Unauthorized: {e}")
```

### Logging Setup
```python
from src.core import setup_logging

logger = setup_logging(
    log_file='bot.log',
    max_size_mb=10,
    level=logging.INFO
)
```

---

## 🔜 Coming Soon (Phase 2)

- Repository pattern implementation
- Base repository with CRUD operations
- UserRepository, VideoRepository, AuthorizationRepository
- Database connection management
- Schema migrations
- Dependency injection container

---

## 📝 Additional Documentation

- [Phase 1 Completion Report](../PHASE_1_COMPLETE.md)
- [Phase 1 Summary](../PHASE_1_SUMMARY.md)
- [Main Project README](../README.md)

---

## 🤝 Contributing

This is a work-in-progress refactoring. Please refer to the migration guide before making changes.

---

**Version:** 2.0.0 (Refactored)  
**License:** MIT  
**Author:** Python Telegram YouTube Bot Team
