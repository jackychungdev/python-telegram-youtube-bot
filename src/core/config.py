"""
Configuration management module

Handles loading and accessing configuration from YAML files.
Provides type-safe access to bot settings.
"""
import os
import yaml
from pathlib import Path
from typing import Any, Dict


class Config:
    """Configuration manager for the bot."""
    
    def __init__(self, config_path: str = None):
        """Initialize configuration from YAML file.
        
        Args:
            config_path: Path to config.yaml file. Defaults to config/config.yaml
        """
        if config_path is None:
            # Look for config in parent directory's config folder
            config_path = Path(__file__).parent.parent.parent / 'config' / 'config.yaml'
        
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        self._config: Dict[str, Any] = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file.
        
        Returns:
            Dictionary containing all configuration values
        """
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key.
        
        Args:
            key: Dot-separated key path (e.g., 'bot.TOKEN')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    @property
    def bot(self) -> Dict[str, Any]:
        """Get bot configuration section."""
        return self._config.get('bot', {})
    
    @property
    def download(self) -> Dict[str, Any]:
        """Get download configuration section."""
        return self._config.get('download', {})
    
    @property
    def features(self) -> Dict[str, Any]:
        """Get features configuration section."""
        return self._config.get('features', {})
    
    @property
    def logging_conf(self) -> Dict[str, Any]:
        """Get logging configuration section."""
        return self._config.get('logging', {})
