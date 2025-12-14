"""
Configuration management for Substack2Markdown.
Loads settings from environment variables and .env file.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv


# Load .env file from current directory or parent directories
load_dotenv()


def get_bool(key: str, default: bool = False) -> bool:
    """Parse boolean from environment variable."""
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')


def get_int(key: str, default: int) -> int:
    """Parse integer from environment variable."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def get_date(key: str) -> Optional[datetime]:
    """Parse date from environment variable (YYYY-MM-DD format)."""
    value = os.getenv(key)
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        print(f"Warning: Invalid date format for {key}: {value}. Use YYYY-MM-DD.")
        return None


@dataclass
class Config:
    """Configuration settings for the scraper."""
    
    # Required
    substack_url: str = field(default_factory=lambda: os.getenv('SUBSTACK_URL', ''))
    
    # Authentication
    email: Optional[str] = field(default_factory=lambda: os.getenv('SUBSTACK_EMAIL'))
    password: Optional[str] = field(default_factory=lambda: os.getenv('SUBSTACK_PASSWORD'))
    use_browser_session: bool = field(default_factory=lambda: get_bool('USE_BROWSER_SESSION', True))
    
    # Output
    output_dir: Path = field(default_factory=lambda: Path(os.getenv('OUTPUT_DIR', './output')))
    download_images: bool = field(default_factory=lambda: get_bool('DOWNLOAD_IMAGES', True))
    image_format: str = field(default_factory=lambda: os.getenv('IMAGE_FORMAT', 'original'))
    save_html: bool = field(default_factory=lambda: get_bool('SAVE_HTML', False))
    
    # Rate limiting
    request_delay: int = field(default_factory=lambda: get_int('REQUEST_DELAY', 5))
    max_retries: int = field(default_factory=lambda: get_int('MAX_RETRIES', 3))
    page_timeout: int = field(default_factory=lambda: get_int('PAGE_TIMEOUT', 30))
    
    # Content filters
    start_date: Optional[datetime] = field(default_factory=lambda: get_date('START_DATE'))
    end_date: Optional[datetime] = field(default_factory=lambda: get_date('END_DATE'))
    paid_only: bool = field(default_factory=lambda: get_bool('PAID_ONLY', False))
    
    # Advanced
    headless: bool = field(default_factory=lambda: get_bool('HEADLESS', False))
    chrome_user_data_dir: Optional[str] = field(
        default_factory=lambda: os.getenv('CHROME_USER_DATA_DIR')
    )
    log_level: str = field(default_factory=lambda: os.getenv('LOG_LEVEL', 'INFO'))
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        # Normalize URL
        if self.substack_url:
            self.substack_url = self.substack_url.rstrip('/')
        
        # Ensure output directory exists
        self.output_dir = Path(self.output_dir)
        
        # Validate image format
        valid_formats = ('original', 'jpg', 'jpeg', 'png', 'webp')
        if self.image_format.lower() not in valid_formats:
            print(f"Warning: Invalid image format '{self.image_format}'. Using 'original'.")
            self.image_format = 'original'
    
    def validate(self) -> bool:
        """Validate that required configuration is present."""
        errors = []
        
        if not self.substack_url:
            errors.append("SUBSTACK_URL is required")
        elif not self.substack_url.startswith('http'):
            errors.append("SUBSTACK_URL must start with http:// or https://")
        
        if not self.use_browser_session and not (self.email and self.password):
            errors.append(
                "Either USE_BROWSER_SESSION must be true, or "
                "SUBSTACK_EMAIL and SUBSTACK_PASSWORD must be set"
            )
        
        if errors:
            for error in errors:
                print(f"Configuration error: {error}")
            return False
        
        return True
    
    @property
    def publication_name(self) -> str:
        """Extract publication name from URL."""
        if not self.substack_url:
            return 'unknown'
        # Extract subdomain or domain name
        url = self.substack_url.replace('https://', '').replace('http://', '')
        return url.split('.')[0].split('/')[0]
    
    @property
    def publication_output_dir(self) -> Path:
        """Get the output directory for this publication."""
        return self.output_dir / self.publication_name
    
    @property
    def posts_dir(self) -> Path:
        """Get the posts output directory."""
        return self.publication_output_dir / 'posts'
    
    @property
    def images_dir(self) -> Path:
        """Get the images output directory."""
        return self.publication_output_dir / 'images'
    
    def ensure_directories(self):
        """Create output directories if they don't exist."""
        self.posts_dir.mkdir(parents=True, exist_ok=True)
        if self.download_images:
            self.images_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
config = Config()
