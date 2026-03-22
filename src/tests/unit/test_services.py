"""
Unit Tests for Service Layer

Tests for YouTube, Download, Cache, and other services.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.application.services.youtube_service import YoutubeService
from src.application.services.cache_service import CacheService
from src.application.services.download_service import DownloadService
from src.domain.entities.video import Video
from src.domain.value_objects.video_quality import VideoQuality


class TestYoutubeService:
    """Test cases for YoutubeService."""
    
    @pytest.mark.asyncio
    async def test_get_video_info(self, mock_video_data):
        """Test fetching video information."""
        youtube = YoutubeService()
        
        # Prepare mock data with yt-dlp format (uses 'id' not 'video_id')
        ytdlp_mock_data = {
            'id': mock_video_data['video_id'],
            'title': mock_video_data['title'],
            'uploader': mock_video_data['uploader'],
            'uploader_url': mock_video_data.get('uploader_url', ''),
            'duration': mock_video_data['duration'],
            'thumbnail': mock_video_data.get('thumbnail_url', ''),
            'description': mock_video_data.get('description'),
            'view_count': mock_video_data.get('view_count'),
            'upload_date': mock_video_data.get('upload_date'),
            'formats': []
        }
        
        # Mock yt_dlp extraction - need to patch the correct import path
        with patch('src.application.services.youtube_service.yt_dlp.YoutubeDL') as MockYDL:
            mock_ydl_instance = MagicMock()
            
            # Setup context manager
            mock_context_manager = MagicMock()
            mock_context_manager.__enter__ = MagicMock(return_value=mock_ydl_instance)
            mock_context_manager.__exit__ = MagicMock(return_value=None)
            MockYDL.return_value = mock_context_manager
            
            # Mock extract_info to return our data
            mock_ydl_instance.extract_info.return_value = ytdlp_mock_data
            
            # Create async mock for run_in_executor that actually calls the lambda
            async def mock_run_in_executor(executor, func):
                # Call the lambda function to get the result
                return func()
            
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value.run_in_executor = mock_run_in_executor
                
                video = await youtube.get_video_info('https://youtube.com/watch?v=test')
                
                assert isinstance(video, Video)
                assert video.video_id == mock_video_data['video_id']
                assert video.title == mock_video_data['title']
    
    @pytest.mark.asyncio
    async def test_happy_flow_youtube_link(self):
        """Test complete happy flow with real YouTube link.
        
        This test verifies the end-to-end flow of:
        1. URL validation
        2. Video ID extraction
        3. Format selection logic
        
        Note: Actual video fetching requires network access and is tested separately.
        
        Args:
            None
            
        Returns:
            None
        """
        youtube = YoutubeService()
        test_url = 'https://youtu.be/_v5BQZdM1ro?si=9Qiy6_aV8fC7_v-1'
        
        # Step 1: Validate URL
        assert youtube.validate_url(test_url) is True, "URL should be valid"
        
        # Step 2: Extract video ID from URL
        video_id = youtube.extract_video_id(test_url)
        assert video_id == '_v5BQZdM1ro', f"Expected video ID '_v5BQZdM1ro', got {video_id}"
        
        # Step 3: Test quality format selection with mock Video entity
        mock_video = Video(
            video_id='_v5BQZdM1ro',
            title='Test Video - Happy Flow',
            uploader='Test Channel',
            uploader_url='https://youtube.com/channel/test',
            duration=180.5,
            thumbnail_url='https://i.ytimg.com/vi/_v5BQZdM1ro/maxresdefault.jpg'
        )
        
        # Add some mock formats for testing
        from src.domain.entities.video import VideoFormat
        mock_video.formats = [
            VideoFormat(format_id='720', height=720, width=1280, ext='mp4', vcodec='h264', acodec='aac'),
            VideoFormat(format_id='1080', height=1080, width=1920, ext='mp4', vcodec='h264', acodec='aac')
        ]
        
        # Select best quality
        best_quality = youtube.select_best_quality_format(mock_video, 'best')
        assert best_quality is not None, "Should select a quality format"
        assert hasattr(best_quality, 'height'), "Should return VideoFormat object"
        
        # Step 4: Verify Video entity properties
        assert mock_video.video_id == '_v5BQZdM1ro'
        assert mock_video.title == 'Test Video - Happy Flow'
        assert mock_video.duration > 0
        assert 'youtube' in mock_video.thumbnail_url or 'ytimg' in mock_video.thumbnail_url
    
    def test_validate_url_valid(self):
        """Test URL validation with valid URLs."""
        youtube = YoutubeService()
        
        valid_urls = [
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtu.be/dQw4w9WgXcQ',
            'http://youtube.com/watch?v=dQw4w9WgXcQ',
        ]
        
        for url in valid_urls:
            assert youtube.validate_url(url) is True
    
    def test_validate_url_invalid(self):
        """Test URL validation with invalid URLs."""
        youtube = YoutubeService()
        
        invalid_urls = [
            'not a url',
            'https://example.com',
            '',
        ]
        
        for url in invalid_urls:
            assert youtube.validate_url(url) is False, f"URL '{url}' should be invalid"

    def test_extract_video_id_from_youtube_url(self):
        """Test video ID extraction from YouTube URLs."""
        youtube = YoutubeService()
        
        test_cases = [
            ('https://www.youtube.com/watch?v=abc123', 'abc123'),
            ('https://youtu.be/xyz789', 'xyz789'),
            ('https://youtube.com/watch?v=test123&list=PL123', 'test123'),
        ]
        
        for url, expected_id in test_cases:
            assert youtube.extract_video_id(url) == expected_id
    
    def test_select_best_quality_format(self, mock_video_data):
        """Test format selection for specific quality."""
        youtube = YoutubeService()
        
        video = Video(
            video_id=mock_video_data['video_id'],
            title=mock_video_data['title'],
            uploader=mock_video_data['uploader'],
            uploader_url=mock_video_data.get('uploader_url', 'https://youtube.com/channel/test'),
            duration=mock_video_data['duration'],
            thumbnail_url=mock_video_data.get('thumbnail_url', 'https://i.ytimg.com/vi/test/maxresdefault.jpg')
        )
        
        # Add test formats
        from src.domain.entities.video import VideoFormat
        
        video.formats = [
            VideoFormat(format_id='360', height=360, ext='mp4', vcodec='h264', acodec='aac'),
            VideoFormat(format_id='720', height=720, ext='mp4', vcodec='h264', acodec='aac'),
            VideoFormat(format_id='1080', height=1080, ext='mp4', vcodec='h264', acodec='aac'),
        ]
        
        # Select 720p format
        selected = youtube.select_best_quality_format(video, '720')
        
        assert selected is not None
        assert selected.height == 720
    
    def test_validate_url_mobile(self):
        """Test URL validation includes mobile URLs."""
        youtube = YoutubeService()
        
        # Mobile URLs should be valid
        assert youtube.validate_url('https://m.youtube.com/watch?v=dQw4w9WgXcQ') is True

class TestCacheService:
    """Test cases for CacheService."""
    
    @pytest.mark.asyncio
    async def test_is_cached_true(self, mock_video_repository):
        """Test cache check when file is cached."""
        mock_video_repository.is_cached = AsyncMock(return_value=True)
        
        cache = CacheService(mock_video_repository)
        
        result = await cache.is_cached('video123', '720')
        
        assert result is True
        mock_video_repository.is_cached.assert_called_once_with('video123', '720')
    
    @pytest.mark.asyncio
    async def test_is_cached_false(self, mock_video_repository):
        """Test cache check when file not cached."""
        mock_video_repository.is_cached = AsyncMock(return_value=False)
        
        cache = CacheService(mock_video_repository)
        
        result = await cache.is_cached('video123', '720')
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_save_to_cache_success(self, mock_video_repository):
        """Test saving file to cache."""
        mock_video_repository.save = AsyncMock(return_value=True)
        
        cache = CacheService(mock_video_repository)
        
        result = await cache.save_to_cache(
            video_id='video123',
            quality='720',
            file_id='telegram_file_123',
            file_size=1024000,
            title='Test Video'
        )
        
        assert result is True
        mock_video_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_cached_qualities(self, mock_video_repository):
        """Test getting cached qualities for video."""
        expected_qualities = ['360', '720', '1080']
        mock_video_repository.get_cached_qualities = AsyncMock(
            return_value=expected_qualities
        )
        
        cache = CacheService(mock_video_repository)
        
        result = await cache.get_cached_qualities('video123')
        
        assert result == expected_qualities
    
    @pytest.mark.asyncio
    async def test_invalidate_cache(self, mock_video_repository):
        """Test cache invalidation."""
        mock_video_repository.delete_cached = AsyncMock(return_value=1)
        
        cache = CacheService(mock_video_repository)
        
        result = await cache.invalidate_cache(video_id='video123', quality='720')
        
        # invalidate_cache returns count, not boolean
        assert result == 1
        mock_video_repository.delete_cached.assert_called_once_with('video123_720')
    
    @pytest.mark.asyncio
    async def test_get_cache_statistics(self, mock_video_repository):
        """Test cache statistics retrieval."""
        expected_stats = {
            'total_files': 100,
            'unique_videos': 50,
            'total_size_mb': 500.5,
            'enabled': True
        }
        mock_video_repository.get_cache_stats = AsyncMock(return_value=expected_stats)
        
        cache = CacheService(mock_video_repository)
        
        result = await cache.get_cache_statistics()
        
        assert result == expected_stats


class TestDownloadService:
    """Test cases for DownloadService."""
    
    @pytest.mark.asyncio
    async def test_register_progress_callback(self):
        """Test progress callback registration."""
        download = DownloadService()
        
        callback = MagicMock()
        
        download.register_progress_callback('task123', callback)
        
        assert 'task123' in download._progress_callbacks
        assert download._progress_callbacks['task123'] == callback
    
    @pytest.mark.asyncio
    async def test_unregister_progress_callback(self):
        """Test progress callback unregistration."""
        download = DownloadService()
        
        callback = MagicMock()
        download.register_progress_callback('task123', callback)
        
        download.unregister_progress_callback('task123')
        
        assert 'task123' not in download._progress_callbacks
    
    def test_get_download_directory(self):
        """Test download directory path."""
        download = DownloadService()
        
        directory = download.get_download_directory()
        
        assert directory is not None
        assert directory.exists() or directory.parent.exists()


class TestHappyFlowIntegration:
    """Integration tests for complete happy flow with YouTube link."""
    
    @pytest.mark.asyncio
    async def test_complete_download_workflow(self, mock_video_data, mock_user_data):
        """Test complete download workflow from URL to task creation.
        
        This test validates the entire happy flow:
        1. User sends YouTube link
        2. URL validation and video info extraction
        3. Quality selection
        4. Download task creation
        5. Progress tracking setup
        
        Args:
            mock_video_data: Mock video metadata fixture
            mock_user_data: Mock user data fixture
            
        Returns:
            None
        """
        # Initialize services
        youtube = YoutubeService()
        download = DownloadService()
        
        test_url = 'https://youtu.be/_v5BQZdM1ro?si=9Qiy6_aV8fC7_v-1'
        user_id = mock_user_data['user_id']
        
        # Step 1: Validate YouTube URL
        assert youtube.validate_url(test_url) is True, "URL should be valid"
        
        # Step 2: Extract video ID
        video_id = youtube.extract_video_id(test_url)
        assert video_id == '_v5BQZdM1ro', "Should extract correct video ID"
        
        # Step 3: Get video information (mocked)
        # Create a mock Video entity directly instead of mocking yt-dlp
        from src.domain.entities.video import Video, VideoFormat
        
        mock_video = Video(
            video_id='_v5BQZdM1ro',
            title='Test Video - Happy Flow',
            uploader='Test Channel',
            uploader_url='https://youtube.com/channel/test',
            duration=180.5,
            thumbnail_url='https://i.ytimg.com/vi/_v5BQZdM1ro/maxresdefault.jpg',
            description='Test video description',
            view_count=1000000,
            upload_date='20240101',
            formats=[
                VideoFormat(format_id='18', height=360, ext='mp4', vcodec='h264', acodec='aac', tbr=500),
                VideoFormat(format_id='22', height=720, ext='mp4', vcodec='h264', acodec='aac', tbr=1500),
                VideoFormat(format_id='137', height=1080, ext='mp4', vcodec='h264', acodec='none', tbr=2500),
            ]
        )
        
        # Mock the get_video_info method to return our mock video (as async)
        async def mock_get_video_info(url):
            return mock_video
        
        # Store original method for restoration
        original_get_video_info = youtube.get_video_info
        youtube.get_video_info = mock_get_video_info
        
        video = await youtube.get_video_info(test_url)
        
        # Assertions - Video entity created correctly
        assert isinstance(video, Video), "Should return Video entity"
        assert video.video_id == '_v5BQZdM1ro', f"Video ID should match, got {video.video_id}"
        assert video.title == 'Test Video - Happy Flow', f"Title should match, got {video.title}"
        assert video.duration == 180.5, f"Duration should match, got {video.duration}"
        assert video.thumbnail_url == 'https://i.ytimg.com/vi/_v5BQZdM1ro/maxresdefault.jpg'
        assert len(video.formats) > 0, f"Should have formats, got {len(video.formats)}"
        
        # Restore original method
        youtube.get_video_info = original_get_video_info

        # Step 4: Select quality format
        selected_quality = youtube.select_best_quality_format(video, 'best')
        assert selected_quality is not None, f"Should select best quality, got {selected_quality}"
        assert hasattr(selected_quality, 'height')
        
        # Step 5: Create download task
        task_id = f"task_{user_id}_{video.video_id}"
        
        # Register progress callback
        progress_callback = MagicMock()
        download.register_progress_callback(task_id, progress_callback)
        
        # Verify callback registered
        assert task_id in download._progress_callbacks
        
        # Note: Progress updates are handled internally by yt-dlp through _progress_hook
        # The DownloadService doesn't have a direct update_progress method
        # Instead, yt-dlp calls the hook during download which then notifies callbacks
        
        # Verify that registering the callback works (the primary functionality we can test)
        assert task_id in download._progress_callbacks, "Callback should be registered"
        
        # Step 7: Cleanup - unregister callback
        download.unregister_progress_callback(task_id)
        assert task_id not in download._progress_callbacks
    
    @pytest.mark.asyncio
    async def test_cache_service_happy_flow(self, mock_video_repository, mock_video_data):
        """Test cache service happy flow.
        
        Validates caching workflow:
        1. Check if video is cached
        2. Cache video metadata
        3. Retrieve cached data
        4. Verify cache statistics
        
        Args:
            mock_video_repository: Mock video repository fixture
            mock_video_data: Mock video data fixture
            
        Returns:
            None
        """
        cache = CacheService(mock_video_repository)
        video_id = '_v5BQZdM1ro'
        quality = '720'
        
        # Step 1: Mock cache miss initially
        mock_video_repository.is_cached = AsyncMock(return_value=False)
        
        is_cached = await cache.is_cached(video_id, quality)
        assert is_cached is False
        
        # Step 2: Mock cache storage
        mock_video_repository.save = AsyncMock(return_value=True)
        mock_video_repository.get_cached_qualities = AsyncMock(return_value=[quality])
        
        # Store in cache using save_to_cache method (not cache_video)
        result = await cache.save_to_cache(
            video_id=video_id,
            quality=quality,
            file_id='telegram_file_123',
            file_size=1024000,
            title=mock_video_data['title']
        )
        
        assert result is True
        mock_video_repository.save.assert_called_once()
        
        # Step 3: Verify cache now has the video
        mock_video_repository.is_cached = AsyncMock(return_value=True)
        
        is_cached = await cache.is_cached(video_id, quality)
        assert is_cached is True
        
        # Step 4: Get cached qualities
        qualities = await cache.get_cached_qualities(video_id)
        assert qualities == [quality]
        assert len(qualities) > 0
    
    def test_url_parsing_various_formats(self):
        """Test URL parsing with various YouTube URL formats.
        
        Validates that the service correctly handles:
        1. Standard youtube.com/watch URLs
        2. Short youtu.be URLs
        3. URLs with additional parameters
        4. Mobile URLs
        
        Returns:
            None
        """
        youtube = YoutubeService()
        
        test_cases = [
            # (URL, Expected Video ID)
            ('https://www.youtube.com/watch?v=_v5BQZdM1ro', '_v5BQZdM1ro'),
            ('https://youtu.be/_v5BQZdM1ro', '_v5BQZdM1ro'),
            ('https://youtu.be/_v5BQZdM1ro?si=9Qiy6_aV8fC7_v-1', '_v5BQZdM1ro'),
            ('http://youtube.com/watch?v=_v5BQZdM1ro', '_v5BQZdM1ro'),
            ('https://m.youtube.com/watch?v=_v5BQZdM1ro', '_v5BQZdM1ro'),
        ]
        
        for url, expected_id in test_cases:
            # Validate URL
            assert youtube.validate_url(url) is True, f"URL should be valid: {url}"
            
            # Extract video ID
            extracted_id = youtube.extract_video_id(url)
            assert extracted_id == expected_id, \
                f"Expected {expected_id} from {url}, got {extracted_id}"


# Run specific test: python -m pytest src/tests/unit/test_services.py::TestHappyFlowIntegration -v
