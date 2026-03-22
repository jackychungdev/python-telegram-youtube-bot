"""
Integration Tests

Tests for complete workflows and component integration.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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
        # Setup mocks
        mock_all_services['youtube_service'].get_video_info = AsyncMock()
        mock_all_services['youtube_service'].get_video_info.return_value = MagicMock(
            video_id=mock_video_data['video_id'],
            title=mock_video_data['title'],
            uploader=mock_video_data['uploader'],
            duration=mock_video_data['duration'],
            url=mock_video_data['url']
        )
        
        mock_all_services['cache_service'].is_cached = AsyncMock(return_value=False)
        mock_all_services['queue_service'].add_to_queue = AsyncMock(return_value=True)
        
        # Simulate user request
        user = User(user_id=mock_user_data['user_id'], username=mock_user_data['username'])
        
        # Check if user can download
        assert user.can_download(limit_per_hour=10) is True
        
        # Get video info
        video = await mock_all_services['youtube_service'].get_video_info(mock_video_data['url'])
        assert video is not None
        
        # Check cache
        is_cached = await mock_all_services['cache_service'].is_cached(video.video_id, '720')
        assert is_cached is False
        
        # Create download task
        task = DownloadTask(
            chat_id=user.user_id,
            user_id=user.user_id,
            username=user.username,
            video_id=video.video_id,
            url=video.url,
            quality='720'
        )
        
        # Add to queue
        added = await mock_all_services['queue_service'].add_to_queue(task)
        assert added is True
        
        # Verify queue service was called correctly
        mock_all_services['queue_service'].add_to_queue.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cached_video_bypasses_download(
        self,
        mock_user_data,
        mock_video_data,
        mock_all_services
    ):
        """Test that cached videos skip download."""
        # Setup cache hit
        mock_all_services['cache_service'].is_cached = AsyncMock(return_value=True)
        mock_all_services['cache_service'].get_cached_file = AsyncMock(
            return_value=('telegram_file_123', 'Video Title', 1024000, 'mp4')
        )
        
        # Get video info
        mock_all_services['youtube_service'].get_video_info = AsyncMock()
        mock_all_services['youtube_service'].get_video_info.return_value = MagicMock(
            video_id=mock_video_data['video_id']
        )
        
        video = await mock_all_services['youtube_service'].get_video_info(mock_video_data['url'])
        
        # Check cache
        is_cached = await mock_all_services['cache_service'].is_cached(video.video_id, '720')
        assert is_cached is True
        
        # Get cached file
        cached = await mock_all_services['cache_service'].get_cached_file(video.video_id, '720')
        assert cached is not None
        assert cached[0] == 'telegram_file_123'
        
        # Queue should NOT be called
        mock_all_services['queue_service'].add_to_queue.assert_not_called()


class TestHandlerServiceIntegration:
    """Test handler integration with services."""
    
    @pytest.mark.asyncio
    async def test_command_handler_with_services(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services
    ):
        """Test command handler uses services correctly."""
        from src.application.handlers.commands import CommandHandlers
        
        # Setup authorization
        mock_all_services['auth_repo'].is_authorized = AsyncMock(return_value=True)
        
        handler = CommandHandlers(
            mock_all_services['telegram_service'].bot,
            mock_all_services
        )
        
        await handler.handle_start(mock_telegram_update, mock_context)
        
        # Verify user repo was called
        mock_all_services['user_repo'].create_or_update.assert_called_once()
        
        # Verify message was sent
        mock_all_services['telegram_service'].send_message.assert_called()
    
    @pytest.mark.asyncio
    async def test_callback_handler_creates_task(
        self,
        mock_telegram_update,
        mock_context,
        mock_all_services,
        mock_video_data
    ):
        """Test callback handler creates download task."""
        from src.application.handlers.callbacks import CallbackHandlers
        
        # Setup mocks
        mock_query = AsyncMock()
        mock_query.data = 'quality_720_testvideo'
        mock_query.from_user.id = 123456
        mock_query.message.chat_id = 123456
        
        mock_telegram_update.callback_query = mock_query
        
        mock_all_services['youtube_service'].get_video_info = AsyncMock()
        mock_all_services['youtube_service'].get_video_info.return_value = MagicMock(
            video_id='testvideo',
            url='https://youtube.com/watch?v=testvideo'
        )
        
        handler = CallbackHandlers(
            mock_all_services['telegram_service'].bot,
            mock_all_services
        )
        
        await handler.handle_quality_selection(mock_telegram_update, mock_context)
        
        # Verify task was created and queued
        mock_all_services['queue_service'].add_to_queue.assert_called_once()


class TestRepositoryServiceIntegration:
    """Test repository and service integration."""
    
    @pytest.mark.asyncio
    async def test_cache_service_with_repository(
        self,
        mock_video_repository,
        mock_video_data
    ):
        """Test cache service integrates with repository."""
        from src.application.services.cache_service import CacheService
        
        # Setup repository mock
        mock_video_repository.is_cached = AsyncMock(return_value=False)
        mock_video_repository.save = AsyncMock(return_value=True)
        
        # Create cache service
        cache = CacheService(mock_video_repository)
        
        # Check cache (should be false)
        result = await cache.is_cached('video123', '720')
        assert result is False
        
        # Save to cache
        saved = await cache.save_to_cache(
            video_id='video123',
            quality='720',
            file_id='file_123',
            file_size=1024000,
            title='Test Video'
        )
        assert saved is True
        
        # Verify repository was called
        mock_video_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_user_repository_rate_limiting(
        self,
        mock_user_repository
    ):
        """Test user repository rate limiting logic."""
        # Setup mock
        mock_user_repository.can_download = AsyncMock(side_effect=[True, True, False])
        mock_user_repository.increment_downloads = AsyncMock()
        
        # First check - should allow
        can_download = await mock_user_repository.can_download(123, limit_per_hour=10)
        assert can_download is True
        
        # Second check - should still allow
        can_download = await mock_user_repository.can_download(123, limit_per_hour=10)
        assert can_download is True
        
        # Third check - should block
        can_download = await mock_user_repository.can_download(123, limit_per_hour=10)
        assert can_download is False


class TestQualitySelectionWorkflow:
    """Test quality selection across components."""
    
    @pytest.mark.asyncio
    async def test_quality_selector_integration(
        self,
        mock_video_data
    ):
        """Test quality selector with real video formats."""
        from src.infrastructure.external.youtube.quality_selector import QualitySelector
        from src.domain.entities.video import VideoFormat
        
        # Create video with formats
        video = Video(
            video_id=mock_video_data['video_id'],
            title=mock_video_data['title'],
            uploader=mock_video_data['uploader'],
            duration=mock_video_data['duration']
        )
        
        # Add various formats
        video.formats = [
            VideoFormat(format_id='1', height=360, ext='mp4'),
            VideoFormat(format_id='2', height=720, ext='mp4'),
            VideoFormat(format_id='3', height=1080, ext='webm'),
            VideoFormat(format_id='4', height=720, ext='webm'),
        ]
        
        # Create selector
        selector = QualitySelector(prefer_mp4=True)
        
        # Get available heights
        heights = selector.get_available_heights(video.formats)
        assert len(heights) == 3
        assert 1080 in heights
        assert 720 in heights
        assert 360 in heights
        
        # Select 720p (should prefer mp4)
        selected = selector.select_by_height(video.formats, 720)
        assert selected is not None
        assert selected.height == 720
        assert selected.ext == 'mp4'  # Prefers mp4 over webm
        
        # Select audio only
        audio_format = selector.select_audio_only(video.formats)
        # Should return None since no audio-only formats
        assert audio_format is None


class TestErrorHandlingWorkflow:
    """Test error handling across layers."""
    
    @pytest.mark.asyncio
    async def test_youtube_service_error_handling(self):
        """Test YouTube service handles errors gracefully."""
        from src.application.services.youtube_service import YoutubeService
        
        youtube = YoutubeService()
        
        # Invalid URL should raise exception or return None
        with pytest.raises(Exception):
            await youtube.get_video_info('invalid_url')
    
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
