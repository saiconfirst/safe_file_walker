 Понял! GitHub неправильно отображает HTML-теги. Вот исправленная версия — только Markdown, без HTML:

```markdown
# 🔒 Safe File Walker

**Finally, a secure alternative to `os.walk()`**

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![MIT License](https://img.shields.io/badge/license-MIT-green.svg)
![Production Ready](https://img.shields.io/badge/status-production--ready-brightgreen.svg)

---

## 🚀 Quick Start


## 🛡️ Security Features

| Threat | Protection |
|--------|------------|
| **Path Traversal** | `is_relative_to()` strict checking |
| **Symlink attacks** | Optional following, always validated |
| **Hardlink duplicates** | LRU cache by (device, inode) |
| **Infinite recursion** | Depth limits + timeout |
| **DoS via huge dirs** | Rate limiting (MB/sec) |
| **Race conditions** | Atomic `lstat()`, TOCTOU-safe |

---

## ⚡ Why not `os.walk()`?

| Feature | `os.walk()` | **SafeFileWalker** |
|---------|-------------|-------------------|
| Symlink escapes | ❌ Vulnerable | ✅ **Blocked** |
| Hardlink dedup | ❌ Processed N× | ✅ **LRU cache** |
| Infinite loops | ❌ Hangs forever | ✅ **Timeout/depth** |
| Rate limiting | ❌ Unrestricted | ✅ **MB/sec limit** |
| Real-time stats | ❌ Silent | ✅ **Live statistics** |
| Callbacks on skip | ❌ No | ✅ **Observability** |

---

## 💼 Use Cases

- 🔍 **Antivirus/EDR** — Safe scanning of user uploads
- 💾 **Backup systems** — Deduplication, no symlink escapes  
- ☁️ **Cloud storage** — Tenant isolation, quota enforcement
- 🕵️ **Forensics** — Deterministic, auditable traversal
- 🌐 **Web hosting** — Secure file manager backend

---

## 📦 Installation

```bash
# From PyPI (coming soon)
pip install safe-file-walker

# Or just copy the file (zero dependencies)
wget https://raw.githubusercontent.com/saiconfirst/safe_file_walker/main/safe_file_walker.py
```

---

## 📊 Performance

- **Zero-allocation hot path** — No GC pressure during traversal
- **`__slots__` everywhere** — Minimal memory footprint
- **Lazy evaluation** — Generator-based, constant memory
- **Optional determinism** — Sorted or fast mode

---

## 📝 License

MIT License — free for commercial use. See [LICENSE](LICENSE).

---

**🔥 The filesystem walker Python should have had 20 years ago 🔥**
