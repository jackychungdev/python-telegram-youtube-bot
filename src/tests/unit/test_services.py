"""
Unit Tests for Service Layer

Tests for YouTube, Download, Cache, and other services.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.application.services.youtube_service import YoutubeService
from src.application.services.cache_service import CacheService
from src.domain.entities.video import Video


class TestYoutubeService:
    """Test cases for YoutubeService."""
    
    @pytest.mark.asyncio
    async def test_get_video_info(self, mock_video_data):
        """Test fetching video information."""
        youtube = YoutubeService()
        
        # Mock yt_dlp extraction
        with patch('youtube_dl.YoutubeDL.extract_info', new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = mock_video_data
            
            video = await youtube.get_video_info('https://youtube.com/watch?v=test')
            
            assert isinstance(video, Video)
            assert video.video_id == mock_video_data['video_id']
            assert video.title == mock_video_data['title']
    
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
            None,
        ]
        
        for url in invalid_urls:
            assert youtube.validate_url(url) is False
    
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
            duration=mock_video_data['duration']
        )
        
        # Add test formats
        from src.domain.entities.video import VideoFormat
        
        video.formats = [
            VideoFormat(format_id='360', height=360, ext='mp4'),
            VideoFormat(format_id='720', height=720, ext='mp4'),
            VideoFormat(format_id='1080', height=1080, ext='mp4'),
        ]
        
        # Select 720p format
        selected = youtube.select_best_quality_format(video, '720')
        
        assert selected is not None
        assert selected.height == 720


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
        mock_video_repository.delete_cached = AsyncMock(return_value=True)
        
        cache = CacheService(mock_video_repository)
        
        result = await cache.invalidate_cache('video123', '720')
        
        assert result is True
        mock_video_repository.delete_cached.assert_called_once_with('video123', '720')
    
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
