"""
Metadata Probe Utility

Media file metadata extraction using ffprobe/ffmpeg.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List


logger = logging.getLogger(__name__)


class MetadataProbe:
    """Utility for extracting media metadata.
    
    Uses ffprobe to extract detailed information:
    - Duration and format
    - Video streams (codec, resolution, bitrate)
    - Audio streams (codec, channels, sample rate)
    - Container information
    
    Attributes:
        ffprobe_path: Path to ffprobe executable
        timeout: Command timeout in seconds
    """
    
    def __init__(self, ffprobe_path: str = 'ffprobe', timeout: int = 10):
        """Initialize metadata probe.
        
        Args:
            ffprobe_path: Path to ffprobe executable
            timeout: Command timeout in seconds
        """
        self.ffprobe_path = ffprobe_path
        self.timeout = timeout
        self._available = None
    
    async def is_available(self) -> bool:
        """Check if ffprobe is available.
        
        Returns:
            True if ffprobe is accessible
        """
        if self._available is not None:
            return self._available
        
        try:
            process = await asyncio.create_subprocess_exec(
                self.ffprobe_path,
                '-version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            self._available = process.returncode == 0
            return self._available
            
        except Exception as e:
            logger.debug(f"ffprobe not available: {e}")
            self._available = False
            return False
    
    async def probe(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Probe media file and extract metadata.
        
        Args:
            file_path: Path to media file
            
        Returns:
            Dictionary with metadata or None if failed
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                logger.error(f"File does not exist: {file_path}")
                return None
            
            # Build ffprobe command
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(path)
            ]
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )
            
            if process.returncode != 0:
                logger.error(f"ffprobe failed: {stderr.decode()}")
                return None
            
            # Parse JSON output
            data = json.loads(stdout.decode())
            return self._parse_probe_data(data)
            
        except asyncio.TimeoutError:
            logger.error(f"ffprobe timeout for {file_path}")
            return None
        except Exception as e:
            logger.error(f"Failed to probe file: {e}")
            return None
    
    def _parse_probe_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse ffprobe JSON output.
        
        Args:
            data: Raw ffprobe JSON data
            
        Returns:
            Parsed metadata dictionary
        """
        result = {
            'format': {},
            'video_streams': [],
            'audio_streams': [],
            'other_streams': []
        }
        
        # Parse format info
        if 'format' in data:
            fmt = data['format']
            result['format'] = {
                'duration': float(fmt.get('duration') or 0),
                'size': int(fmt.get('size') or 0),
                'bitrate': int(fmt.get('bit_rate') or 0),
                'format_name': fmt.get('format_name', 'unknown'),
                'format_long_name': fmt.get('format_long_name', 'unknown'),
            }
        
        # Parse streams
        for stream in data.get('streams', []):
            codec_type = stream.get('codec_type')
            
            if codec_type == 'video':
                video_info = self._parse_video_stream(stream)
                result['video_streams'].append(video_info)
            elif codec_type == 'audio':
                audio_info = self._parse_audio_stream(stream)
                result['audio_streams'].append(audio_info)
            else:
                result['other_streams'].append({
                    'codec_type': codec_type,
                    'codec_name': stream.get('codec_name', 'unknown')
                })
        
        return result
    
    def _parse_video_stream(self, stream: Dict[str, Any]) -> Dict[str, Any]:
        """Parse video stream information.
        
        Args:
            stream: Stream data from ffprobe
            
        Returns:
            Parsed video stream info
        """
        return {
            'index': stream.get('index', 0),
            'codec_name': stream.get('codec_name', 'unknown'),
            'codec_long_name': stream.get('codec_long_name', 'unknown'),
            'width': stream.get('width', 0),
            'height': stream.get('height', 0),
            'aspect_ratio': stream.get('display_aspect_ratio', 'unknown'),
            'fps': self._parse_fps(stream),
            'bitrate': int(stream.get('bit_rate') or 0),
            'pix_fmt': stream.get('pix_fmt', 'unknown'),
            'has_alpha': stream.get('has_b_frames', 0) > 0,
        }
    
    def _parse_audio_stream(self, stream: Dict[str, Any]) -> Dict[str, Any]:
        """Parse audio stream information.
        
        Args:
            stream: Stream data from ffprobe
            
        Returns:
            Parsed audio stream info
        """
        return {
            'index': stream.get('index', 0),
            'codec_name': stream.get('codec_name', 'unknown'),
            'codec_long_name': stream.get('codec_long_name', 'unknown'),
            'channels': stream.get('channels', 0),
            'sample_rate': int(stream.get('sample_rate') or 0),
            'bitrate': int(stream.get('bit_rate') or 0),
            'channel_layout': stream.get('channel_layout', 'unknown'),
        }
    
    @staticmethod
    def _parse_fps(stream: Dict[str, Any]) -> float:
        """Parse FPS from stream data.
        
        Args:
            stream: Stream data from ffprobe
            
        Returns:
            FPS as float
        """
        fps_str = stream.get('r_frame_rate', '0/0')
        
        try:
            num, denom = map(int, fps_str.split('/'))
            if denom == 0:
                return 0.0
            return num / denom
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    async def get_duration(self, file_path: Path) -> Optional[float]:
        """Get media file duration in seconds.
        
        Args:
            file_path: Path to media file
            
        Returns:
            Duration in seconds or None
        """
        data = await self.probe(file_path)
        
        if data and 'format' in data:
            return data['format'].get('duration')
        
        return None
    
    async def get_resolution(self, file_path: Path) -> Optional[tuple]:
        """Get video resolution (width x height).
        
        Args:
            file_path: Path to media file
            
        Returns:
            Tuple of (width, height) or None
        """
        data = await self.probe(file_path)
        
        if data and data['video_streams']:
            video = data['video_streams'][0]
            return (video['width'], video['height'])
        
        return None
    
    async def has_video(self, file_path: Path) -> bool:
        """Check if file has video streams.
        
        Args:
            file_path: Path to media file
            
        Returns:
            True if file contains video
        """
        data = await self.probe(file_path)
        
        if data and data['video_streams']:
            return True
        
        return False
    
    async def has_audio(self, file_path: Path) -> bool:
        """Check if file has audio streams.
        
        Args:
            file_path: Path to media file
            
        Returns:
            True if file contains audio
        """
        data = await self.probe(file_path)
        
        if data and data['audio_streams']:
            return True
        
        return False
    
    async def get_video_codec(self, file_path: Path) -> Optional[str]:
        """Get video codec name.
        
        Args:
            file_path: Path to media file
            
        Returns:
            Codec name or None
        """
        data = await self.probe(file_path)
        
        if data and data['video_streams']:
            return data['video_streams'][0].get('codec_name')
        
        return None
    
    async def get_audio_codec(self, file_path: Path) -> Optional[str]:
        """Get audio codec name.
        
        Args:
            file_path: Path to media file
            
        Returns:
            Codec name or None
        """
        data = await self.probe(file_path)
        
        if data and data['audio_streams']:
            return data['audio_streams'][0].get('codec_name')
        
        return None
