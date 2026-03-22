"""
Integration Tests

Tests for complete workflows and component integration.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Message
from src.domain.entities.user import User
from src.domain.entities.video import Video
from src.domain.entities.download_task import DownloadTask
from src.domain.value_objects.download_status import DownloadStatus


class TestCompleteDownloadWorkflow:
    """Test complete download workflow from URL to file."""
    
    @pytest.mark.asyncio
    async def test_full_download_workflow(
        self,
        mock_user_data,
        mock_video_data,
        mock_all_services
    ):
        """Test complete download process."""
        from src.application.handlers.commands import CommandHandlers
        
        # Setup: Mock message with YouTube link
        youtube_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        mock_message = MagicMock(spec=Message)
        mock_message.text = youtube_url
        mock_message.effective_user = MagicMock()
        mock_message.effective_user.id = 123456
        mock_message.effective_chat = MagicMock()
        mock_message.effective_chat.id = 123456
        
        mock_telegram_update.message = mock_message
        
        # Setup: Authorization
        mock_all_services['auth_repo'].is_authorized = AsyncMock(return_value=True)
        
        # Setup: User context (no rate limit)
        mock_all_services['user_repo'].get_user_info = AsyncMock(return_value={
            'downloads_in_hour': 0,
            'total_downloads': 5
        })
        
        # Setup: YouTube service returns video info with proper types
        mock_video = MagicMock()
        mock_video.video_id = mock_video_data['video_id']
        mock_video.title = mock_video_data['title']
        mock_video.uploader = mock_video_data['uploader']
        mock_video.duration = mock_video_data['duration']
        mock_video.view_count = int(mock_video_data['view_count'])  # Ensure view_count is integer
        mock_all_services['youtube_service'].get_video_info = AsyncMock(return_value=mock_video)
        
        # Setup: Message deletion mock
        processing_msg = AsyncMock()
        processing_msg.delete = AsyncMock()
        mock_all_services['telegram_service'].send_message = AsyncMock(return_value=processing_msg)
        
        # Execute: Create handler and process message
        handler = CommandHandlers(
            mock_all_services['telegram_service'].bot,
            mock_all_services
        )
        
        # Mock get_user_context properly with AsyncMock
        handler.get_user_context = AsyncMock(return_value={'downloads_in_hour': 0})
        
        await handler.handle_message(mock_telegram_update, mock_context)
        
        # Verify: Authorization was checked
        mock_all_services['auth_repo'].is_authorized.assert_called_once_with(123456)
        
        # Verify: Video info was fetched
        mock_all_services['youtube_service'].get_video_info.assert_called_once_with(youtube_url)
        
        # Verify: Messages were sent (processing + quality selection)
        assert mock_all_services['telegram_service'].send_message.call_count >= 1
        
        # Verify: Quality selection keyboard was sent with reply_markup
        last_call = mock_all_services['telegram_service'].send_message.call_args_list[-1]
        assert 'reply_markup' in last_call.kwargs
    
    @pytest.mark.asyncio
    async def test_handler_error_sends_message(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test handler errors send error message to user."""
        from src.application.handlers.base_handler import BaseHandler
        
        # Create concrete implementation for testing
        class TestHandler(BaseHandler):
            async def handle(self, update, context):
                pass
        
        handler = TestHandler(
            mock_all_services['telegram_service'].bot,
            mock_all_services
        )
        
        # Send error message
        await handler.send_error_message(123456, "Test error")
        
        # Verify notification was sent
        mock_all_services['telegram_service'].notify_user.assert_called_once_with(
            user_id=123456,
            message="Error: Test error",
            notification_type='error'
        )


