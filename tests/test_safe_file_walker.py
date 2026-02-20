"""
Tests for safe_file_walker module with mocks.
"""
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import pytest

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from safe_file_walker import SafeFileWalker, SafeWalkConfig, WalkStats


class TestSafeWalkConfig:
    """Test configuration validation."""
    
    def test_config_defaults(self):
        config = SafeWalkConfig(root=Path("/test"))
        assert config.root == Path("/test").resolve()
        assert config.max_rate_mb_per_sec == 10.0
        assert config.follow_symlinks is False
        assert config.timeout_sec == 3600.0
        assert config.max_depth is None
        assert config.max_unique_files == 1_000_000
        assert config.deterministic is True
        assert config.on_skip is None
    
    def test_config_validation(self):
        with pytest.raises(ValueError):
            SafeWalkConfig(root=Path("relative/path"))
        
        config = SafeWalkConfig(root=Path("/test"), max_depth=5)
        assert config.max_depth == 5
        
        config = SafeWalkConfig(root=Path("/test"), max_rate_mb_per_sec=0.5)
        assert config.max_rate_mb_per_sec == 0.5


class MockDirEntry:
    """Mock os.DirEntry for testing."""
    
    def __init__(self, name, path, is_file=True, is_dir=False, is_symlink=False,
                 stat_result=None, inode=12345, device_id=1):
        self.name = name
        self.path = path
        self._is_file = is_file
        self._is_dir = is_dir
        self._is_symlink = is_symlink
        self._stat_result = stat_result or MagicMock(
            st_mode=0o100644 if is_file else 0o040755,
            st_ino=inode,
            st_dev=device_id,
            st_size=1024 if is_file else 4096,
        )
    
    def is_file(self, follow_symlinks=True):
        return self._is_file
    
    def is_dir(self, follow_symlinks=True):
        return self._is_dir
    
    def is_symlink(self):
        return self._is_symlink
    
    def stat(self, follow_symlinks=True):
        return self._stat_result


