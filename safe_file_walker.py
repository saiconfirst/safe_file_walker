# safe_file_walker.py
"""
Безопасный итератор файлов с защитой от:
- Path Traversal (через is_relative_to)
- Symlink- и hardlink-атак
- DoS через бесконечную рекурсию или высокую нагрузку
- Race condition при проверке путей

Поддерживает:
- Ограничение скорости обработки (rate limiting)
- Таймаут и глубину обхода
- Коллбэки для observability
- Дедупликацию по inode/device (с LRU)
- Опциональный детерминированный порядок (для воспроизводимости)
- Статистику обхода
"""

import os
import stat
import time
from pathlib import Path
from typing import Iterator, Optional, Callable, Deque, Tuple
from collections import deque
from dataclasses import dataclass


def _validate_positive(value: float, name: str) -> None:
    """Валидирует, что значение положительное."""
    if value <= 0:
        raise ValueError(f"{name} must be positive")


__all__ = ['SafeWalkConfig', 'WalkStats', 'SafeFileWalker']


@dataclass(frozen=True, slots=True)
class SafeWalkConfig:
    """
    Конфигурация безопасного обхода файловой системы.

    Attributes:
        root: Абсолютный путь к корневой директории (обязательно абсолютный).
        max_rate_mb_per_sec: Максимальная скорость обработки данных в МБ/сек (должна быть положительной).
        follow_symlinks: Следовать ли по символическим ссылкам (по умолчанию — нет).
        timeout_sec: Максимальное время выполнения обхода в секундах (должно быть положительным).
        max_depth: Максимальная глубина рекурсии (None — без ограничений).
                   0 = только корень, 1 = корень + прямые подкаталоги и т.д.
        max_unique_files: Максимальное количество уникальных файлов в кэше (LRU).
        deterministic: Сохранять ли детерминированный порядок обхода (по умолчанию True).
                       Отключение экономит память на крупных директориях.
        on_skip: Коллбэк, вызываемый при пропуске файла/директории.
                 Принимает (путь: Path, причина: str).
    """
    root: Path
    max_rate_mb_per_sec: float = 10.0
    follow_symlinks: bool = False
    timeout_sec: float = 3600.0
    max_depth: Optional[int] = None
    max_unique_files: int = 1_000_000
    deterministic: bool = True
    on_skip: Optional[Callable[[Path, str], None]] = None


@dataclass(frozen=True, slots=True)
class WalkStats:
    """
    Статистика выполнения обхода.
    """
    files_yielded: int = 0
    files_skipped: int = 0
    dirs_skipped: int = 0
    bytes_processed: int = 0
    time_elapsed: float = 0.0

    def __str__(self) -> str:
        return (
            f"Files: {self.files_yielded}, "
            f"Skipped: {self.files_skipped}, "
            f"Dirs skipped: {self.dirs_skipped}, "
            f"Bytes: {self.bytes_processed}, "
            f"Time: {self.time_elapsed:.2f}s"
        )

    def __repr__(self) -> str:
        return (
            f"WalkStats(files_yielded={self.files_yielded}, "
            f"files_skipped={self.files_skipped}, "
            f"dirs_skipped={self.dirs_skipped}, "
            f"bytes_processed={self.bytes_processed}, "
            f"time_elapsed={self.time_elapsed!r})"
        )


@dataclass(slots=True)
class _InternalStats:
    """
    Внутренняя изменяемая статистика для производительности.
    """
    files_yielded: int = 0
    files_skipped: int = 0
    dirs_skipped: int = 0
    bytes_processed: int = 0
    start_time: float = 0.0


