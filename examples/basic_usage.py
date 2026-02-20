#!/usr/bin/env python3
"""
Basic usage examples for safe-file-walker.
"""
from pathlib import Path
from safe_file_walker import SafeFileWalker, SafeWalkConfig


def example_basic_scan():
    """Basic directory scanning."""
    print("=== Basic Directory Scan ===")
    
    # Scan current directory
    config = SafeWalkConfig(root=Path(".").resolve())
    
    with SafeFileWalker(config) as walker:
        file_count = 0
        for file_path in walker:
            file_count += 1
            if file_count <= 5:  # Show first 5 files
                print(f"  {file_path}")
        
        print(f"\nTotal files found: {file_count}")
        print(f"Stats: {walker.stats}")
    print()


def example_with_limits():
    """Scanning with resource limits."""
    print("=== Scanning with Resource Limits ===")
    
    config = SafeWalkConfig(
        root=Path(".").resolve(),
        max_depth=2,           # Only go 2 levels deep
        max_rate_mb_per_sec=1.0,  # Limit I/O to 1 MB/s
        timeout_sec=30,        # Stop after 30 seconds
        deterministic=True     # Process in sorted order
    )
    
    print(f"Configuration:")
    print(f"  Max depth: {config.max_depth}")
    print(f"  Rate limit: {config.max_rate_mb_per_sec} MB/s")
    print(f"  Timeout: {config.timeout_sec} seconds")
    print(f"  Deterministic: {config.deterministic}")
    print()
    
    with SafeFileWalker(config) as walker:
        file_count = 0
        for file_path in walker:
            file_count += 1
            if file_count <= 3:
                print(f"  {file_path}")
        
        print(f"\nFiles found (with limits): {file_count}")
        print(f"Stats: {walker.stats}")
    print()


def example_skip_callback():
    """Using the skip callback for auditing."""
    print("=== Skip Callback for Auditing ===")
    
    def on_skip(path, reason):
        print(f"  [SKIP] {path.name}: {reason}")
    
    config = SafeWalkConfig(
        root=Path(".").resolve(),
        on_skip=on_skip,
        follow_symlinks=False  # Will skip symlinks
    )
    
    with SafeFileWalker(config) as walker:
        file_count = 0
        for file_path in walker:
            file_count += 1
        
        print(f"\nFiles processed: {file_count}")
        print(f"Files skipped: {walker.stats.files_skipped}")
        print(f"Dirs skipped: {walker.stats.dirs_skipped}")
    print()


def example_hardlink_deduplication():
    """Demonstrate hardlink deduplication."""
    print("=== Hardlink Deduplication ===")
    
    config = SafeWalkConfig(
        root=Path(".").resolve(),
        max_unique_files=1000  # LRU cache size
    )
    
    print("Note: Hardlinks are automatically deduplicated.")
    print("Files with same (device_id, inode) are processed only once.")
    print()
    
    with SafeFileWalker(config) as walker:
        file_count = 0
        for file_path in walker:
            file_count += 1
        
        stats = walker.stats
        print(f"Files yielded: {stats.files_yielded}")
        print(f"Files skipped (duplicates): {stats.files_skipped}")
        print(f"Total unique files: {stats.files_yielded}")
    print()


def example_performance_stats():
    """Show performance statistics."""
    print("=== Performance Statistics ===")
    
    config = SafeWalkConfig(root=Path(".").resolve())
    
    with SafeFileWalker(config) as walker:
        file_count = 0
        total_size = 0
        
        for file_path in walker:
            file_count += 1
            try:
                total_size += file_path.stat().st_size
            except OSError:
                pass
        
        stats = walker.stats
        print(f"Performance:")
        print(f"  Files processed: {file_count}")
        print(f"  Total size: {total_size / 1024 / 1024:.2f} MB")
        print(f"  Time elapsed: {stats.time_elapsed:.2f} seconds")
        
        if stats.time_elapsed > 0:
            files_per_sec = stats.files_yielded / stats.time_elapsed
            mb_per_sec = stats.bytes_processed / 1024 / 1024 / stats.time_elapsed
            print(f"  Files/second: {files_per_sec:.1f}")
            print(f"  MB/second: {mb_per_sec:.2f}")
    print()


if __name__ == "__main__":
    example_basic_scan()
    example_with_limits()
    example_skip_callback()
    example_hardlink_deduplication()
    example_performance_stats()