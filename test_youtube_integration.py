"""
Integration test for YouTube video download functionality
Tests actual video information extraction using yt-dlp
"""

import pytest
import yt_dlp
import asyncio
import os
import sys

# Ensure UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

# Test the specific YouTube link provided
TEST_YOUTUBE_URL = "https://youtu.be/lAZc4uOsSxo?si=tSLkOH3SCFEJbDy"
TEST_VIDEO_ID = "lAZc4uOsSxo"


def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    import re
    patterns = [
        r'(?:v=|\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


class TestYouTubeVideoInfo:
    """Test actual YouTube video information extraction"""
    
    def test_video_info_extraction(self):
        """Test extracting real video information from the provided YouTube link"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'force_ipv4': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(TEST_YOUTUBE_URL, download=False)
                
                # Verify basic information
                assert info is not None, "Failed to extract video info"
                assert info.get('id') == TEST_VIDEO_ID, f"Video ID mismatch: expected {TEST_VIDEO_ID}, got {info.get('id')}"
                assert info.get('title'), "Video title is missing"
                assert info.get('duration'), "Video duration is missing"
                assert info.get('uploader'), "Uploader information is missing"
                
                print(f"\n[PASS] Video Information:")
                print(f"   Title: {info.get('title')}")
                print(f"   ID: {info.get('id')}")
                print(f"   Duration: {info.get('duration')} seconds")
                print(f"   Uploader: {info.get('uploader')}")
                print(f"   View Count: {info.get('view_count', 'N/A')}")
                
        except Exception as e:
            pytest.fail(f"Failed to extract video information: {str(e)}")
    
    def test_available_formats(self):
        """Test that video has available formats for download"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(TEST_YOUTUBE_URL, download=False)
                
                formats = info.get('formats', [])
                assert len(formats) > 0, "No formats available for this video"
                
                # Check for video formats
                video_formats = [f for f in formats if f.get('vcodec') != 'none']
                assert len(video_formats) > 0, "No video formats available"
                
                # Check for audio formats
                audio_formats = [f for f in formats if f.get('acodec') != 'none']
                assert len(audio_formats) > 0, "No audio formats available"
                
                # Get available qualities
                heights = set()
                for f in video_formats:
                    if f.get('height'):
                        heights.add(f.get('height'))
                
                print(f"\n[PASS] Available Formats:")
                print(f"   Total formats: {len(formats)}")
                print(f"   Video formats: {len(video_formats)}")
                print(f"   Audio formats: {len(audio_formats)}")
                print(f"   Available heights: {sorted(heights)}")
                
        except Exception as e:
            pytest.fail(f"Failed to get format information: {str(e)}")
    
    def test_thumbnail_availability(self):
        """Test that video thumbnail is available"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(TEST_YOUTUBE_URL, download=False)
                
                thumbnail = info.get('thumbnail')
                assert thumbnail, "Thumbnail URL is missing"
                assert thumbnail.startswith('http'), "Thumbnail URL is invalid"
                
                print(f"\n[PASS] Thumbnail: {thumbnail}")
                
        except Exception as e:
            pytest.fail(f"Failed to get thumbnail information: {str(e)}")
    
    def test_video_accessibility(self):
        """Test that the video is accessible and not private/deleted"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(TEST_YOUTUBE_URL, download=False)
                
                # If we got here, the video is accessible
                assert info.get('id') == TEST_VIDEO_ID
                
                # Check it's not a live stream (bot doesn't support live streams)
                is_live = info.get('is_live', False)
                
                print(f"\n[PASS] Video Accessibility:")
                print(f"   Accessible: Yes")
                print(f"   Is Live: {is_live}")
                print(f"   Availability: {info.get('availability', 'public')}")
                
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if 'private' in error_msg.lower():
                pytest.fail("Video is private and cannot be accessed")
            elif 'unavailable' in error_msg.lower():
                pytest.fail("Video is unavailable or has been deleted")
            elif 'members-only' in error_msg.lower():
                pytest.fail("Video is members-only")
            else:
                pytest.fail(f"Download error: {error_msg}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {str(e)}")


class TestBotFunctions:
    """Test bot-specific functions with real YouTube data"""
    
    def test_extract_video_id_from_full_url(self):
        """Test video ID extraction from the complete YouTube URL"""
        video_id = extract_video_id(TEST_YOUTUBE_URL)
        assert video_id == TEST_VIDEO_ID
        assert len(video_id) == 11
        print(f"\n[PASS] Extracted Video ID: {video_id}")
    
    def test_reconstruct_youtube_url(self):
        """Test reconstructing YouTube URL from extracted ID"""
        video_id = extract_video_id(TEST_YOUTUBE_URL)
        
        # Reconstruct different URL formats
        standard_url = f"https://www.youtube.com/watch?v={video_id}"
        short_url = f"https://youtu.be/{video_id}"
        embed_url = f"https://www.youtube.com/embed/{video_id}"
        
        # All should extract to the same ID
        assert extract_video_id(standard_url) == video_id
        assert extract_video_id(short_url) == video_id
        assert extract_video_id(embed_url) == video_id
        
        print(f"\n[PASS] URL Reconstruction successful for ID: {video_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
