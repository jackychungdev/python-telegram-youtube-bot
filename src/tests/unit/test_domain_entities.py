"""
Unit Tests for Domain Entities

Tests for User, Video, and DownloadTask entities.
"""
import pytest
from datetime import datetime
from src.domain.entities.user import User
from src.domain.entities.video import Video, VideoFormat
from src.domain.entities.download_task import DownloadTask
from src.domain.value_objects.video_quality import VideoQuality
from src.domain.value_objects.download_status import DownloadStatus


class TestUser:
    """Test cases for User entity."""
    
    def test_create_user(self, mock_user_data):
        """Test user creation with valid data."""
        user = User(
            user_id=mock_user_data['user_id'],
            username=mock_user_data['username']
        )
        
        assert user.user_id == mock_user_data['user_id']
        assert user.username == mock_user_data['username']
        assert user.downloads_in_hour == 0
        assert user.last_video_url is None
    
    def test_user_can_download_within_limit(self):
        """Test rate limiting allows downloads under limit."""
        user = User(user_id=123, username='test')
        
        # Should allow when under limit
        assert user.can_download(limit_per_hour=10) is True
        
        # Increment to limit
        for _ in range(5):
            user.increment_downloads()
        
        # Should still allow (5 < 10)
        assert user.can_download(limit_per_hour=10) is True
    
    def test_user_blocked_when_over_limit(self):
        """Test rate limiting blocks downloads at/over limit."""
        user = User(user_id=123, username='test')
        
        # Increment to limit
        for _ in range(10):
            user.increment_downloads()
        
        # Should block at limit
        assert user.can_download(limit_per_hour=10) is False
    
    def test_user_update_activity(self):
        """Test user activity update (replaces update_username)."""
        user = User(user_id=123, username='old_name')
        
        user.update_activity(username='new_name')
        
        assert user.username == 'new_name'
    
    def test_user_increment_downloads(self):
        """Test download counter increment."""
        user = User(user_id=123, username='test')
        
        initial_count = user.downloads_in_hour
        
        user.increment_downloads()
        
        assert user.downloads_in_hour == initial_count + 1


class TestVideo:
    """Test cases for Video entity."""
    
    def test_create_video(self, mock_video_data):
        """Test video creation with valid data."""
        video = Video(
            video_id=mock_video_data['video_id'],
            title=mock_video_data['title'],
            uploader=mock_video_data['uploader'],
            uploader_url=mock_video_data.get('uploader_url', 'https://youtube.com/channel/test'),
            duration=mock_video_data['duration'],
            thumbnail_url=mock_video_data.get('thumbnail_url', 'https://i.ytimg.com/vi/test/maxresdefault.jpg')
        )
        
        assert video.video_id == mock_video_data['video_id']
        assert video.title == mock_video_data['title']
        assert video.uploader == mock_video_data['uploader']
        assert video.duration == mock_video_data['duration']
    
    def test_video_get_formats_for_quality(self, mock_video_data):
        """Test format selection for specific quality (replaces get_best_format_for_quality)."""
        video = Video(
            video_id=mock_video_data['video_id'],
            title=mock_video_data['title'],
            uploader=mock_video_data['uploader'],
            uploader_url=mock_video_data.get('uploader_url', 'https://youtube.com/channel/test'),
            duration=mock_video_data['duration'],
            thumbnail_url=mock_video_data.get('thumbnail_url', 'https://i.ytimg.com/vi/test/maxresdefault.jpg')
        )
        
        # Add some formats
        format_720 = VideoFormat(
            format_id='720',
            height=720,
            width=1280,
            ext='mp4',
            vcodec='h264',
            acodec='aac'
        )
        
        format_1080 = VideoFormat(
            format_id='1080',
            height=1080,
            width=1920,
            ext='mp4',
            vcodec='h264',
            acodec='aac'
        )
        
        video.formats = [format_720, format_1080]
        
        # Get formats for 720p quality
        formats = video.get_formats_for_quality(VideoQuality.Q720)
        
        assert len(formats) > 0
        # Should include formats with height <= 720
        assert all(fmt.height <= 720 for fmt in formats if fmt.height)
    
    def test_video_available_qualities(self, mock_video_data):
        """Test available qualities extraction."""
        video = Video(
            video_id=mock_video_data['video_id'],
            title=mock_video_data['title'],
            uploader=mock_video_data['uploader'],
            uploader_url=mock_video_data.get('uploader_url', 'https://youtube.com/channel/test'),
            duration=mock_video_data['duration'],
            thumbnail_url=mock_video_data.get('thumbnail_url', 'https://i.ytimg.com/vi/test/maxresdefault.jpg')
        )
        
        # Add formats with different heights
        video.formats = [
            VideoFormat(format_id='1', height=360, ext='mp4', vcodec='h264', acodec='aac'),
            VideoFormat(format_id='2', height=720, ext='mp4', vcodec='h264', acodec='aac'),
            VideoFormat(format_id='3', height=1080, ext='mp4', vcodec='h264', acodec='aac'),
        ]
        
        qualities = video.available_qualities
        
        assert len(qualities) > 0
        # Check that expected qualities are present using correct enum names (Q prefix, not P)
        quality_values = [q.value for q in qualities]
        assert '360' in quality_values or '720' in quality_values


