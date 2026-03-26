"""Tests for Sure Finance Cache Manager."""

import asyncio
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.asyncio import Redis

from custom_components.sure_finance.cache_manager import CacheManager


class TestCacheManager:
    """Test suite for CacheManager."""
    
    @pytest.fixture
    def cache_manager(self, temp_cache_dir):
        """Create a test cache manager instance."""
        return CacheManager(
            cache_dir=temp_cache_dir,
            default_ttl=3600
        )
    
    def test_initialization(self, temp_cache_dir):
        """Test cache manager initialization."""
        # Test with default values
        cache = CacheManager()
        assert cache.cache_dir == Path(".cache")
        assert cache.default_ttl == 3600
        assert cache._redis is None
        assert cache._memory_cache == {}
        
        # Test with custom values
        cache = CacheManager(
            cache_dir=temp_cache_dir,
            redis_url="redis://localhost:6379",
            default_ttl=1800
        )
        assert cache.cache_dir == temp_cache_dir
        assert cache.redis_url == "redis://localhost:6379"
        assert cache.default_ttl == 1800
    
    def test_cache_dir_creation(self, tmp_path):
        """Test that cache directory is created if it doesn't exist."""
        cache_dir = tmp_path / "new_cache_dir"
        assert not cache_dir.exists()
        
        cache = CacheManager(cache_dir=cache_dir)
        assert cache_dir.exists()
        assert cache_dir.is_dir()
    
    @pytest.mark.asyncio
    async def test_redis_connection_success(self, cache_manager, mock_redis):
        """Test successful Redis connection."""
        with patch('redis.asyncio.Redis.from_url', return_value=mock_redis):
            cache_manager.redis_url = "redis://localhost:6379"
            await cache_manager.connect_redis()
            
            assert cache_manager._redis is mock_redis
            mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, cache_manager):
        """Test Redis connection failure handling."""
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        
        with patch('redis.asyncio.Redis.from_url', return_value=mock_redis):
            cache_manager.redis_url = "redis://localhost:6379"
            await cache_manager.connect_redis()
            
            # Should handle the error gracefully
            assert cache_manager._redis is None
    
    @pytest.mark.asyncio
    async def test_redis_connection_no_url(self, cache_manager):
        """Test Redis connection when no URL is provided."""
        cache_manager.redis_url = None
        await cache_manager.connect_redis()
        
        assert cache_manager._redis is None
    
    @pytest.mark.asyncio
    async def test_close_redis_connection(self, cache_manager, mock_redis):
        """Test Redis connection cleanup."""
        cache_manager._redis = mock_redis
        
        await cache_manager.close()
        
        mock_redis.close.assert_called_once()
        assert cache_manager._redis is None
    
    @pytest.mark.asyncio
    async def test_close_no_redis(self, cache_manager):
        """Test close when no Redis connection exists."""
        cache_manager._redis = None
        
        # Should not raise an error
        await cache_manager.close()
    
    def test_get_cache_key(self, cache_manager):
        """Test cache key generation."""
        # Test with default namespace
        key = cache_manager._get_cache_key("test_key")
        assert key == "sure_finance:default:test_key"
        
        # Test with custom namespace
        key = cache_manager._get_cache_key("test_key", "accounts")
        assert key == "sure_finance:accounts:test_key"
    
    @pytest.mark.asyncio
    async def test_memory_cache_get_hit(self, cache_manager):
        """Test memory cache hit scenario."""
        # Setup memory cache with valid entry
        full_key = "sure_finance:default:test_key"
        expires_at = datetime.utcnow() + timedelta(hours=1)
        cache_manager._memory_cache[full_key] = {
            "value": {"test": "data"},
            "expires_at": expires_at
        }
        
        result = await cache_manager.get("test_key")
        
        assert result == {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_memory_cache_get_expired(self, cache_manager):
        """Test memory cache with expired entry."""
        # Setup memory cache with expired entry
        full_key = "sure_finance:default:test_key"
        expires_at = datetime.utcnow() - timedelta(hours=1)  # Expired
        cache_manager._memory_cache[full_key] = {
            "value": {"test": "data"},
            "expires_at": expires_at
        }
        
        result = await cache_manager.get("test_key")
        
        # Should return None and clean up expired entry
        assert result is None
        assert full_key not in cache_manager._memory_cache
    
    @pytest.mark.asyncio
    async def test_redis_cache_get_hit(self, cache_manager, mock_redis):
        """Test Redis cache hit scenario."""
        cache_manager._redis = mock_redis
        
        # Setup Redis to return data
        test_data = {"test": "data"}
        mock_redis.get.return_value = json.dumps(test_data)
        
        result = await cache_manager.get("test_key")
        
        assert result == test_data
        mock_redis.get.assert_called_once_with("sure_finance:default:test_key")
    
    @pytest.mark.asyncio
    async def test_redis_cache_get_miss(self, cache_manager, mock_redis):
        """Test Redis cache miss scenario."""
        cache_manager._redis = mock_redis
        
        # Setup Redis to return None
        mock_redis.get.return_value = None
        
        result = await cache_manager.get("test_key")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_redis_cache_get_error(self, cache_manager, mock_redis):
        """Test Redis cache error handling."""
        cache_manager._redis = mock_redis
        
        # Setup Redis to raise an error
        mock_redis.get.side_effect = Exception("Redis error")
        
        result = await cache_manager.get("test_key")
        
        # Should handle error gracefully and return None
        assert result is None
    
    @pytest.mark.asyncio
    async def test_file_cache_get_hit(self, cache_manager):
        """Test file cache hit scenario."""
        # Create a cache file
        full_key = "sure_finance:default:test_key"
        test_data = {"test": "data"}
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        cache_file = cache_manager.cache_dir / f"{full_key}.cache"
        with open(cache_file, "wb") as f:
            pickle.dump({"value": test_data, "expires_at": expires_at}, f)
        
        result = await cache_manager.get("test_key")
        
        assert result == test_data
    
    @pytest.mark.asyncio
    async def test_file_cache_get_expired(self, cache_manager):
        """Test file cache with expired entry."""
        # Create an expired cache file
        full_key = "sure_finance:default:test_key"
        test_data = {"test": "data"}
        expires_at = datetime.utcnow() - timedelta(hours=1)  # Expired
        
        cache_file = cache_manager.cache_dir / f"{full_key}.cache"
        with open(cache_file, "wb") as f:
            pickle.dump({"value": test_data, "expires_at": expires_at}, f)
        
        result = await cache_manager.get("test_key")
        
        # Should return None and delete expired file
        assert result is None
        assert not cache_file.exists()
    
    @pytest.mark.asyncio
    async def test_file_cache_get_corrupted(self, cache_manager):
        """Test file cache with corrupted file."""
        # Create a corrupted cache file
        full_key = "sure_finance:default:test_key"
        cache_file = cache_manager.cache_dir / f"{full_key}.cache"
        
        with open(cache_file, "w") as f:
            f.write("corrupted data")
        
        result = await cache_manager.get("test_key")
        
        # Should handle corruption gracefully
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_memory_cache(self, cache_manager):
        """Test setting data in memory cache."""
        test_data = {"test": "data"}
        
        await cache_manager.set("test_key", test_data, ttl=1800)
        
        # Verify memory cache
        full_key = "sure_finance:default:test_key"
        assert full_key in cache_manager._memory_cache
        
        cached_entry = cache_manager._memory_cache[full_key]
        assert cached_entry["value"] == test_data
        assert cached_entry["expires_at"] > datetime.utcnow()
    
    @pytest.mark.asyncio
    async def test_set_redis_cache(self, cache_manager, mock_redis):
        """Test setting data in Redis cache."""
        cache_manager._redis = mock_redis
        test_data = {"test": "data"}
        
        await cache_manager.set("test_key", test_data, ttl=1800)
        
        # Verify Redis call
        mock_redis.setex.assert_called_once_with(
            "sure_finance:default:test_key",
            1800,
            json.dumps(test_data, default=str)
        )
    
    @pytest.mark.asyncio
    async def test_set_redis_error(self, cache_manager, mock_redis):
        """Test Redis set error handling."""
        cache_manager._redis = mock_redis
        mock_redis.setex.side_effect = Exception("Redis error")
        
        test_data = {"test": "data"}
        
        # Should not raise an error
        await cache_manager.set("test_key", test_data)
        
        # Memory cache should still work
        full_key = "sure_finance:default:test_key"
        assert full_key in cache_manager._memory_cache
    
    @pytest.mark.asyncio
    async def test_set_file_cache(self, cache_manager):
        """Test setting data in file cache."""
        test_data = {"test": "data"}
        
        await cache_manager.set("test_key", test_data, ttl=1800)
        
        # Verify file cache
        full_key = "sure_finance:default:test_key"
        cache_file = cache_manager.cache_dir / f"{full_key}.cache"
        
        assert cache_file.exists()
        
        with open(cache_file, "rb") as f:
            cached_data = pickle.load(f)
            assert cached_data["value"] == test_data
            assert cached_data["expires_at"] > datetime.utcnow()
    
    @pytest.mark.asyncio
    async def test_set_file_cache_error(self, cache_manager):
        """Test file cache set error handling."""
        test_data = {"test": "data"}
        
        # Make cache directory read-only to cause write error
        cache_manager.cache_dir.chmod(0o444)
        
        try:
            # Should not raise an error
            await cache_manager.set("test_key", test_data)
            
            # Memory cache should still work
            full_key = "sure_finance:default:test_key"
            assert full_key in cache_manager._memory_cache
        finally:
            # Restore permissions
            cache_manager.cache_dir.chmod(0o755)
    
    @pytest.mark.asyncio
    async def test_set_default_ttl(self, cache_manager):
        """Test setting data with default TTL."""
        test_data = {"test": "data"}
        
        await cache_manager.set("test_key", test_data)  # No TTL specified
        
        # Should use default TTL
        full_key = "sure_finance:default:test_key"
        cached_entry = cache_manager._memory_cache[full_key]
        
        expected_expiry = datetime.utcnow() + timedelta(seconds=3600)
        # Allow for small timing differences
        assert abs((cached_entry["expires_at"] - expected_expiry).total_seconds()) < 5
    
    @pytest.mark.asyncio
    async def test_delete_all_caches(self, cache_manager, mock_redis):
        """Test deleting data from all cache layers."""
        cache_manager._redis = mock_redis
        
        # Setup data in memory cache
        full_key = "sure_finance:default:test_key"
        cache_manager._memory_cache[full_key] = {
            "value": {"test": "data"},
            "expires_at": datetime.utcnow() + timedelta(hours=1)
        }
        
        # Setup file cache
        cache_file = cache_manager.cache_dir / f"{full_key}.cache"
        with open(cache_file, "wb") as f:
            pickle.dump({"value": {"test": "data"}, "expires_at": datetime.utcnow() + timedelta(hours=1)}, f)
        
        await cache_manager.delete("test_key")
        
        # Verify memory cache deletion
        assert full_key not in cache_manager._memory_cache
        
        # Verify Redis deletion
        mock_redis.delete.assert_called_once_with(full_key)
        
        # Verify file cache deletion
        assert not cache_file.exists()
    
    @pytest.mark.asyncio
    async def test_delete_redis_error(self, cache_manager, mock_redis):
        """Test Redis delete error handling."""
        cache_manager._redis = mock_redis
        mock_redis.delete.side_effect = Exception("Redis error")
        
        # Should not raise an error
        await cache_manager.delete("test_key")
    
    @pytest.mark.asyncio
    async def test_delete_file_error(self, cache_manager):
        """Test file delete error handling."""
        # Create a cache file
        full_key = "sure_finance:default:test_key"
        cache_file = cache_manager.cache_dir / f"{full_key}.cache"
        cache_file.touch()
        
        # Make file read-only to cause delete error
        cache_file.chmod(0o444)
        cache_manager.cache_dir.chmod(0o555)
        
        try:
            # Should not raise an error
            await cache_manager.delete("test_key")
        finally:
            # Restore permissions for cleanup
            cache_manager.cache_dir.chmod(0o755)
            cache_file.chmod(0o644)
    
    @pytest.mark.asyncio
    async def test_clear_namespace_memory(self, cache_manager):
        """Test clearing namespace from memory cache."""
        # Setup memory cache with multiple namespaces
        cache_manager._memory_cache.update({
            "sure_finance:accounts:key1": {"value": "data1", "expires_at": datetime.utcnow() + timedelta(hours=1)},
            "sure_finance:accounts:key2": {"value": "data2", "expires_at": datetime.utcnow() + timedelta(hours=1)},
            "sure_finance:transactions:key1": {"value": "data3", "expires_at": datetime.utcnow() + timedelta(hours=1)},
            "sure_finance:other:key1": {"value": "data4", "expires_at": datetime.utcnow() + timedelta(hours=1)},
        })
        
        await cache_manager.clear_namespace("accounts")
        
        # Verify only accounts namespace was cleared
        remaining_keys = list(cache_manager._memory_cache.keys())
        assert "sure_finance:accounts:key1" not in remaining_keys
        assert "sure_finance:accounts:key2" not in remaining_keys
        assert "sure_finance:transactions:key1" in remaining_keys
        assert "sure_finance:other:key1" in remaining_keys
    
    @pytest.mark.asyncio
    async def test_clear_namespace_redis(self, cache_manager, mock_redis):
        """Test clearing namespace from Redis cache."""
        cache_manager._redis = mock_redis
        
        # Setup Redis scan_iter to return matching keys
        mock_redis.scan_iter.return_value = [
            "sure_finance:accounts:key1",
            "sure_finance:accounts:key2"
        ].__iter__()
        
        await cache_manager.clear_namespace("accounts")
        
        # Verify scan_iter was called with correct pattern
        mock_redis.scan_iter.assert_called_once_with(match="sure_finance:accounts:*")
        
        # Verify delete was called for each key
        assert mock_redis.delete.call_count == 2
    
    @pytest.mark.asyncio
    async def test_clear_namespace_files(self, cache_manager):
        """Test clearing namespace from file cache."""
        # Create cache files for different namespaces
        files_to_create = [
            "sure_finance:accounts:key1.cache",
            "sure_finance:accounts:key2.cache",
            "sure_finance:transactions:key1.cache",
            "sure_finance:other:key1.cache"
        ]
        
        for filename in files_to_create:
            cache_file = cache_manager.cache_dir / filename
            cache_file.touch()
        
        await cache_manager.clear_namespace("accounts")
        
        # Verify only accounts files were deleted
        remaining_files = [f.name for f in cache_manager.cache_dir.iterdir()]
        assert "sure_finance:accounts:key1.cache" not in remaining_files
        assert "sure_finance:accounts:key2.cache" not in remaining_files
        assert "sure_finance:transactions:key1.cache" in remaining_files
        assert "sure_finance:other:key1.cache" in remaining_files
    
    @pytest.mark.asyncio
    async def test_get_or_set_cache_hit(self, cache_manager):
        """Test get_or_set with cache hit."""
        # Setup cache with existing data
        test_data = {"test": "cached_data"}
        await cache_manager.set("test_key", test_data)
        
        # Factory function should not be called
        factory = AsyncMock(return_value={"test": "new_data"})
        
        result = await cache_manager.get_or_set("test_key", factory)
        
        assert result == test_data
        factory.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_or_set_cache_miss(self, cache_manager):
        """Test get_or_set with cache miss."""
        # No existing cache data
        factory_data = {"test": "new_data"}
        factory = AsyncMock(return_value=factory_data)
        
        result = await cache_manager.get_or_set("test_key", factory, ttl=1800)
        
        assert result == factory_data
        factory.assert_called_once()
        
        # Verify data was cached
        cached_result = await cache_manager.get("test_key")
        assert cached_result == factory_data
    
    def test_cleanup_expired_memory(self, cache_manager):
        """Test cleanup of expired entries from memory cache."""
        now = datetime.utcnow()
        
        # Setup memory cache with mixed expired/valid entries
        cache_manager._memory_cache.update({
            "expired_key1": {"value": "data1", "expires_at": now - timedelta(hours=1)},
            "expired_key2": {"value": "data2", "expires_at": now - timedelta(minutes=1)},
            "valid_key1": {"value": "data3", "expires_at": now + timedelta(hours=1)},
            "valid_key2": {"value": "data4", "expires_at": now + timedelta(minutes=1)},
        })
        
        cache_manager.cleanup_expired()
        
        # Verify only valid entries remain
        remaining_keys = list(cache_manager._memory_cache.keys())
        assert "expired_key1" not in remaining_keys
        assert "expired_key2" not in remaining_keys
        assert "valid_key1" in remaining_keys
        assert "valid_key2" in remaining_keys
    
    def test_cleanup_expired_files(self, cache_manager):
        """Test cleanup of expired cache files."""
        now = datetime.utcnow()
        
        # Create expired cache file
        expired_file = cache_manager.cache_dir / "expired.cache"
        with open(expired_file, "wb") as f:
            pickle.dump({
                "value": "expired_data",
                "expires_at": now - timedelta(hours=1)
            }, f)
        
        # Create valid cache file
        valid_file = cache_manager.cache_dir / "valid.cache"
        with open(valid_file, "wb") as f:
            pickle.dump({
                "value": "valid_data",
                "expires_at": now + timedelta(hours=1)
            }, f)
        
        # Create corrupted cache file
        corrupted_file = cache_manager.cache_dir / "corrupted.cache"
        with open(corrupted_file, "w") as f:
            f.write("corrupted data")
        
        cache_manager.cleanup_expired()
        
        # Verify cleanup results
        assert not expired_file.exists()
        assert valid_file.exists()
        assert not corrupted_file.exists()  # Corrupted files should be cleaned up too
    
    def test_cache_key_methods(self, cache_manager):
        """Test cache key generation helper methods."""
        # Test account key
        assert cache_manager.account_key() == "accounts:all"
        assert cache_manager.account_key("123") == "account:123"
        
        # Test transaction key
        assert cache_manager.transaction_key() == "transactions"
        assert cache_manager.transaction_key("123") == "transactions:account:123"
        assert cache_manager.transaction_key(page=2) == "transactions:page:2"
        assert cache_manager.transaction_key("123", 2) == "transactions:account:123:page:2"
        
        # Test summary key
        assert cache_manager.summary_key() == "summary:current"
        assert cache_manager.summary_key("monthly") == "summary:monthly"
        
        # Test cashflow key
        assert cache_manager.cashflow_key(2023, 6) == "cashflow:2023-06"
        assert cache_manager.cashflow_key(2023, 12) == "cashflow:2023-12"


class TestCacheManagerIntegration:
    """Integration tests for CacheManager."""
    
    @pytest.mark.asyncio
    async def test_full_cache_flow(self, temp_cache_dir):
        """Test complete cache flow through all layers."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir, default_ttl=3600)
        
        test_data = {"test": "data", "number": 42}
        
        # Set data
        await cache_manager.set("flow_test", test_data, ttl=1800)
        
        # Get data (should hit memory cache)
        result1 = await cache_manager.get("flow_test")
        assert result1 == test_data
        
        # Clear memory cache
        cache_manager._memory_cache.clear()
        
        # Get data again (should hit file cache)
        result2 = await cache_manager.get("flow_test")
        assert result2 == test_data
        
        # Delete data
        await cache_manager.delete("flow_test")
        
        # Get data again (should return None)
        result3 = await cache_manager.get("flow_test")
        assert result3 is None
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self, temp_cache_dir):
        """Test concurrent cache access."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        
        async def set_data(key, value):
            await cache_manager.set(key, value)
            return await cache_manager.get(key)
        
        # Perform concurrent operations
        tasks = [
            set_data(f"key_{i}", {"value": i})
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all operations succeeded
        for i, result in enumerate(results):
            assert result == {"value": i}
    
    @pytest.mark.asyncio
    async def test_large_data_handling(self, temp_cache_dir):
        """Test caching of large data sets."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        
        # Create large data set
        large_data = {
            "items": [f"item_{i}" for i in range(10000)],
            "metadata": {f"key_{i}": f"value_{i}" for i in range(1000)}
        }
        
        # Cache large data
        await cache_manager.set("large_data", large_data)
        
        # Retrieve large data
        result = await cache_manager.get("large_data")
        
        assert result == large_data
        assert len(result["items"]) == 10000
        assert len(result["metadata"]) == 1000
    
    @pytest.mark.asyncio
    async def test_ttl_behavior(self, temp_cache_dir):
        """Test TTL behavior across cache layers."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        
        test_data = {"test": "ttl_data"}
        
        # Set data with short TTL
        await cache_manager.set("ttl_test", test_data, ttl=1)  # 1 second
        
        # Should be available immediately
        result1 = await cache_manager.get("ttl_test")
        assert result1 == test_data
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        result2 = await cache_manager.get("ttl_test")
        assert result2 is None
    
    @pytest.mark.asyncio
    async def test_namespace_isolation(self, temp_cache_dir):
        """Test that different namespaces are properly isolated."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        
        # Set data in different namespaces
        await cache_manager.set("same_key", {"namespace": "accounts"}, namespace="accounts")
        await cache_manager.set("same_key", {"namespace": "transactions"}, namespace="transactions")
        await cache_manager.set("same_key", {"namespace": "default"}, namespace="default")
        
        # Verify isolation
        accounts_data = await cache_manager.get("same_key", namespace="accounts")
        transactions_data = await cache_manager.get("same_key", namespace="transactions")
        default_data = await cache_manager.get("same_key", namespace="default")
        
        assert accounts_data["namespace"] == "accounts"
        assert transactions_data["namespace"] == "transactions"
        assert default_data["namespace"] == "default"
        
        # Clear one namespace
        await cache_manager.clear_namespace("accounts")
        
        # Verify only that namespace was cleared
        assert await cache_manager.get("same_key", namespace="accounts") is None
        assert await cache_manager.get("same_key", namespace="transactions") is not None
        assert await cache_manager.get("same_key", namespace="default") is not None


class TestCacheManagerPerformance:
    """Performance tests for CacheManager."""
    
    @pytest.mark.asyncio
    async def test_memory_cache_performance(self, temp_cache_dir):
        """Test memory cache performance with many operations."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        
        # Perform many cache operations
        start_time = datetime.utcnow()
        
        for i in range(1000):
            await cache_manager.set(f"perf_key_{i}", {"value": i})
        
        for i in range(1000):
            result = await cache_manager.get(f"perf_key_{i}")
            assert result["value"] == i
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Should complete 2000 operations in reasonable time
        assert duration < 5.0  # Less than 5 seconds
    
    @pytest.mark.asyncio
    async def test_cleanup_performance(self, temp_cache_dir):
        """Test cleanup performance with many expired entries."""
        cache_manager = CacheManager(cache_dir=temp_cache_dir)
        
        # Create many expired entries
        expired_time = datetime.utcnow() - timedelta(hours=1)
        for i in range(1000):
            full_key = f"expired_key_{i}"
            cache_manager._memory_cache[full_key] = {
                "value": {"data": i},
                "expires_at": expired_time
            }
        
        # Create expired cache files
        for i in range(100):
            cache_file = temp_cache_dir / f"expired_file_{i}.cache"
            with open(cache_file, "wb") as f:
                pickle.dump({
                    "value": {"data": i},
                    "expires_at": expired_time
                }, f)
        
        start_time = datetime.utcnow()
        cache_manager.cleanup_expired()
        end_time = datetime.utcnow()
        
        duration = (end_time - start_time).total_seconds()
        
        # Cleanup should complete in reasonable time
        assert duration < 2.0  # Less than 2 seconds
        
        # Verify cleanup was effective
        assert len(cache_manager._memory_cache) == 0
        cache_files = list(temp_cache_dir.glob("expired_file_*.cache"))
        assert len(cache_files) == 0
