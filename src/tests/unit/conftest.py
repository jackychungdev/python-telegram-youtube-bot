"""
Pytest Conftest for Unit Tests

Defines common fixtures for unit tests.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_video_data():
    """Mock video data fixture."""
    return {
        'video_id': 'test123',
        'title': 'Test Video',
        'uploader': 'Test Channel',
        'uploader_url': 'https://youtube.com/c/testchannel',
        'duration': 180,
        'thumbnail_url': 'https://i.ytimg.com/vi/test123/maxresdefault.jpg',
        'description': 'Test video description',
        'view_count': 1000,
        'upload_date': '20240101',
    }


@pytest.fixture
def mock_user_data():
    """Mock user data fixture."""
    return {
        'user_id': 123456,
        'username': 'testuser',
        'language': 'en',
    }


@pytest.fixture
def mock_video_repository():
    """Mock video repository fixture."""
    mock_repo = MagicMock()
    mock_repo.is_cached = AsyncMock(return_value=False)
    mock_repo.save = AsyncMock(return_value=True)
    mock_repo.get_cached_qualities = AsyncMock(return_value=[])
    mock_repo.get_cache_statistics = AsyncMock(return_value={
        'total_videos': 0,
        'total_size': 0,
        'oldest_video': None,
        'newest_video': None,
    })
    return mock_repo


@pytest.fixture
def mock_user_repository():
    """Mock user repository fixture."""
    mock_repo = MagicMock()
    mock_repo.find_by_id = AsyncMock(return_value=None)
    mock_repo.save = AsyncMock(return_value=True)
    mock_repo.increment_downloads = AsyncMock(return_value=True)
    return mock_repo


@pytest.fixture
def mock_authorization_repository():
    """Mock authorization repository fixture."""
    mock_repo = MagicMock()
    mock_repo.is_authorized_user = AsyncMock(return_value=False)
    mock_repo.add_user = AsyncMock(return_value=True)
    mock_repo.remove_user = AsyncMock(return_value=True)
    mock_repo.get_authorized_count = AsyncMock(return_value=0)
    mock_repo.get_all_authorized = AsyncMock(return_value=[])
    return mock_repo


@pytest.fixture
def mock_telegram_bot():
    """Mock Telegram bot fixture."""
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(return_value=True)
    mock_bot.send_video = AsyncMock(return_value=True)
    return mock_bot


@pytest.fixture
def mock_telegram_update():
    """Mock Telegram update fixture."""
    mock_update = MagicMock()
    mock_update.message = MagicMock()
    mock_update.message.chat_id = 123456
    mock_update.effective_user = MagicMock()
    mock_update.effective_user.id = 123456
    mock_update.effective_user.username = 'testuser'
    mock_update.effective_chat = MagicMock()
    mock_update.effective_chat.id = 123456
    mock_update.callback_query = MagicMock()
    return mock_update


@pytest.fixture
def mock_context():
    """Mock Telegram context fixture."""
    mock_ctx = MagicMock()
    mock_ctx.user_data = {}
    return mock_ctx


@pytest.fixture
def mock_all_services(
    mock_video_repository,
    mock_user_repository,
    mock_authorization_repository,
    mock_telegram_bot
):
    """Mock all services fixture."""
    from application.services.youtube_service import YoutubeService
    from application.services.cache_service import CacheService
    from application.services.download_service import DownloadService
    from application.services.telegram_service import TelegramService
    from application.services.queue_service import QueueService
    
    # Create mock services
    youtube_service = MagicMock(spec=YoutubeService)
    youtube_service.get_video_info = AsyncMock(return_value=MagicMock())
    
    cache_service = MagicMock(spec=CacheService)
    cache_service.is_cached = AsyncMock(return_value=False)
    cache_service.save_to_cache = AsyncMock(return_value=True)
    cache_service.get_cached_qualities = AsyncMock(return_value=[])
    cache_service.get_cache_statistics = AsyncMock(return_value={'total_files': 0})
    
    download_service = MagicMock(spec=DownloadService)
    download_service.start_download = AsyncMock(return_value=True)
    
    telegram_service = MagicMock(spec=TelegramService)
    telegram_service.bot = mock_telegram_bot
    telegram_service.send_message = AsyncMock(return_value=MagicMock())
    telegram_service.notify_user = AsyncMock(return_value=MagicMock())
    
    queue_service = MagicMock(spec=QueueService)
    queue_service.add_to_queue = AsyncMock(return_value='task_123')
    queue_service.get_queue_status = AsyncMock(return_value={
        'queue_length': 0,
        'active_tasks': 0,
        'max_concurrent': 3
    })
    
    return {
        'youtube_service': youtube_service,
        'cache_service': cache_service,
        'download_service': download_service,
        'telegram_service': telegram_service,
        'queue_service': queue_service,
        'video_repo': mock_video_repository,
        'user_repo': mock_user_repository,
        'auth_repo': mock_authorization_repository,
    }


@pytest.fixture
def mock_download_task_data():
    """Mock download task data fixture."""
    return {
        'chat_id': 123456,
        'user_id': 123456,
        'username': 'testuser',
        'video_id': 'test_video',
        'url': 'https://youtube.com/watch?v=test',
        'quality': '720',
    }
