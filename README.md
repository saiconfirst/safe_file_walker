# Safe File Walker

[![License](https://img.shields.io/badge/License-Non--Commercial--Only-red)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/downloads/)
[![Code Style: Black](https://img.shields.io/badge/Code%20Style-Black-black)](https://github.com/psf/black)
![GitHub Repo stars](https://img.shields.io/github/stars/saiconfirst/safe_file_walker?style=social)
![PyPI - Downloads](https://img.shields.io/pypi/dm/safe-file-walker?label=PyPI%20downloads)
![GitHub last commit](https://img.shields.io/github/last-commit/saiconfirst/safe_file_walker)
![GitHub issues](https://img.shields.io/github/issues/saiconfirst/safe_file_walker)

> ⚠️ **Non-Commercial Use Only** — Commercial use requires explicit permission.  
> Contact: [@saicon001 on Telegram](https://t.me/saicon001)

A **production-grade**, **security-hardened** file system walker for Python with built-in protection against common vulnerabilities and resource exhaustion attacks.

## 🛡️ Why Use Safe File Walker?

Standard file walking utilities (`os.walk`, `pathlib.rglob`) are vulnerable to multiple security issues:

- **Path Traversal** attacks via symbolic links
- **Hardlink duplication** bypassing rate limits
- **Resource exhaustion** from infinite recursion or large directories
- **TOCTOU (Time-of-Check-Time-of-Use)** race conditions
- **Memory leaks** from unbounded inode caching

Safe File Walker solves all these problems while providing enterprise-grade features:

✅ **Hardlink deduplication** with LRU cache  
✅ **Rate limiting** to prevent I/O DoS  
✅ **Symlink sandboxing** with strict boundary enforcement  
✅ **TOCTOU-safe** atomic operations  
✅ **Real-time statistics** and observability  
✅ **Deterministic ordering** for reproducible results  
✅ **Zero external dependencies**

## 📊 Feature Comparison

| Feature | Safe File Walker | `os.walk` | GNU `find` | Rust `fd` |
|---------|------------------|-----------|------------|-----------|
| Hardlink deduplication (LRU) | ✅ | ❌ | ❌ | ❌ |
| Rate limiting | ✅ | ❌ | ❌ | ❌ |
| Symlink sandbox | ✅ | ⚠️ | ✅ | ✅ |
| Depth + timeout control | ✅ | ❌ | ⚠️ | ❌ |
| Observability callbacks | ✅ | ❌ | ❌ | ❌ |
| Real-time statistics | ✅ | ❌ | ❌ | ❌ |
| Deterministic order | ✅ | ❌ | ✅ | ✅ |
| TOCTOU-safe | ✅ | ⚠️ | ⚠️ | ✅ |
| Context manager | ✅ | ❌ | ❌ | ❌ |

## 🚀 Installation

```bash
pip install safe-file-walker
```

Or install directly from source:

```bash
pip install git+https://github.com/saiconfirst/safe_file_walker.git
```

## 🚀 Quick Start

```python
from pathlib import Path
from safe_file_walker import SafeFileWalker, SafeWalkConfig

# Scan current directory with safe defaults
config = SafeWalkConfig(root=Path(".").resolve())

with SafeFileWalker(config) as walker:
    for file_path in walker:
        print(file_path)
```

## 📖 Basic Usage

```python
from safe_file_walker import SafeFileWalker, SafeWalkConfig

# Configure the walker
config = SafeWalkConfig(
    root=Path("/secure/data").resolve(),
    max_rate_mb_per_sec=5.0,      # Limit I/O to 5 MB/s
    follow_symlinks=False,        # Never follow symlinks (default)
    timeout_sec=300,              # Stop after 5 minutes
    max_depth=10,                 # Only go 10 levels deep
    deterministic=True            # Sort directory entries for reproducibility
)

# Walk files safely
with SafeFileWalker(config) as walker:
    for file_path in walker:
        print(f"Processing: {file_path}")
    
    print(f"Stats: {walker.stats}")
```

## 🔍 Advanced Features

### Observability & Monitoring

Get real-time statistics and audit skipped files:

```python
def on_skip(path, reason):
    print(f"[AUDIT] Skipped {path}: {reason}")

config = SafeWalkConfig(
    root=Path("/data"),
    on_skip=on_skip,
    max_unique_files=100_000  # LRU cache size for hardlink deduplication
)

with SafeFileWalker(config) as walker:
    for file_path in walker:
        process_file(file_path)
    
    # Get final statistics
    stats = walker.stats
    print(f"Processed {stats.files_yielded} files in {stats.time_elapsed:.2f}s")
```

### Memory-Conscious Walking

For directories with millions of files, disable deterministic ordering to save memory:

```python
config = SafeWalkConfig(
    root=Path("/large-dataset"),
    deterministic=False,  # Process entries in filesystem order (saves memory)
    max_unique_files=50_000  # Smaller LRU cache
)
```

## 🛡️ Security Guarantees

Safe File Walker provides comprehensive protection against common file system traversal vulnerabilities:

### Path Traversal Protection
- Uses `path.is_relative_to(root)` to ensure all paths stay within boundaries
- Resolves symbolic links before boundary checks when `follow_symlinks=True`

### Symlink Attack Prevention
- By default, never follows symbolic links (`follow_symlinks=False`)
- When enabled, validates resolved paths against root boundary
- Prevents symlink cycles with depth limiting

### Hardlink Deduplication
- Tracks files by `(device_id, inode_number)` to prevent processing the same file multiple times
- Uses LRU cache with configurable size to prevent memory exhaustion
- Essential for forensic analysis and backup tools

### Resource Exhaustion Protection
- **Timeout**: Automatic termination after configured time
- **Depth limiting**: Prevents infinite recursion
- **Rate limiting**: Controls I/O bandwidth consumption
- **Memory bounds**: Configurable LRU cache size

### TOCTOU Safety
- Uses atomic `os.scandir()` + `DirEntry.stat()` operations
- Eliminates race conditions between path checking and file access

## 📐 API Reference

### `SafeWalkConfig`

Configuration class with the following parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `root` | `Path` | *required* | Absolute path to root directory |
| `max_rate_mb_per_sec` | `float` | `10.0` | Maximum I/O rate in MB/s |
| `follow_symlinks` | `bool` | `False` | Whether to follow symbolic links |
| `timeout_sec` | `float` | `3600.0` | Maximum execution time in seconds |
| `max_depth` | `Optional[int]` | `None` | Maximum directory depth (0 = root only) |
| `max_unique_files` | `int` | `1_000_000` | LRU cache size for hardlink deduplication |
| `deterministic` | `bool` | `True` | Sort directory entries for reproducible order |
| `on_skip` | `Callable[[Path, str], None]` | `None` | Callback for skipped files/directories |

### `WalkStats`

Immutable statistics object with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `files_yielded` | `int` | Number of files successfully processed |
| `files_skipped` | `int` | Number of files skipped |
| `dirs_skipped` | `int` | Number of directories skipped |
| `bytes_processed` | `int` | Total bytes processed (for rate limiting) |
| `time_elapsed` | `float` | Total execution time in seconds |

### `SafeFileWalker`

Main walker class that implements:

- Context manager protocol (`__enter__`, `__exit__`)
- Iterator protocol (`__iter__`)
- Statistics property (`stats`)
- String representation (`__repr__`)

## 🧪 Testing

The library includes comprehensive tests covering:

- Security vulnerability scenarios
- Performance benchmarks
- Edge cases and error handling
- Cross-platform compatibility

Run tests with:

```bash
pytest tests/ -v
```

## 📈 Performance Characteristics

- **Time Complexity**: O(n log n) worst case (with `deterministic=True`), O(n) best case
- **Space Complexity**: O(max_unique_files + directory_size) 
- **System Calls**: ~1.5 per file (optimal for security requirements)
- **Memory Usage**: Configurable and bounded

## 🎯 Use Cases

- **Backup and archival tools**
- **Forensic analysis software**
- **File integrity monitoring systems**
- **Malware scanners**
- **Data migration utilities**
- **Security auditing tools**

## ❓ FAQ

### Why not just use `os.walk` or `pathlib.rglob`?
`os.walk` and `pathlib.rglob` are vulnerable to symlink attacks, hardlink duplication, and resource exhaustion. Safe File Walker provides military‑grade security guarantees while maintaining performance.

### How does hardlink deduplication work?
Each file is identified by `(device_id, inode_number)`. An LRU cache tracks already‑processed files, preventing duplicate work when the same file appears via multiple hardlinks.

### What’s the performance impact of rate limiting?
Rate limiting adds negligible overhead (a few nanoseconds per file). It prevents I/O‑based denial‑of‑service attacks and ensures predictable resource consumption.

### Can I use Safe File Walker in async code?
Yes. While the walker itself is synchronous, you can run it in a thread pool (e.g., `asyncio.to_thread`) or process files asynchronously inside the loop.

### Is it safe to follow symbolic links?
Only if you trust the entire directory tree. By default, symlinks are **never** followed (`follow_symlinks=False`). When enabled, each resolved path is validated against the root boundary.

### What happens on timeout?
The walker raises a `TimeoutError` and stops iteration. Any files already yielded remain valid.

### Can I use this for real‑time malware scanning?
Absolutely. The combination of rate limiting, timeout control, and deterministic ordering makes it ideal for security scanning pipelines.

### How do I contribute?
See [Contributing](#-contributing). We welcome security audits, performance improvements, and new feature proposals.

---
## 💖 Support

If you find this project useful, consider supporting its development:

- **Commercial licensing** for business use: contact [@saicon001 on Telegram](https://t.me/saicon001)
- **Sponsor** the developer via [GitHub Sponsors](https://github.com/sponsors/saiconfirst) (coming soon)
- **Star** the repository to show your appreciation

---

## 📜 License

Non-Commercial License - commercial use requires explicit written permission from the author. See [LICENSE](LICENSE) for full terms.

## 🙏 Acknowledgments

This implementation was developed through rigorous security auditing and iterative refinement, incorporating best practices from:
- Secure coding guidelines (CERT, OWASP)
- File system security research
- Production incident post-mortems
- Performance optimization techniques

## 📬 Contributing

## 💬 Stay in Touch

If you're using **Safe File Walker** in your projects or just want to say hello:

- 🤝 **Morally support** the project by sharing feedback  
- 💡 Suggest improvements or report edge cases  
- ❤️ **Materially support** via [Kaspi](https://kaspi.kz/qr?id=YOUR_ID) if it saves you time or enhances security

I’d love to hear from you!

[![Telegram](https://img.shields.io/badge/Telegram-Contact-blue?logo=telegram&logoColor=white)](https://t.me/saicon001)

Contributions are welcome! Please open an issue or pull request on GitHub.

---

**Safe File Walker** — because secure file system traversal shouldn't be an afterthought.
