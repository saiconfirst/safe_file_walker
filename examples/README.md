# Examples

Example code showing different ways to use `safe-file-walker`.

## 📁 Files

### `basic_usage.py`
Basic examples showing different configuration options:
- Basic directory scanning
- Scanning with resource limits (depth, rate, timeout)
- Skip callback for auditing skipped files
- Hardlink deduplication demonstration
- Performance statistics

```bash
python basic_usage.py
```

### `security_scanner.py`
Advanced security scanner example:
- Simulates malware scanning pipeline
- Suspicious filename detection
- File hash calculation (SHA256)
- Large file detection
- Executive file identification
- JSON report generation

```bash
python security_scanner.py
```

## 🚀 Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/saiconfirst/safe_file_walker.git
   cd safe_file_walker
   ```

2. **Run examples:**
   ```bash
   cd examples
   python basic_usage.py
   ```

## 🔧 Use Cases

### Backup Tool
```python
from safe_file_walker import SafeFileWalker, SafeWalkConfig
from pathlib import Path
import shutil

def backup_directory(source, destination):
    config = SafeWalkConfig(
        root=Path(source).resolve(),
        max_rate_mb_per_sec=10.0,  # Don't overload I/O
        deterministic=True         # Reproducible order
    )
    
    with SafeFileWalker(config) as walker:
        for filepath in walker:
            dest_path = Path(destination) / filepath.relative_to(source)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(filepath, dest_path)
    
    print(f"Backup complete: {walker.stats.files_yielded} files")
```

### File Integrity Monitor
```python
import hashlib
from safe_file_walker import SafeFileWalker, SafeWalkConfig

def create_integrity_database(root_path):
    integrity_data = {}
    
    config = SafeWalkConfig(root=Path(root_path).resolve())
    
    with SafeFileWalker(config) as walker:
        for filepath in walker:
            try:
                file_hash = hashlib.sha256(filepath.read_bytes()).hexdigest()
                integrity_data[str(filepath)] = {
                    'hash': file_hash,
                    'size': filepath.stat().st_size,
                    'mtime': filepath.stat().st_mtime
                }
            except (OSError, IOError):
                continue
    
    return integrity_data
```

### Log File Analyzer
```python
from safe_file_walker import SafeWalkConfig, SafeFileWalker
import re

def analyze_logs(root_path, pattern):
    matches = []
    
    def on_skip(path, reason):
        if 'symlink' in reason.lower():
            print(f"Skipping symlink: {path}")
    
    config = SafeWalkConfig(
        root=Path(root_path).resolve(),
        on_skip=on_skip,
        follow_symlinks=False
    )
    
    with SafeFileWalker(config) as walker:
        for filepath in walker:
            if filepath.suffix == '.log':
                try:
                    content = filepath.read_text(encoding='utf-8', errors='ignore')
                    if re.search(pattern, content):
                        matches.append(str(filepath))
                except (OSError, IOError, UnicodeDecodeError):
                    continue
    
    return matches
```

### Malware Scanner (Production)
```python
from safe_file_walker import SafeWalkConfig, SafeFileWalker
import yara  # yara-python for pattern matching

def scan_for_malware(root_path, yara_rules):
    config = SafeWalkConfig(
        root=Path(root_path).resolve(),
        follow_symlinks=False,  # Critical for security!
        max_depth=20,
        timeout_sec=600
    )
    
    infected_files = []
    
    with SafeFileWalker(config) as walker:
        for filepath in walker:
            try:
                matches = yara_rules.match(str(filepath))
                if matches:
                    infected_files.append({
                        'file': str(filepath),
                        'matches': [str(m) for m in matches]
                    })
            except (OSError, IOError, yara.Error):
                continue
    
    return infected_files
```

## ⚠️ Security Notes

- Always use `follow_symlinks=False` for security-sensitive applications
- Rate limiting prevents I/O-based denial-of-service
- Timeout protection ensures scans complete within reasonable time
- Hardlink deduplication prevents infinite loops in malicious file systems
- Container-aware scanning is built-in (via boundary checking)

## 📊 Performance Tips

1. **For large directories:** Set `deterministic=False` to save memory
2. **For network drives:** Reduce `max_rate_mb_per_sec` to avoid saturation
3. **For deep hierarchies:** Set appropriate `max_depth` to limit recursion
4. **For memory-constrained systems:** Reduce `max_unique_files` cache size
5. **Use `on_skip` callback** to audit why files were skipped

## 🔍 Debugging

Enable verbose output with a custom `on_skip` callback:

```python
def verbose_skip(path, reason):
    print(f"[DEBUG] Skipped {path}: {reason}")

config = SafeWalkConfig(root=Path("."), on_skip=verbose_skip)
```