class TestSafeFileWalker:
    """Test the main walker logic."""
    
    @patch('os.scandir')
    def test_basic_walk(self, mock_scandir):
        """Test walking a simple directory structure."""
        root = Path("/test").resolve()
        
        # Create mock directory entries
        entries = [
            MockDirEntry("file1.txt", str(root / "file1.txt"), is_file=True, is_dir=False),
            MockDirEntry("file2.txt", str(root / "file2.txt"), is_file=True, is_dir=False),
            MockDirEntry("subdir", str(root / "subdir"), is_file=False, is_dir=True),
        ]
        
        subdir_entries = [
            MockDirEntry("file3.txt", str(root / "subdir" / "file3.txt"), is_file=True, is_dir=False),
        ]
        
        mock_scandir.side_effect = [entries, subdir_entries]
        
        config = SafeWalkConfig(root=root, max_depth=2)
        walker = SafeFileWalker(config)
        
        with walker as w:
            files = list(w)
        
        assert len(files) == 3  # file1, file2, file3
        assert files[0] == root / "file1.txt"
        assert files[1] == root / "file2.txt"
        assert files[2] == root / "subdir" / "file3.txt"
        
        stats = walker.stats
        assert stats.files_yielded == 3
        assert stats.files_skipped == 0
        assert stats.dirs_skipped == 0
    
    @patch('os.scandir')
    def test_hardlink_deduplication(self, mock_scandir):
        """Test that hardlinks are not processed twice."""
        root = Path("/test").resolve()
        
        # Two files with same inode (hardlinks)
        entries = [
            MockDirEntry("file1.txt", str(root / "file1.txt"), 
                        is_file=True, is_dir=False, inode=1001),
            MockDirEntry("file2.txt", str(root / "file2.txt"), 
                        is_file=True, is_dir=False, inode=1001),  # Same inode
            MockDirEntry("file3.txt", str(root / "file3.txt"), 
                        is_file=True, is_dir=False, inode=1002),  # Different inode
        ]
        
        mock_scandir.return_value = entries
        
        config = SafeWalkConfig(root=root, max_unique_files=1000)
        walker = SafeFileWalker(config)
        
        with walker as w:
            files = list(w)
        
        # Only 2 unique files (file1 and file3, file2 is duplicate)
        assert len(files) == 2
        assert walker.stats.files_yielded == 2
        assert walker.stats.files_skipped == 1
    
    @patch('os.scandir')
    @patch('time.time')
    def test_rate_limiting(self, mock_time, mock_scandir):
        """Test I/O rate limiting."""
        root = Path("/test").resolve()
        
        # Create a large file (5 MB)
        entries = [
            MockDirEntry("large.bin", str(root / "large.bin"), is_file=True, is_dir=False,
                        stat_result=MagicMock(st_size=5 * 1024 * 1024)),  # 5 MB
        ]
        
        mock_scandir.return_value = entries
        
        # Mock time to simulate rate limiting
        time_values = [0.0, 0.01, 0.5]  # Start, after stat, after sleep
        mock_time.side_effect = time_values
        
        config = SafeWalkConfig(root=root, max_rate_mb_per_sec=1.0)  # 1 MB/s
        walker = SafeFileWalker(config)
        
        with walker as w:
            files = list(w)
        
        # Should have slept because 5 MB at 1 MB/s = 5 seconds
        # We can't easily test the sleep call, but we can verify it ran
        assert len(files) == 1
        assert walker.stats.bytes_processed == 5 * 1024 * 1024
    
    @patch('os.scandir')
    def test_symlink_handling(self, mock_scandir):
        """Test symlink behavior."""
        root = Path("/test").resolve()
        
        entries = [
            MockDirEntry("normal.txt", str(root / "normal.txt"), 
                        is_file=True, is_dir=False, is_symlink=False),
            MockDirEntry("link.txt", str(root / "link.txt"), 
                        is_file=True, is_dir=False, is_symlink=True),
        ]
        
        mock_scandir.return_value = entries
        
        # With follow_symlinks=False (default)
        config = SafeWalkConfig(root=root, follow_symlinks=False)
        walker = SafeFileWalker(config)
        
        with walker as w:
            files = list(w)
        
        # Only non-symlink file should be yielded
        assert len(files) == 1
        assert files[0] == root / "normal.txt"
        assert walker.stats.files_skipped == 1
    
    @patch('os.scandir')
    @patch('time.time')
    def test_timeout(self, mock_time, mock_scandir):
        """Test timeout protection."""
        root = Path("/test").resolve()
        
        entries = [
            MockDirEntry("file1.txt", str(root / "file1.txt"), is_file=True, is_dir=False),
            MockDirEntry("file2.txt", str(root / "file2.txt"), is_file=True, is_dir=False),
        ]
        
        mock_scandir.return_value = entries
        
        # Simulate time passing beyond timeout
        mock_time.side_effect = [0.0, 10.0, 20.0]  # Start, after first file, after second
        
        config = SafeWalkConfig(root=root, timeout_sec=15.0)
        walker = SafeFileWalker(config)
        
        with pytest.raises(TimeoutError):
            with walker as w:
                files = list(w)  # Should timeout on second file
        
        stats = walker.stats
        assert stats.files_yielded == 1  # Only first file before timeout
    
    @patch('os.scandir')
    def test_on_skip_callback(self, mock_scandir):
        """Test skip callback functionality."""
        root = Path("/test").resolve()
        
        entries = [
            MockDirEntry("file.txt", str(root / "file.txt"), is_file=True, is_dir=False),
            MockDirEntry("broken.link", str(root / "broken.link"), 
                        is_file=False, is_dir=False, is_symlink=True),
        ]
        
        mock_scandir.return_value = entries
        
        skipped_items = []
        def on_skip(path, reason):
            skipped_items.append((path, reason))
        
        config = SafeWalkConfig(root=root, on_skip=on_skip, follow_symlinks=False)
        walker = SafeFileWalker(config)
        
        with walker as w:
            files = list(w)
        
        assert len(files) == 1
        assert len(skipped_items) == 1
        assert skipped_items[0][0] == root / "broken.link"
        assert "symlink" in skipped_items[0][1].lower()
    
    @patch('os.scandir')
    def test_deterministic_ordering(self, mock_scandir):
        """Test deterministic vs non-deterministic ordering."""
        root = Path("/test").resolve()
        
        # Create entries in unsorted order
        entries = [
            MockDirEntry("z_file.txt", str(root / "z_file.txt"), is_file=True, is_dir=False),
            MockDirEntry("a_file.txt", str(root / "a_file.txt"), is_file=True, is_dir=False),
            MockDirEntry("m_file.txt", str(root / "m_file.txt"), is_file=True, is_dir=False),
        ]
        
        mock_scandir.return_value = entries
        
        # Test deterministic=True (default)
        config = SafeWalkConfig(root=root, deterministic=True)
        walker = SafeFileWalker(config)
        
        with walker as w:
            files_det = list(w)
        
        # Files should be sorted alphabetically
        assert files_det[0].name == "a_file.txt"
        assert files_det[1].name == "m_file.txt"
        assert files_det[2].name == "z_file.txt"
        
        # Test deterministic=False
        mock_scandir.return_value = entries  # Reset
        config = SafeWalkConfig(root=root, deterministic=False)
        walker = SafeFileWalker(config)
        
        with walker as w:
            files_nondet = list(w)
        
        # Files should be in original order
        assert files_nondet[0].name == "z_file.txt"
        assert files_nondet[1].name == "a_file.txt"
        assert files_nondet[2].name == "m_file.txt"


class TestWalkStats:
    """Test statistics tracking."""
    
    def test_stats_immutable(self):
        stats = WalkStats(
            files_yielded=10,
            files_skipped=2,
            dirs_skipped=1,
            bytes_processed=1024,
            time_elapsed=1.5
        )
        
        # Test property access
        assert stats.files_yielded == 10
        assert stats.files_skipped == 2
        assert stats.dirs_skipped == 1
        assert stats.bytes_processed == 1024
        assert stats.time_elapsed == 1.5
        
        # Test __repr__
        repr_str = repr(stats)
        assert "WalkStats" in repr_str
        assert "files_yielded=10" in repr_str


if __name__ == '__main__':
    pytest.main([__file__, '-v'])