"""
Test Fixtures

Reusable test data and mock objects for unit and integration tests.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import Update, Message, User, Chat


# === Data Fixtures ===

@pytest.fixture
def mock_user_data():
    """Create mock user data dictionary.
    
    Returns:
        Dictionary with valid user data
    """
    return {
        'user_id': 123456789,
        'username': 'test_user',
        'first_name': 'Test',
        'last_name': 'User',
        'language_code': 'en',
    }


@pytest.fixture
def mock_video_data():
    """Create mock video data dictionary.
    
    Returns:
        Dictionary with valid video metadata
    """
    return {
        'video_id': 'dQw4w9WgXcQ',
        'title': 'Test Video Title',
        'uploader': 'Test Channel',
        'uploader_url': 'https://youtube.com/channel/test',
        'duration': 212.5,
        'thumbnail_url': 'https://i.ytimg.com/vi/test/maxresdefault.jpg',
        'description': 'Test video description',
        'view_count': 1000000,
        'upload_date': '20240101',
        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    }


@pytest.fixture
def mock_download_task_data(mock_user_data, mock_video_data):
    """Create mock download task data.
    
    Args:
        mock_user_data: User data fixture
        mock_video_data: Video data fixture
        
    Returns:
        Dictionary with download task parameters
    """
    return {
        'chat_id': mock_user_data['user_id'],
        'user_id': mock_user_data['user_id'],
        'username': mock_user_data['username'],
        'video_id': mock_video_data['video_id'],
        'url': mock_video_data['url'],
        'quality': '720',
    }


# === Telegram Mock Fixtures ===

@pytest.fixture
def mock_telegram_user(mock_user_data):
    """Create mock Telegram User object.
    
    Args:
        mock_user_data: User data fixture
        
    Returns:
        Mocked telegram.User object
    """
    user = MagicMock(spec=User)
    user.id = mock_user_data['user_id']
    user.username = mock_user_data['username']
    user.first_name = mock_user_data['first_name']
    user.last_name = mock_user_data.get('last_name')
    user.language_code = mock_user_data.get('language_code', 'en')
    return user


@pytest.fixture
def mock_telegram_chat():
    """Create mock Telegram Chat object.
    
    Returns:
        Mocked telegram.Chat object
    """
    chat = MagicMock(spec=Chat)
    chat.id = 123456789
    chat.type = 'private'
    return chat


@pytest.fixture
def mock_telegram_message(mock_telegram_user, mock_telegram_chat):
    """Create mock Telegram Message object.
    
    Args:
        mock_telegram_user: User fixture
        mock_telegram_chat: Chat fixture
        
    Returns:
        Mocked telegram.Message object
    """
    message = MagicMock(spec=Message)
    message.message_id = 1
    message.from_user = mock_telegram_user
    message.chat = mock_telegram_chat
    message.text = ''
    message.date = None
    return message


@pytest.fixture
def mock_telegram_update(mock_telegram_message):
    """Create mock Telegram Update object.
    
    Args:
        mock_telegram_message: Message fixture
        
    Returns:
        Mocked telegram.Update object
    """
    update = MagicMock(spec=Update)
    update.update_id = 1
    update.message = mock_telegram_message
    update.effective_user = mock_telegram_message.from_user
    update.effective_chat = mock_telegram_message.chat
    update.callback_query = None
    update.inline_query = None
    return update


@pytest.fixture
def mock_context():
    """Create mock Telegram ContextTypes object.
    
    Returns:
        Mocked context object
    """
    context = AsyncMock()
    context.chat_data = {}
    context.user_data = {}
    context.bot_data = {}
    context.job_queue = None
    return context


# === Service Mock Fixtures ===

@pytest.fixture
def mock_youtube_service():
    """Create mock YoutubeService.
    
    Returns:
        Mocked YoutubeService instance
    """
    service = AsyncMock()
    service.get_video_info = AsyncMock()
    service.select_best_quality_format = MagicMock()
    service.get_available_qualities = MagicMock()
    service.validate_url = MagicMock(return_value=True)
    service.extract_video_id = MagicMock(return_value='test_video_id')
    return service


@pytest.fixture
def mock_download_service():
    """Create mock DownloadService.
    
    Returns:
        Mocked DownloadService instance
    """
    service = AsyncMock()
    service.execute_download = AsyncMock()
    service.register_progress_callback = MagicMock()
    service.unregister_progress_callback = MagicMock()
    service.cancel_download = AsyncMock()
    service.get_download_directory = MagicMock(return_value='/tmp/downloads')
    return service


@pytest.fixture
def mock_cache_service():
    """Create mock CacheService.
    
    Returns:
        Mocked CacheService instance
    """
    service = AsyncMock()
    service.get_cached_file = AsyncMock()
    service.save_to_cache = AsyncMock()
    service.is_cached = AsyncMock(return_value=False)
    service.get_cached_qualities = AsyncMock()
    service.invalidate_cache = AsyncMock()
    service.get_cache_statistics = AsyncMock()
    return service


@pytest.fixture
def mock_telegram_bot_service():
    """Create mock TelegramService.
    
    Returns:
        Mocked TelegramService instance
    """
    service = AsyncMock()
    service.send_message = AsyncMock(return_value=True)
    service.send_video = AsyncMock()
    service.send_audio = AsyncMock()
    service.send_document = AsyncMock()
    service.edit_message = AsyncMock()
    service.delete_message = AsyncMock()
    service.notify_user = AsyncMock(return_value=True)
    service.create_inline_keyboard = MagicMock()
    return service


@pytest.fixture
def mock_queue_service():
    """Create mock QueueService.
    
    Returns:
        Mocked QueueService instance
    """
    service = AsyncMock()
    service.add_to_queue = AsyncMock(return_value=True)
    service.remove_from_queue = AsyncMock()
    service.get_queue_status = MagicMock(return_value={
        'queue_length': 0,
        'active_tasks': 0,
        'max_concurrent': 3
    })
    service.start_worker = AsyncMock()
    service.stop_worker = AsyncMock()
    return service


@pytest.fixture
def mock_user_repository():
    """Create mock UserRepository.
    
    Returns:
        Mocked UserRepository instance
    """
    repo = AsyncMock()
    repo.create_or_update = AsyncMock()
    repo.get_user = AsyncMock()
    repo.get_all_users = AsyncMock()
    repo.delete_user = AsyncMock()
    repo.update_language = AsyncMock()
    repo.get_language = AsyncMock()
    repo.increment_downloads = AsyncMock()
    repo.get_downloads_count = AsyncMock()
    repo.can_download = AsyncMock(return_value=True)
    repo.update_activity = AsyncMock()
    return repo


@pytest.fixture
def mock_authorization_repository():
    """Create mock AuthorizationRepository.
    
    Returns:
        Mocked AuthorizationRepository instance
    """
    repo = AsyncMock()
    repo.add_user = AsyncMock()
    repo.remove_user = AsyncMock()
    repo.is_authorized = AsyncMock(return_value=True)
    repo.get_all_authorized = AsyncMock()
    repo.get_authorized_count = AsyncMock()
    return repo


@pytest.fixture
def mock_video_repository():
    """Create mock VideoRepository.
    
    Returns:
        Mocked VideoRepository instance
    """
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.get_cached = AsyncMock()
    repo.get_cached_by_file_id = AsyncMock()
    repo.is_cached = AsyncMock(return_value=False)
    repo.get_cached_qualities = AsyncMock()
    repo.delete_cached = AsyncMock()
    repo.get_cache_stats = AsyncMock()
    return repo


# === Composite Fixtures ===

@pytest.fixture
def mock_all_services(
    mock_youtube_service,
    mock_download_service,
    mock_cache_service,
    mock_telegram_bot_service,
    mock_queue_service,
    mock_user_repository,
    mock_authorization_repository,
    mock_video_repository
):
    """Create dictionary of all mocked services.
    
    Returns:
        Dictionary with all service mocks
    """
    return {
        'youtube_service': mock_youtube_service,
        'download_service': mock_download_service,
        'cache_service': mock_cache_service,
        'telegram_service': mock_telegram_bot_service,
        'queue_service': mock_queue_service,
        'user_repo': mock_user_repository,
        'auth_repo': mock_authorization_repository,
        'video_repo': mock_video_repository,
    }


@pytest.fixture
def mock_application():
    """Create mock Telegram Application.
    
    Returns:
        Mocked Application instance
    """
    app = AsyncMock()
    app.bot = AsyncMock()
    app.add_handler = MagicMock()
    app.run_polling = AsyncMock()
    return app