class TestVideoFormat:
    """Test cases for VideoFormat value object."""
    
    def test_create_video_format(self):
        """Test format creation."""
        fmt = VideoFormat(
            format_id='test',
            height=720,
            width=1280,
            ext='mp4',
            vcodec='h264',
            acodec='aac'
        )
        
        assert fmt.height == 720
        assert fmt.width == 1280
        assert fmt.ext == 'mp4'
    
    def test_format_has_video(self):
        """Test video detection using is_video property."""
        fmt_with_video = VideoFormat(
            format_id='test',
            height=720,
            width=1280,
            ext='mp4',
            vcodec='h264',
            acodec='aac'
        )
        
        fmt_without_video = VideoFormat(
            format_id='test',
            height=720,
            ext='mp4',
            vcodec='none',
            acodec='aac'
        )
        
        assert fmt_with_video.is_video is True
        assert fmt_without_video.is_video is False
    
    def test_format_has_audio(self):
        """Test audio detection using is_audio property."""
        fmt_with_audio = VideoFormat(
            format_id='test',
            height=720,
            ext='mp4',
            vcodec='none',
            acodec='aac'
        )
        
        fmt_without_audio = VideoFormat(
            format_id='test',
            height=720,
            ext='mp4',
            vcodec='h264',
            acodec='none'
        )
        
        assert fmt_with_audio.is_audio is True
        assert fmt_without_audio.is_audio is False


class TestDownloadTask:
    """Test cases for DownloadTask entity."""
    
    def test_create_download_task(self, mock_download_task_data):
        """Test task creation with valid data."""
        task = DownloadTask(
            chat_id=mock_download_task_data['chat_id'],
            user_id=mock_download_task_data['user_id'],
            username=mock_download_task_data['username'],
            video_id=mock_download_task_data['video_id'],
            url=mock_download_task_data['url'],
            quality=mock_download_task_data['quality']
        )
        
        assert task.chat_id == mock_download_task_data['chat_id']
        assert task.video_id == mock_download_task_data['video_id']
        assert task.quality == mock_download_task_data['quality']
        assert task.status.value == DownloadStatus.PENDING.value
        assert task.progress_percent == 0
    
    def test_task_mark_started(self, mock_download_task_data):
        """Test marking task as started."""
        task = DownloadTask(**mock_download_task_data)
        
        task.mark_started()
        
        assert task.status.value == DownloadStatus.DOWNLOADING.value
        assert task.started_at is not None
    
    def test_task_mark_completed(self, mock_download_task_data):
        """Test marking task as completed."""
        task = DownloadTask(**mock_download_task_data)
        
        task.mark_completed()
        
        assert task.status.value == DownloadStatus.COMPLETED.value
        assert task.completed_at is not None
    
    def test_task_mark_failed(self, mock_download_task_data):
        """Test marking task as failed."""
        task = DownloadTask(**mock_download_task_data)
        
        error_msg = "Test error"
        task.mark_failed(error_msg)
        
        assert task.status.value == DownloadStatus.FAILED.value
        assert task.error_message == error_msg
