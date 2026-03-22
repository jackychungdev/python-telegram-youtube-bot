"""
Main entry point for the refactored Telegram YouTube Bot

This is the new modular version with layered architecture.
Currently serves as a bridge to the legacy implementation during migration.
"""
import sys
from pathlib import Path

# Add parent directory to path to import legacy modules during migration
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from legacy telegram_youtube_bot.py during migration
# TODO: Replace with new modular implementation in Phase 5-6
from telegram_youtube_bot import main as legacy_main


def main():
    """Main entry point.
    
    Currently delegates to legacy implementation.
    Will be replaced with new modular architecture in later phases.
    """
    # For now, use legacy implementation
    # This will be replaced with new dependency injection setup
    legacy_main()


if __name__ == '__main__':
    main()
