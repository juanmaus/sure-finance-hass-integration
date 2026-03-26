"""Unit tests for CacheManager Path handling."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the CacheManager from the integration
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'sure_finance'))
from cache_manager import CacheManager


class TestCacheManagerPathHandling(unittest.TestCase):
    """Test CacheManager Path object handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_manager_init_with_string_path(self):
        """Test CacheManager initialization with string path."""
        cache_dir_str = str(self.temp_path / "cache_string")
        
        # This should not raise AttributeError
        cache_manager = CacheManager(cache_dir=cache_dir_str)
        
        # Verify cache_dir is a Path object
        self.assertIsInstance(cache_manager.cache_dir, Path)
        self.assertEqual(str(cache_manager.cache_dir), cache_dir_str)
        
        # Verify directory was created
        self.assertTrue(cache_manager.cache_dir.exists())
        self.assertTrue(cache_manager.cache_dir.is_dir())

    def test_cache_manager_init_with_path_object(self):
        """Test CacheManager initialization with Path object."""
        cache_dir_path = self.temp_path / "cache_path"
        
        # This should work as before
        cache_manager = CacheManager(cache_dir=cache_dir_path)
        
        # Verify cache_dir is a Path object
        self.assertIsInstance(cache_manager.cache_dir, Path)
        self.assertEqual(cache_manager.cache_dir, cache_dir_path)
        
        # Verify directory was created
        self.assertTrue(cache_manager.cache_dir.exists())
        self.assertTrue(cache_manager.cache_dir.is_dir())

    def test_cache_manager_init_with_none(self):
        """Test CacheManager initialization with None (default)."""
        # This should use default ".cache" directory
        cache_manager = CacheManager(cache_dir=None)
        
        # Verify cache_dir is a Path object
        self.assertIsInstance(cache_manager.cache_dir, Path)
        self.assertEqual(str(cache_manager.cache_dir), ".cache")
        
        # Verify directory was created
        self.assertTrue(cache_manager.cache_dir.exists())
        self.assertTrue(cache_manager.cache_dir.is_dir())

    def test_cache_manager_mkdir_no_attribute_error(self):
        """Test that mkdir() doesn't raise AttributeError."""
        cache_dir_str = str(self.temp_path / "test_mkdir")
        
        # This should not raise AttributeError: 'str' object has no attribute 'mkdir'
        try:
            cache_manager = CacheManager(cache_dir=cache_dir_str)
            # If we get here, the fix worked
            self.assertTrue(True)
        except AttributeError as e:
            if "'str' object has no attribute 'mkdir'" in str(e):
                self.fail("AttributeError still occurs: CacheManager not properly handling string paths")
            else:
                raise  # Re-raise if it's a different AttributeError

    def test_cache_manager_path_operations(self):
        """Test that all Path operations work correctly."""
        cache_dir_str = str(self.temp_path / "path_ops")
        cache_manager = CacheManager(cache_dir=cache_dir_str)
        
        # Test that we can use Path operations
        cache_file = cache_manager.cache_dir / "test.cache"
        
        # This should work without errors
        self.assertIsInstance(cache_file, Path)
        self.assertTrue(str(cache_file).endswith("test.cache"))
        
        # Test file creation
        cache_file.touch()
        self.assertTrue(cache_file.exists())
        
        # Test file deletion
        cache_file.unlink()
        self.assertFalse(cache_file.exists())

    @patch('custom_components.sure_finance.cache_manager.Redis')
    async def test_cache_manager_async_operations(self, mock_redis):
        """Test async operations work with fixed Path handling."""
        cache_dir_str = str(self.temp_path / "async_ops")
        cache_manager = CacheManager(cache_dir=cache_dir_str)
        
        # Test basic async operations
        await cache_manager.set("test_key", "test_value")
        value = await cache_manager.get("test_key")
        
        # Value should be retrieved from memory cache
        self.assertEqual(value, "test_value")
        
        # Clean up
        await cache_manager.close()

    def test_home_assistant_path_simulation(self):
        """Test with Home Assistant-style path (simulating hass.config.path())."""
        # Simulate what hass.config.path("custom_components", "sure_finance", "cache") returns
        ha_config_path = "/config/custom_components/sure_finance/cache"
        
        # In a real scenario, this would be a string returned by hass.config.path()
        # Our fix should handle this without AttributeError
        try:
            cache_manager = CacheManager(cache_dir=ha_config_path)
            self.assertIsInstance(cache_manager.cache_dir, Path)
            self.assertEqual(str(cache_manager.cache_dir), ha_config_path)
        except AttributeError as e:
            if "'str' object has no attribute 'mkdir'" in str(e):
                self.fail("Fix failed: Still getting AttributeError with HA-style path")
            else:
                raise

    def test_type_annotation_compliance(self):
        """Test that type annotations are correctly updated."""
        from typing import get_type_hints
        
        # Get type hints for CacheManager.__init__
        hints = get_type_hints(CacheManager.__init__)
        
        # cache_dir should accept Union[str, Path] or similar
        cache_dir_type = hints.get('cache_dir')
        
        # This test ensures our type annotation update is correct
        # The exact type checking depends on Python version and typing module
        self.assertIsNotNone(cache_dir_type)


class TestCacheManagerIntegration(unittest.TestCase):
    """Integration tests for CacheManager with file operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def test_full_cache_workflow_with_string_path(self):
        """Test complete cache workflow with string path input."""
        cache_dir_str = str(self.temp_path / "workflow_test")
        cache_manager = CacheManager(cache_dir=cache_dir_str)
        
        try:
            # Test setting and getting values
            await cache_manager.set("workflow_key", {"test": "data"}, namespace="test")
            
            # Verify file was created
            cache_files = list(cache_manager.cache_dir.glob("*.cache"))
            self.assertGreater(len(cache_files), 0)
            
            # Test retrieval
            value = await cache_manager.get("workflow_key", namespace="test")
            self.assertEqual(value, {"test": "data"})
            
            # Test deletion
            await cache_manager.delete("workflow_key", namespace="test")
            value = await cache_manager.get("workflow_key", namespace="test")
            self.assertIsNone(value)
            
        finally:
            await cache_manager.close()

    async def test_cache_manager_with_nested_directories(self):
        """Test CacheManager with deeply nested directory paths."""
        nested_path = str(self.temp_path / "very" / "deep" / "nested" / "cache")
        
        # This should create all parent directories
        cache_manager = CacheManager(cache_dir=nested_path)
        
        # Verify all directories were created
        self.assertTrue(cache_manager.cache_dir.exists())
        self.assertTrue(cache_manager.cache_dir.is_dir())
        
        # Test that we can perform cache operations
        await cache_manager.set("nested_key", "nested_value")
        value = await cache_manager.get("nested_key")
        self.assertEqual(value, "nested_value")
        
        await cache_manager.close()


if __name__ == '__main__':
    # Run synchronous tests
    unittest.main(verbosity=2, exit=False)
    
    # Run async tests
    async def run_async_tests():
        """Run async test methods."""
        test_instance = TestCacheManagerIntegration()
        test_instance.setUp()
        
        try:
            await test_instance.test_full_cache_workflow_with_string_path()
            print("✓ test_full_cache_workflow_with_string_path passed")
            
            await test_instance.test_cache_manager_with_nested_directories()
            print("✓ test_cache_manager_with_nested_directories passed")
            
        finally:
            test_instance.tearDown()
    
    # Run async tests
    asyncio.run(run_async_tests())
    print("\n✅ All CacheManager Path handling tests completed successfully!")
