"""
Utility functions for Substack2Markdown.
"""

import re
import unicodedata
from typing import Optional
from datetime import datetime
from pathlib import Path


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """
    Sanitize a string for use as a filename.
    
    Args:
        name: The string to sanitize
        max_length: Maximum length of the resulting filename
    
    Returns:
        A safe filename string
    """
    # Normalize unicode characters
    name = unicodedata.normalize('NFKD', name)
    name = name.encode('ascii', 'ignore').decode('ascii')
    
    # Replace problematic characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'[\s_]+', '-', name)
    name = re.sub(r'-+', '-', name)
    name = name.strip('-.')
    
    # Truncate if too long
    if len(name) > max_length:
        name = name[:max_length].rsplit('-', 1)[0]
    
    return name or 'untitled'


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse a date string in various formats.
    
    Args:
        date_str: Date string to parse
    
    Returns:
        datetime object or None if parsing fails
    """
    formats = [
        '%Y-%m-%dT%H:%M:%S.%fZ',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d',
        '%B %d, %Y',
        '%b %d, %Y',
        '%d %B %Y',
        '%d %b %Y',
    ]
    
    if not date_str:
        return None
    
    date_str = date_str.strip()
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Try ISO format with timezone handling
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        pass
    
    return None


def get_file_size_str(size_bytes: int) -> str:
    """
    Convert bytes to human-readable size string.
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Human-readable size string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def count_words(text: str) -> int:
    """
    Count words in text.
    
    Args:
        text: Text to count words in
    
    Returns:
        Word count
    """
    # Remove markdown formatting
    text = re.sub(r'[#*_`\[\]()]', '', text)
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Split and count
    words = text.split()
    return len(words)


def estimate_read_time(word_count: int, wpm: int = 200) -> int:
    """
    Estimate reading time in minutes.
    
    Args:
        word_count: Number of words
        wpm: Words per minute (default: 200)
    
    Returns:
        Estimated reading time in minutes
    """
    return max(1, round(word_count / wpm))


def ensure_dir(path: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
    
    Returns:
        The path
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_domain(url: str) -> str:
    """
    Extract domain from URL.
    
    Args:
        url: Full URL
    
    Returns:
        Domain name
    """
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.netloc or ''


def truncate_string(s: str, max_length: int, suffix: str = '...') -> str:
    """
    Truncate a string to a maximum length.
    
    Args:
        s: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated string
    """
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


class ProgressTracker:
    """Track and display download progress."""
    
    def __init__(self, total: int):
        self.total = total
        self.downloaded = 0
        self.failed = 0
        self.skipped = 0
    
    @property
    def processed(self) -> int:
        return self.downloaded + self.failed + self.skipped
    
    @property
    def remaining(self) -> int:
        return self.total - self.processed
    
    @property
    def success_rate(self) -> float:
        if self.processed == 0:
            return 0.0
        return self.downloaded / self.processed * 100
    
    def add_success(self):
        self.downloaded += 1
    
    def add_failure(self):
        self.failed += 1
    
    def add_skip(self):
        self.skipped += 1
    
    def summary(self) -> str:
        return (
            f"Downloaded: {self.downloaded}, "
            f"Failed: {self.failed}, "
            f"Skipped: {self.skipped}, "
            f"Total: {self.total}"
        )
