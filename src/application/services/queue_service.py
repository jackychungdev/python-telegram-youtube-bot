"""
Queue Service

Business logic for download queue management, task scheduling, and concurrency control.
"""
import asyncio
import logging
from typing import Optional, List, Dict, Any
from collections import deque
from datetime import datetime

from domain import DownloadTask, DownloadStatus


logger = logging.getLogger(__name__)


class QueueService:
    """Service for managing download queues.
    
    Handles queue operations, task scheduling, and concurrent downloads:
    - Task queue management (FIFO)
    - Priority queue support
    - Concurrency control
    - Progress monitoring
    
    Attributes:
        max_queue_size: Maximum number of tasks in queue
        max_concurrent: Maximum concurrent downloads
        queue: Download task queue
    """
    
    def __init__(
        self,
        max_queue_size: int = 100,
        max_concurrent: int = 3
    ):
        """Initialize queue service.
        
        Args:
            max_queue_size: Maximum queue size
            max_concurrent: Maximum concurrent downloads
        """
        self.max_queue_size = max_queue_size
        self.max_concurrent = max_concurrent
        
        # Task queues
        self._queue: deque[DownloadTask] = deque(maxlen=max_queue_size)
        self._priority_queue: deque[DownloadTask] = deque()
        self._active_tasks: Dict[int, DownloadTask] = {}
        
        # Concurrency control
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f"Queue service initialized (max_size={max_queue_size}, max_concurrent={max_concurrent})")
    
    async def start_worker(self):
        """Start the queue worker background task."""
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._process_queue())
            logger.info("Queue worker started")
    
    async def stop_worker(self):
        """Stop the queue worker."""
        self._running = False
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Queue worker stopped")
    
    async def add_to_queue(
        self, 
        task: DownloadTask, 
        priority: bool = False
    ) -> bool:
        """Add task to download queue.
        
        Args:
            task: DownloadTask to queue
            priority: Add to priority queue (skip regular queue)
            
        Returns:
            True if added successfully, False if queue is full
        """
        if len(self._queue) >= self.max_queue_size:
            logger.warning(f"Queue full, rejecting task {task.task_id}")
            return False
        
        task.status = DownloadStatus.QUEUED
        
        if priority:
            self._priority_queue.append(task)
            logger.info(f"Priority task added: {task.video_id}")
        else:
            self._queue.append(task)
            logger.info(f"Task added to queue: {task.video_id} (queue size: {len(self._queue)})")
        
        return True
    
    async def remove_from_queue(self, task_id: int) -> bool:
        """Remove task from queue.
        
        Args:
            task_id: Task ID to remove
            
        Returns:
            True if removed, False if not found
        """
        # Check regular queue
        for i, task in enumerate(self._queue):
            if task.task_id == task_id:
                del self._queue[i]
                task.status = DownloadStatus.CANCELLED
                logger.info(f"Task {task_id} removed from queue")
                return True
        
        # Check priority queue
        for i, task in enumerate(self._priority_queue):
            if task.task_id == task_id:
                del self._priority_queue[i]
                task.status = DownloadStatus.CANCELLED
                logger.info(f"Priority task {task_id} removed")
                return True
        
        # Check active tasks
        if task_id in self._active_tasks:
            task = self._active_tasks[task_id]
            task.status = DownloadStatus.CANCELLED
            del self._active_tasks[task_id]
            logger.info(f"Active task {task_id} cancelled")
            return True
        
        logger.warning(f"Task {task_id} not found in queue")
        return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status.
        
        Returns:
            Dictionary with queue statistics
        """
        return {
            'queue_length': len(self._queue),
            'priority_queue_length': len(self._priority_queue),
            'active_tasks': len(self._active_tasks),
            'max_queue_size': self.max_queue_size,
            'max_concurrent': self.max_concurrent,
            'running': self._running
        }
    
    def get_all_queued_tasks(self) -> List[DownloadTask]:
        """Get all queued tasks.
        
        Returns:
            List of all queued tasks
        """
        return list(self._queue) + list(self._priority_queue)
    
    def get_active_tasks(self) -> List[DownloadTask]:
        """Get currently active tasks.
        
        Returns:
            List of active tasks
        """
        return list(self._active_tasks.values())
    
    async def _process_queue(self):
        """Background worker to process the queue."""
        logger.info("Queue processor running")
        
        while self._running:
            try:
                # Get next task (priority first)
                task = await self._get_next_task()
                
                if task:
                    # Process task with semaphore (concurrency control)
                    asyncio.create_task(self._execute_with_semaphore(task))
                
                # Small delay to prevent busy loop
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(1)
    
    async def _get_next_task(self) -> Optional[DownloadTask]:
        """Get next task from queue (priority first).
        
        Returns:
            Next DownloadTask or None
        """
        # Priority queue first
        if self._priority_queue:
            return self._priority_queue.popleft()
        
        # Then regular queue
        if self._queue:
            return self._queue.popleft()
        
        return None
    
    async def _execute_with_semaphore(self, task: DownloadTask):
        """Execute task respecting concurrency limits.
        
        Args:
            task: DownloadTask to execute
        """
        async with self._semaphore:
            self._active_tasks[task.task_id] = task
            task.started_at = datetime.now()
            
            try:
                logger.info(f"Executing task: {task.video_id} (quality: {task.quality})")
                
                # Execute callback if registered
                if task.task_id in self._execution_callbacks:
                    callback = self._execution_callbacks[task.task_id]
                    await callback(task)
                
                task.status = DownloadStatus.COMPLETED
                logger.info(f"Task completed: {task.video_id}")
                
            except Exception as e:
                logger.error(f"Task failed: {task.video_id} - {e}")
                task.status = DownloadStatus.FAILED
                task.error_message = str(e)
            
            finally:
                # Clean up
                if task.task_id in self._active_tasks:
                    del self._active_tasks[task.task_id]
                
                # Clean up callbacks
                if task.task_id in self._execution_callbacks:
                    del self._execution_callbacks[task.task_id]
    
    # Execution callbacks
    _execution_callbacks: Dict[int, callable] = {}
    
    def register_execution_callback(self, task_id: int, callback: callable):
        """Register callback for task execution.
        
        Args:
            task_id: Task ID
            callback: Async function to execute the task
        """
        self._execution_callbacks[task_id] = callback
    
    def unregister_execution_callback(self, task_id: int):
        """Remove execution callback.
        
        Args:
            task_id: Task ID
        """
        if task_id in self._execution_callbacks:
            del self._execution_callbacks[task_id]
    
    def clear_queue(self):
        """Clear all queued tasks."""
        count = len(self._queue) + len(self._priority_queue)
        self._queue.clear()
        self._priority_queue.clear()
        logger.info(f"Cleared {count} tasks from queue")
    
    def pause_queue(self):
        """Pause queue processing."""
        self._running = False
        logger.info("Queue paused")
    
    def resume_queue(self):
        """Resume queue processing."""
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._process_queue())
            logger.info("Queue resumed")
    
    def is_queue_full(self) -> bool:
        """Check if queue is full.
        
        Returns:
            True if queue is at max capacity
        """
        return len(self._queue) >= self.max_queue_size
    
    def get_position_in_queue(self, task_id: int) -> int:
        """Get position of task in queue.
        
        Args:
            task_id: Task ID
            
        Returns:
            Position (1-based) or -1 if not found
        """
        for i, task in enumerate(self._queue):
            if task.task_id == task_id:
                return i + 1
        
        for i, task in enumerate(self._priority_queue):
            if task.task_id == task_id:
                return i + 1
        
        return -1
