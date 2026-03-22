"""
Pytest Configuration

Shared fixtures and pytest hooks for all tests.
"""
import pytest
import asyncio
import sys
from pathlib import Path


# Add src to path for imports
src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(src_path))


@pytest.fixture(scope='session')
def event_loop():
    """Create event loop for async tests.
    
    Yields:
        Asyncio event loop
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def reset_async_state():
    """Reset async state between tests.
    
    Yields:
        Control to test
    """
    # Setup: nothing needed
    yield
    # Teardown: cancel any pending tasks
    loop = asyncio.get_event_loop()
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()
    # Run until all tasks are cancelled
    if pending:
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