class TestMessageHandlerIntegration:
    """Integration tests for regular message handler with YouTube links."""
    
    @pytest.mark.asyncio
    async def test_message_handler_youtube_link_full_workflow(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services,
        mock_video_data
    ):
        """Test complete workflow when user sends YouTube link as regular message."""
        from src.application.handlers.commands import CommandHandlers
        
        # Setup: Mock message with YouTube link
        youtube_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        mock_message = MagicMock(spec=Message)
        mock_message.text = youtube_url
        
        # Override the update's message and user/chat
        mock_telegram_update.message = mock_message
        mock_telegram_update.effective_user = MagicMock()
        mock_telegram_update.effective_user.id = 123456
        mock_telegram_update.effective_chat = MagicMock()
        mock_telegram_update.effective_chat.id = 123456
        
        # Setup: Authorization
        mock_all_services['auth_repo'].is_authorized = AsyncMock(return_value=True)
        
        # Setup: User context (no rate limit)
        mock_all_services['user_repo'].get_user_info = AsyncMock(return_value={
            'downloads_in_hour': 0,
            'total_downloads': 5
        })
        
        # Setup: YouTube service returns video info
        mock_video = MagicMock()
        mock_video.video_id = mock_video_data['video_id']
        mock_video.title = mock_video_data['title']
        mock_video.uploader = mock_video_data['uploader']
        mock_video.duration = mock_video_data['duration']
        mock_video.view_count = mock_video_data['view_count']
        mock_all_services['youtube_service'].get_video_info = AsyncMock(return_value=mock_video)
        
        # Setup: Message deletion mock
        processing_msg = AsyncMock()
        processing_msg.delete = AsyncMock()
        mock_all_services['telegram_service'].send_message = AsyncMock(return_value=processing_msg)
        
        # Execute: Create handler and process message
        handler = CommandHandlers(
            mock_all_services['telegram_service'].bot,
            mock_all_services
        )
        
        await handler.handle_message(mock_telegram_update, mock_context)
        
        # Verify: Authorization was checked
        mock_all_services['auth_repo'].is_authorized.assert_called_once_with(123456)
        
        # Verify: Video info was fetched
        mock_all_services['youtube_service'].get_video_info.assert_called_once_with(youtube_url)
        
        # Verify: Messages were sent (processing + quality selection)
        assert mock_all_services['telegram_service'].send_message.call_count >= 1
        
        # Verify: Quality selection keyboard was sent with reply_markup
        last_call = mock_all_services['telegram_service'].send_message.call_args_list[-1]
        assert 'reply_markup' in last_call.kwargs
    
    @pytest.mark.asyncio
    async def test_message_handler_unauthorized_user_blocked(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test that unauthorized users are blocked from downloading."""
        from src.application.handlers.commands import CommandHandlers
        
        # Setup: Mock message with YouTube link
        mock_message = MagicMock(spec=Message)
        mock_message.text = 'https://www.youtube.com/watch?v=test123'
        mock_message.effective_user = MagicMock()
        mock_message.effective_user.id = 999999
        mock_message.effective_chat = MagicMock()
        mock_message.effective_chat.id = 999999
        
        mock_telegram_update.message = mock_message
        
        # Setup: User is NOT authorized
        mock_all_services['auth_repo'].is_authorized = AsyncMock(return_value=False)
        
        # Execute
        handler = CommandHandlers(
            mock_all_services['telegram_service'].bot,
            mock_all_services
        )
        
        await handler.handle_message(mock_telegram_update, mock_context)
        
        # Verify: Authorization was checked
        mock_all_services['auth_repo'].is_authorized.assert_called_once_with(999999)
        
        # Verify: Error message was sent via notify_user
        mock_all_services['telegram_service'].notify_user.assert_called_once()
        call_args = mock_all_services['telegram_service'].notify_user.call_args
        assert 'authorization' in call_args.kwargs['message'].lower() or \
               'authorized' in call_args.kwargs['message'].lower()
    
    @pytest.mark.asyncio
    async def test_message_handler_rate_limit_enforced(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test that rate limiting prevents excessive downloads."""
        from src.application.handlers.commands import CommandHandlers
        
        # Setup: Mock message with YouTube link
        mock_message = MagicMock(spec=Message)
        mock_message.text = 'https://www.youtube.com/watch?v=test123'
        mock_message.effective_user = MagicMock()
        mock_message.effective_user.id = 123456
        mock_message.effective_chat = MagicMock()
        mock_message.effective_chat.id = 123456
        
        mock_telegram_update.message = mock_message
        
        # Setup: User is authorized but at rate limit
        mock_all_services['auth_repo'].is_authorized = AsyncMock(return_value=True)
        mock_all_services['user_repo'].get_user_info = AsyncMock(return_value={
            'downloads_in_hour': 10,  # At the limit
            'total_downloads': 50
        })
        
        # Execute
        handler = CommandHandlers(
            mock_all_services['telegram_service'].bot,
            mock_all_services
        )
        
        await handler.handle_message(mock_telegram_update, mock_context)
        
        # Verify: Rate limit was checked
        mock_all_services['user_repo'].get_user_info.assert_called_once_with(123456)
        
        # Verify: Rate limit error message was sent
        mock_all_services['telegram_service'].notify_user.assert_called_once()
        call_args = mock_all_services['telegram_service'].notify_user.call_args
        assert 'limit' in call_args.kwargs['message'].lower()
    
    @pytest.mark.asyncio
    async def test_message_handler_non_youtube_link_ignored(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test that non-YouTube links are ignored without processing."""
        from src.application.handlers.commands import CommandHandlers
        
        # Setup: Mock message with non-YouTube link
        mock_message = MagicMock(spec=Message)
        mock_message.text = 'https://vimeo.com/test123'
        
        # Override the update's message and user
        mock_telegram_update.message = mock_message
        mock_telegram_update.effective_user = MagicMock()
        mock_telegram_update.effective_user.id = 123456
        
        # Execute
        handler = CommandHandlers(
            mock_all_services['telegram_service'].bot,
            mock_all_services
        )
        
        await handler.handle_message(mock_telegram_update, mock_context)
        
        # Verify: No authorization check (link was ignored immediately)
        mock_all_services['auth_repo'].is_authorized.assert_not_called()
        
        # Verify: No messages sent
        mock_all_services['telegram_service'].send_message.assert_not_called()
        mock_all_services['telegram_service'].notify_user.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_message_handler_various_youtube_url_formats(
        self,
        mock_context,
        mock_all_services,
        mock_video_data
    ):
        """Test that various YouTube URL formats are recognized."""
        from src.application.handlers.commands import CommandHandlers
        from unittest.mock import MagicMock as Mock
        
        url_formats = [
            ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://youtube.com/watch?v=dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://youtu.be/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('http://youtu.be/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://www.youtube.com/shorts/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
        ]
        
        for youtube_url, expected_video_id in url_formats:
            # Create fresh mocks for each iteration
            mock_update = Mock()
            mock_message = Mock()
            mock_message.text = youtube_url
            mock_update.message = mock_message
            mock_update.effective_user = Mock()
            mock_update.effective_user.id = 123456
            mock_update.effective_chat = Mock()
            mock_update.effective_chat.id = 123456
            
            # Setup fresh service mocks
            auth_repo = AsyncMock()
            auth_repo.is_authorized = AsyncMock(return_value=True)
            
            user_repo = AsyncMock()
            user_repo.get_user_info = AsyncMock(return_value={'downloads_in_hour': 0})
            
            youtube_service = AsyncMock()
            mock_video = Mock()
            mock_video.video_id = expected_video_id
            youtube_service.get_video_info = AsyncMock(return_value=mock_video)
            
            telegram_service = AsyncMock()
            processing_msg = AsyncMock()
            processing_msg.delete = AsyncMock()
            telegram_service.send_message = AsyncMock(return_value=processing_msg)
            
            fresh_services = {
                'auth_repo': auth_repo,
                'user_repo': user_repo,
                'youtube_service': youtube_service,
                'telegram_service': telegram_service,
                'cache_service': AsyncMock(),
                'download_service': AsyncMock(),
                'queue_service': AsyncMock(),
            }
            
            # Execute
            handler = CommandHandlers(telegram_service['bot'] if isinstance(telegram_service, dict) else telegram_service, fresh_services)
            
            # Mock get_user_context to return a proper coroutine
            async def mock_get_context(uid):
                return {'downloads_in_hour': 0}
            handler.get_user_context = mock_get_context
            
            await handler.handle_message(mock_update, mock_context)
            
            # Verify: Each format was processed
            youtube_service.get_video_info.assert_called_once_with(youtube_url)
    
    @pytest.mark.asyncio
    async def test_message_handler_quality_selection_callback_integration(
        self,
        mock_context,
        mock_all_services,
        mock_video_data
    ):
        """Test that quality selection creates proper callback data."""
        from src.application.handlers.commands import CommandHandlers
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from unittest.mock import MagicMock as Mock
        
        # Create fresh mocks
        mock_update = Mock()
        mock_message = Mock()
        mock_message.text = 'https://www.youtube.com/watch?v=test123'
        mock_update.message = mock_message
        mock_update.effective_user = Mock()
        mock_update.effective_user.id = 123456
        mock_update.effective_chat = Mock()
        mock_update.effective_chat.id = 123456
        
        # Setup fresh service mocks
        auth_repo = AsyncMock()
        auth_repo.is_authorized = AsyncMock(return_value=True)
        
        user_repo = AsyncMock()
        user_repo.get_user_info = AsyncMock(return_value={'downloads_in_hour': 0})
        
        youtube_service = AsyncMock()
        mock_video = Mock()
        mock_video.video_id = 'test123'
        mock_video.title = 'Test Video'
        youtube_service.get_video_info = AsyncMock(return_value=mock_video)
        
        telegram_service = AsyncMock()
        processing_msg = AsyncMock()
        processing_msg.delete = AsyncMock()
        telegram_service.send_message = AsyncMock(return_value=processing_msg)
        
        fresh_services = {
            'auth_repo': auth_repo,
            'user_repo': user_repo,
            'youtube_service': youtube_service,
            'telegram_service': telegram_service,
            'cache_service': AsyncMock(),
            'download_service': AsyncMock(),
            'queue_service': AsyncMock(),
        }
        
        # Execute
        handler = CommandHandlers(telegram_service['bot'] if isinstance(telegram_service, dict) else telegram_service, fresh_services)
        
        # Mock get_user_context to return a proper coroutine
        async def mock_get_context(uid):
            return {'downloads_in_hour': 0}
        handler.get_user_context = mock_get_context
        
        await handler.handle_message(mock_update, mock_context)
        
        # Verify: Quality options were sent
        calls = telegram_service.send_message.call_args_list
        assert len(calls) >= 2  # Processing message + quality selection
        
        # Get the quality selection message (last call)
        quality_call = calls[-1]
        assert 'reply_markup' in quality_call.kwargs
        
        # Verify keyboard structure
        reply_markup = quality_call.kwargs['reply_markup']
        assert isinstance(reply_markup, InlineKeyboardMarkup)
        
        # Check that all quality options are present
        keyboard = reply_markup.inline_keyboard
        all_callback_data = []
        for row in keyboard:
            for button in row:
                if isinstance(button, InlineKeyboardButton):
                    all_callback_data.append(button.callback_data)
        
        # Verify quality options exist
        assert any('dl_2160_' in cb for cb in all_callback_data)  # 4K
        assert any('dl_1080_' in cb for cb in all_callback_data)  # Full HD
        assert any('dl_720_' in cb for cb in all_callback_data)   # HD
        assert any('dl_480_' in cb for cb in all_callback_data)   # SD
        assert any('dl_360_' in cb for cb in all_callback_data)   # SD
        assert any('dl_audio_' in cb for cb in all_callback_data) # Audio


class TestDatabaseIntegration:
    """Integration tests with actual database operations."""
    
    @pytest.mark.asyncio
    async def test_authorization_repository_add_and_check(
        self,
        temp_database,
        mock_user_data
    ):
        """Test adding and checking authorization in real database."""
        from src.infrastructure.persistence.repositories.authorization_repository import AuthorizationRepository
        
        # Create repository with real database connection
        auth_repo = AuthorizationRepository(temp_database)
        
        # Add user to authorized list
        added = await auth_repo.add_user(
            mock_user_data['user_id'],
            mock_user_data['username']
        )
        assert added is True
        
        # Check if user is authorized
        is_authorized = await auth_repo.is_authorized(mock_user_data['user_id'])
        assert is_authorized is True
        
        # Get user info
        user_info = await auth_repo.get_user_info(mock_user_data['user_id'])
        assert user_info is not None
        assert user_info['user_id'] == mock_user_data['user_id']
    
    @pytest.mark.asyncio
    async def test_user_repository_create_and_track_download(
        self,
        temp_database,
        mock_user_data
    ):
        """Test user creation and download tracking in real database."""
        from src.infrastructure.persistence.repositories.user_repository import UserRepository
        
        # Create repository
        user_repo = UserRepository(temp_database)
        
        # Create or update user
        created = await user_repo.create_or_update(
            user_id=mock_user_data['user_id'],
            username=mock_user_data['username'],
            first_name=mock_user_data['first_name'],
            last_name=mock_user_data.get('last_name'),
            language_code='en'
        )
        assert created is not None
        
        # Check download permission (should be allowed)
        can_download = await user_repo.can_download(
            mock_user_data['user_id'],
            limit_per_hour=10
        )
        assert can_download is True
        
        # Increment download count
        incremented = await user_repo.increment_downloads(mock_user_data['user_id'])
        assert incremented is True
        
        # Get user info
        user_info = await user_repo.get_user_info(mock_user_data['user_id'])
        assert user_info is not None
        assert user_info['downloads_in_hour'] >= 0


class TestServiceIntegration:
    """Integration tests for service layer interactions."""
    
    @pytest.mark.asyncio
    async def test_queue_service_task_creation_and_retrieval(
        self,
        mock_all_services,
        mock_video_data
    ):
        """Test creating download task and retrieving from queue."""
        from src.domain.entities.download_task import DownloadTask
        
        # Create download task
        task = DownloadTask(
            chat_id=123456,
            user_id=123456,
            username='test_user',
            video_id=mock_video_data['video_id'],
            url=mock_video_data['url'],
            quality='720'
        )
        
        # Add to queue
        added = await mock_all_services['queue_service'].add_to_queue(task)
        assert added is True
        
        # Get queue status
        status = mock_all_services['queue_service'].get_queue_status()
        assert status['queue_length'] >= 1
        
        # Remove from queue
        removed = await mock_all_services['queue_service'].remove_from_queue(task.task_id)
        assert removed is True
    
    @pytest.mark.asyncio
    async def test_cache_service_save_and_retrieve(
        self,
        mock_video_repository,
        mock_video_data
    ):
        """Test saving to cache and retrieving."""
        from src.application.services.cache_service import CacheService
        
        # Setup repository
        mock_video_repository.is_cached = AsyncMock(return_value=False)
        mock_video_repository.save = AsyncMock(return_value=True)
        mock_video_repository.get_by_video_id_and_quality = AsyncMock(return_value=MagicMock(
            telegram_file_id='file_123',
            file_size=1024000,
            extension='mp4'
        ))
        
        # Create cache service
        cache_service = CacheService(mock_video_repository)
        
        # Save to cache
        saved = await cache_service.save_to_cache(
            video_id=mock_video_data['video_id'],
            quality='720',
            file_id='file_720p',
            file_size=5242880,
            title=mock_video_data['title']
        )
        assert saved is True
        
        # Check if cached
        is_cached = await cache_service.is_cached(mock_video_data['video_id'], '720')
        assert is_cached is True
        
        # Get cached file
        cached = await cache_service.get_cached_file(mock_video_data['video_id'], '720')
        assert cached is not None