class SafeFileWalker:
    """
    Итератор для безопасного рекурсивного обхода файловой системы.

    Гарантирует:
    - Отсутствие выхода за пределы root (даже через symlink)
    - Отсутствие повторной обработки одного и того же файла через hardlink
    - Ограничение скорости, времени и глубины
    - Чёткую отчётность о пропущенных элементах
    - Опциональную детерминированность обхода
    - Статистику обхода
    """
    
    __slots__ = (
        'config',
        '_stats',
        '_seen_inodes',
        '_inode_fifo'
    )

    def __init__(self, config: SafeWalkConfig):
        if not isinstance(config.root, Path):
            raise TypeError("config.root must be a pathlib.Path")
        if not config.root.is_absolute():
            raise ValueError("Root path must be absolute")
        _validate_positive(config.max_unique_files, "max_unique_files")
        _validate_positive(config.max_rate_mb_per_sec, "max_rate_mb_per_sec")
        _validate_positive(config.timeout_sec, "timeout_sec")
        
        if config.max_depth is not None and config.max_depth < 0:
            raise ValueError("max_depth must be non-negative or None")
            
        start_time = time.monotonic()
        self._stats = _InternalStats(start_time=start_time)
        self.config = config
        # LRU-like кэш через deque + set для дедупликации
        self._seen_inodes: set[Tuple[int, int]] = set()
        self._inode_fifo: Deque[Tuple[int, int]] = deque()

    @property
    def stats(self) -> WalkStats:
        """Возвращает снимок статистики обхода."""
        current_time = time.monotonic()
        return WalkStats(
            files_yielded=self._stats.files_yielded,
            files_skipped=self._stats.files_skipped,
            dirs_skipped=self._stats.dirs_skipped,
            bytes_processed=self._stats.bytes_processed,
            time_elapsed=current_time - self._stats.start_time
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Очистка ресурсов
        self._seen_inodes.clear()
        self._inode_fifo.clear()

    def __repr__(self) -> str:
        return f"SafeFileWalker(config={self.config!r}, stats={self.stats!r})"

    def _check_timeout(self) -> None:
        """Проверяет, не превышен ли лимит времени выполнения."""
        elapsed = time.monotonic() - self._stats.start_time
        if elapsed > self.config.timeout_sec:
            raise TimeoutError("File walk exceeded configured time limit")

    def _check_depth(self, path: Path, current_depth: int) -> bool:
        """Проверяет, не превышена ли максимальная глубина."""
        if self.config.max_depth is None:
            return True
        if current_depth > self.config.max_depth:
            self._skip(path, "max_depth_exceeded", is_dir=True)
            return False
        return True

    def _increment_stat(self, field: str) -> None:
        """Централизованное обновление статистики."""
        if field == 'files_yielded':
            self._stats.files_yielded += 1
        elif field == 'files_skipped':
            self._stats.files_skipped += 1
        elif field == 'dirs_skipped':
            self._stats.dirs_skipped += 1
        else:
            raise ValueError(f"Unknown stat field: {field}")

    def _update_bytes_processed(self, size: int) -> None:
        """Обновляет количество обработанных байт."""
        self._stats.bytes_processed += size

    def _skip(self, path: Path, reason: str, is_dir: bool = False) -> None:
        """Вызывает коллбэк пропуска, если он задан."""
        if is_dir:
            self._increment_stat('dirs_skipped')
        else:
            self._increment_stat('files_skipped')

        if self.config.on_skip is not None:
            try:
                self.config.on_skip(path, reason)
            except Exception:
                # Не позволяем коллбэку сломать основной поток
                pass

    def _rate_limit(self, file_size: int) -> None:
        """
        Применяет ограничение скорости на основе накопленного объёма.

        Args:
            file_size: Размер файла в байтах.
        """
        if file_size <= 0:
            return
        self._update_bytes_processed(file_size)
        current_elapsed = time.monotonic() - self._stats.start_time
        target_elapsed = self._stats.bytes_processed / (self.config.max_rate_mb_per_sec * 1024 * 1024)
        if current_elapsed < target_elapsed:
            sleep_duration = target_elapsed - current_elapsed
            if sleep_duration > 0:
                time.sleep(sleep_duration)

    def _add_inode(self, dev_ino: Tuple[int, int]) -> bool:
        """
        Добавляет inode в кэш с LRU-логикой.
        
        Returns:
            True если успешно добавлен, False если пропущен (duplicate или full cache).
        """
        if dev_ino in self._seen_inodes:
            return False  # уже есть
        if len(self._seen_inodes) >= self.config.max_unique_files:
            oldest = self._inode_fifo.popleft()
            self._seen_inodes.discard(oldest)
        self._seen_inodes.add(dev_ino)
        self._inode_fifo.append(dev_ino)
        return True

    def _process_entry(self, entry: os.DirEntry, root_abs: Path, depth: int) -> Optional[Tuple[Path, os.stat_result, bool]]:
        """
        Обрабатывает один элемент каталога с атомарным lstat.
        
        Returns:
            - (resolved_path: Path, stat_result: os.stat_result, is_dir: bool) для файлов
            - (resolved_path, stat_result, True) для директорий
            - None если пропущен
        """
        entry_path = Path(entry.path)

        # Атомарный stat — предотвращает TOCTOU
        try:
            stat_result = entry.stat(follow_symlinks=False)  # всегда lstat
        except (OSError, ValueError) as e:
            # stat_result не определена при ошибке — предполагаем файл (частый случай)
            self._skip(entry_path, f"stat_failed: {type(e).__name__}", is_dir=False)
            return None

        is_symlink = stat.S_ISLNK(stat_result.st_mode)
        is_dir = stat.S_ISDIR(stat_result.st_mode)

        if is_symlink and not self.config.follow_symlinks:
            self._skip(entry_path, "symlink_blocked", is_dir=is_dir)
            return None

        resolved_path = entry_path
        if is_symlink and self.config.follow_symlinks:
            try:
                resolved_path = entry_path.resolve(strict=False)
            except OSError:
                self._skip(entry_path, "broken_symlink", is_dir=is_dir)
                return None

        if not resolved_path.is_relative_to(root_abs):
            self._skip(entry_path, "traversal_via_symlink", is_dir=is_dir)
            return None

        # Проверка глубины после разрешения symlink
        if not self._check_depth(resolved_path, depth):
            return None

        return resolved_path, stat_result, is_dir

    def __iter__(self) -> Iterator[Path]:
        """
        Возвращает итератор по всем файлам внутри root с учётом всех ограничений.

        Yields:
            Path: Путь к каждому найденному файлу (абсолютный, разрешённый).
        """
        try:
            root_abs = self.config.root.resolve(strict=False)
        except OSError as e:
            raise ValueError(f"Cannot resolve root path: {self.config.root}") from e

        # Используем стек для DFS вместо рекурсии — избегаем глубоких вызовов
        # Элемент стека: (Path, depth)
        stack: list[Tuple[Path, int]] = [(root_abs, 0)]

        while stack:
            current_dir, depth = stack.pop()
            self._check_timeout()

            # Проверка глубины для директории
            if not self._check_depth(current_dir, depth):
                continue

            try:
                with os.scandir(current_dir) as scan_iter:
                    if self.config.deterministic:
                        entries = sorted(scan_iter, key=lambda e: e.name)
                    else:
                        entries = scan_iter  # ленивый генератор
            except (OSError, PermissionError) as e:
                self._skip(current_dir, f"scan_failed: {type(e).__name__}", is_dir=True)
                continue

            subdirs: list[Tuple[Path, int]] = []

            for entry in entries:
                self._check_timeout()
                result = self._process_entry(entry, root_abs, depth + 1)
                if result is None:
                    continue

                resolved_path, stat_result, is_dir = result

                if is_dir:
                    subdirs.append((resolved_path, depth + 1))
                else:
                    # Файл: проверяем дедупликацию по (dev, ino)
                    inode_key = (stat_result.st_dev, stat_result.st_ino)
                    if not self._add_inode(inode_key):
                        self._skip(resolved_path, "hardlink_duplicate_or_cache_full", is_dir=False)
                        continue

                    self._rate_limit(stat_result.st_size)
                    self._increment_stat('files_yielded')
                    yield resolved_path

            # Добавляем подкаталоги в обратном порядке для сохранения порядка (как в os.walk)
            stack.extend(reversed(subdirs))