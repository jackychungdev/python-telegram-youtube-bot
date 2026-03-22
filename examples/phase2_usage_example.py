"""
Example usage of Phase 2 Data Access Layer

This file demonstrates how to use the new repository pattern
and dependency injection container.
"""
import asyncio
from src.infrastructure.persistence import (
    UserRepository, 
    VideoRepository, 
    AuthorizationRepository,
    Database
)
from src.core import Container


async def example_direct_repository_usage():
    """Example 1: Using repositories directly."""
    print("=== Example 1: Direct Repository Usage ===")
    
    # Initialize repositories
    user_repo = UserRepository('users.db')
    video_repo = VideoRepository('users.db')
    auth_repo = AuthorizationRepository('authorized_users.db')
    
    # Create or update user
    await user_repo.create_or_update(
        user_id=123456,
        username='test_user',
        video_url='https://youtube.com/watch?v=test'
    )
    print("✓ User created/updated")
    
    # Set language preference
    await user_repo.update_language(123456, 'en')
    lang = await user_repo.get_language(123456)
    print(f"✓ User language: {lang}")
    
    # Check rate limit
    can_download = await user_repo.can_download(123456, limit_per_hour=10)
    print(f"✓ Can download: {can_download}")
    
    if can_download:
        count = await user_repo.increment_downloads(123456)
        print(f"✓ Download count incremented to: {count}")
    
    # Cache video information
    await video_repo.save(
        video_id='test_video_123',
        quality='720',
        file_id='telegram_file_abc',
        file_size=1024000,
        title='Test Video',
        channel_username='@testchannel'
    )
    print("✓ Video cached")
    
    # Check cache
    cached = await video_repo.get_cached('test_video_123', '720')
    if cached:
        file_id, title, username, url = cached
        print(f"✓ Cache hit: {title} by {username}")
    
    # Get cache statistics
    stats = await video_repo.get_cache_stats()
    print(f"✓ Cache stats: {stats['total_files']} files, {stats['total_size_mb']} MB")
    
    # Add authorized user
    await auth_repo.add_user(123456, added_by='admin')
    is_auth = await auth_repo.is_authorized(123456)
    print(f"✓ User authorized: {is_auth}")
    
    # Get user stats
    user_stats = await user_repo.get_user_stats()
    print(f"✓ Total users: {user_stats['total_users']}, Active (24h): {user_stats['active_users_24h']}")


async def example_dependency_injection():
    """Example 2: Using Dependency Injection container."""
    print("\n=== Example 2: Dependency Injection ===")
    
    # Setup container
    container = Container()
    
    # Register services as singletons
    container.register_singleton(
        UserRepository,
        db_path='users.db'
    )
    container.register_singleton(
        VideoRepository,
        db_path='users.db'
    )
    container.register_singleton(
        AuthorizationRepository,
        db_path='authorized_users.db'
    )
    
    # Resolve dependencies
    user_repo = container.resolve(UserRepository)
    video_repo = container.resolve(VideoRepository)
    auth_repo = container.resolve(AuthorizationRepository)
    
    # Use repositories
    await user_repo.create_or_update(789012, 'injected_user')
    print("✓ User created via DI")
    
    # Check if registered
    is_registered = container.is_registered(UserRepository)
    print(f"✓ UserRepository registered: {is_registered}")


async def example_database_operations():
    """Example 3: Using Database directly."""
    print("\n=== Example 3: Direct Database Operations ===")
    
    # Get database instance
    db = await Database.get_database('users.db')
    
    # Execute raw query
    await db.execute(
        'UPDATE users SET username = ? WHERE user_id = ?',
        ('updated_user', 123456)
    )
    await db.commit()
    print("✓ Raw SQL executed and committed")
    
    # Use convenience functions
    from src.infrastructure.persistence import fetch_one, fetch_all
    
    user = await fetch_one(
        'SELECT * FROM users WHERE user_id = ?',
        (123456,)
    )
    if user:
        print(f"✓ Fetched user: {user.get('username')}")
    
    all_users = await fetch_all('SELECT * FROM users')
    print(f"✓ Fetched {len(all_users)} total users")
    
    # Get database size
    size_mb = await db.get_size_mb()
    print(f"✓ Database size: {size_mb} MB")


async def example_complete_workflow():
    """Example 4: Complete workflow combining all components."""
    print("\n=== Example 4: Complete Workflow ===")
    
    # Initialize all repositories
    user_repo = UserRepository()
    video_repo = VideoRepository()
    auth_repo = AuthorizationRepository()
    
    user_id = 999888
    video_id = 'workflow_test'
    quality = '1080'
    
    # Step 1: Check authorization
    if not await auth_repo.is_authorized(user_id):
        print(f"✗ User {user_id} not authorized")
        # For demo, authorize them
        await auth_repo.add_user(user_id, added_by='system')
        print(f"✓ Auto-authorized user {user_id}")
    
    # Step 2: Create/update user record
    await user_repo.create_or_update(user_id, 'workflow_user')
    print(f"✓ User record ready")
    
    # Step 3: Check rate limit
    if not await user_repo.can_download(user_id, limit_per_hour=5):
        print(f"✗ Rate limit exceeded")
        return
    
    # Step 4: Check cache
    cached = await video_repo.get_cached(video_id, quality)
    if cached:
        print(f"✓ Cache HIT - returning cached file")
        file_id = cached[0]
    else:
        print(f"✓ Cache MISS - would download now")
        # Simulate download and caching
        await video_repo.save(
            video_id=video_id,
            quality=quality,
            file_id='new_file_123',
            file_size=2048000,
            title='Workflow Test Video'
        )
        file_id = 'new_file_123'
    
    # Step 5: Update download counter
    await user_repo.increment_downloads(user_id)
    print(f"✓ Download counter updated")
    
    # Step 6: Update activity
    await user_repo.update_activity(
        user_id, 
        username='workflow_user',
        video_url=f'https://youtube.com/watch?v={video_id}'
    )
    print(f"✓ Activity logged")
    
    print(f"\n✓ Complete workflow finished successfully!")


async def main():
    """Run all examples."""
    print("=" * 60)
    print("Phase 2 Data Access Layer - Usage Examples")
    print("=" * 60)
    
    try:
        # Run examples
        await example_direct_repository_usage()
        await example_dependency_injection()
        await example_database_operations()
        await example_complete_workflow()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
