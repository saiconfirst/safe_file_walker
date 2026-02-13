&lt;p align="center"&gt;
  🔒 &lt;b&gt;Safe File Walker&lt;/b&gt; 🔒
&lt;/p&gt;

&lt;p align="center"&gt;
  &lt;b&gt;Finally, a secure alternative to &lt;code&gt;os.walk()&lt;/code&gt;&lt;/b&gt;
&lt;/p&gt;

&lt;p align="center"&gt;
  &lt;img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"&gt;
  &lt;img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License"&gt;
  &lt;img src="https://img.shields.io/badge/status-production--ready-brightgreen.svg" alt="Production Ready"&gt;
&lt;/p&gt;

---

## 🚀 Quick Start

```python
from pathlib import Path
from safe_file_walker import SafeWalkConfig, SafeFileWalker

config = SafeWalkConfig(
    root=Path("/var/www/uploads"),
    max_rate_mb_per_sec=50,      # Don't kill the disk
    timeout_sec=3600,             # Max 1 hour
    max_depth=5,                  # Don't go too deep
    follow_symlinks=False,        # Sandbox mode
)

with SafeFileWalker(config) as walker:
    for file_path in walker:
        process(file_path)

print(walker.stats)  
# Files: 15420, Skipped: 3, Dirs skipped: 1, Bytes: 2147483648, Time: 45.23s
