"""
Substack scraper module.
Extracts post listings and individual post content.
"""

import re
import json
import time
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from config import Config
from browser import SubstackBrowser


@dataclass
class Post:
    """Represents a Substack post."""
    url: str
    title: str
    slug: str
    date: Optional[datetime] = None
    subtitle: Optional[str] = None
    author: Optional[str] = None
    is_paid: bool = False
    is_podcast: bool = False
    excerpt: Optional[str] = None
    word_count: int = 0
    read_time: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        if self.date:
            data['date'] = self.date.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Post':
        """Create from dictionary."""
        if data.get('date') and isinstance(data['date'], str):
            data['date'] = datetime.fromisoformat(data['date'])
        return cls(**data)


@dataclass
class PostContent:
    """Full content of a scraped post."""
    post: Post
    html_content: str
    markdown_content: str = ''
    images: List[Dict[str, str]] = None  # List of {url, local_path}
    
    def __post_init__(self):
        if self.images is None:
            self.images = []


class SubstackScraper:
    """Scrapes content from a Substack publication."""
    
    def __init__(self, config: Config, browser: SubstackBrowser):
        self.config = config
        self.browser = browser
        self._posts_cache: List[Post] = []
    
    def get_all_posts(self) -> List[Post]:
        """Get a list of all posts in the publication."""
        print("\nFetching post list...")
        posts = []
        
        # Try multiple methods to get post list
        
        # Method 1: API endpoint (fastest and most reliable)
        api_posts = self._get_posts_from_api()
        if api_posts:
            posts.extend(api_posts)
            print(f"[OK] Found {len(api_posts)} posts via API")
        
        # Method 2: Archive page scraping (fallback)
        if not posts:
            archive_posts = self._get_posts_from_archive()
            if archive_posts:
                posts.extend(archive_posts)
                print(f"[OK] Found {len(archive_posts)} posts from archive")
        
        # Method 3: Sitemap (another fallback)
        if not posts:
            sitemap_posts = self._get_posts_from_sitemap()
            if sitemap_posts:
                posts.extend(sitemap_posts)
                print(f"[OK] Found {len(sitemap_posts)} posts from sitemap")
        
        # Deduplicate by URL
        seen_urls = set()
        unique_posts = []
        for post in posts:
            if post.url not in seen_urls:
                seen_urls.add(post.url)
                unique_posts.append(post)
        
        # Sort by date (newest first)
        unique_posts.sort(key=lambda p: p.date or datetime.min, reverse=True)
        
        # Apply filters
        filtered_posts = self._apply_filters(unique_posts)
        
        print(f"[OK] Total unique posts after filtering: {len(filtered_posts)}")
        self._posts_cache = filtered_posts
        return filtered_posts
    
    def _get_posts_from_api(self) -> List[Post]:
        """Fetch posts using Substack's API."""
        posts = []
        offset = 0
        limit = 12
        
        while True:
            api_url = f"{self.config.substack_url}/api/v1/archive?sort=new&offset={offset}&limit={limit}"
            
            page_source = self.browser.get_page(api_url)
            if not page_source:
                break
            
            try:
                # Extract JSON from page (might be wrapped in HTML)
                soup = BeautifulSoup(page_source, 'lxml')
                
                # Check if it's raw JSON or wrapped
                try:
                    data = json.loads(page_source)
                except json.JSONDecodeError:
                    # Try to extract JSON from pre tag
                    pre_tag = soup.find('pre')
                    if pre_tag:
                        data = json.loads(pre_tag.get_text())
                    else:
                        break
                
                if not data:
                    break
                
                for item in data:
                    post = self._parse_api_post(item)
                    if post:
                        posts.append(post)
                
                if len(data) < limit:
                    break
                
                offset += limit
                time.sleep(1)  # Small delay between API calls
                
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"API parsing error: {e}")
                break
        
        return posts
    
    def _parse_api_post(self, data: Dict) -> Optional[Post]:
        """Parse a post from API response."""
        try:
            slug = data.get('slug', '')
            url = f"{self.config.substack_url}/p/{slug}"
            
            date_str = data.get('post_date') or data.get('published_at')
            date = None
            if date_str:
                try:
                    date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass
            
            return Post(
                url=url,
                title=data.get('title', 'Untitled'),
                slug=slug,
                date=date,
                subtitle=data.get('subtitle'),
                author=data.get('author', {}).get('name') if isinstance(data.get('author'), dict) else None,
                is_paid=data.get('audience') == 'only_paid',
                is_podcast=data.get('type') == 'podcast',
                excerpt=data.get('description'),
                word_count=data.get('wordcount', 0),
            )
        except Exception as e:
            print(f"Error parsing API post: {e}")
            return None
    
    def _get_posts_from_archive(self) -> List[Post]:
        """Scrape posts from the archive page."""
        posts = []
        
        archive_url = f"{self.config.substack_url}/archive"
        page_source = self.browser.get_page(archive_url)
        
        if not page_source:
            return posts
        
        # Scroll to load all posts (for lazy-loaded archives)
        self.browser.scroll_to_bottom()
        page_source = self.browser.driver.page_source
        
        soup = BeautifulSoup(page_source, 'lxml')
        
        # Find post containers (various Substack layouts)
        post_selectors = [
            'article',
            '.post-preview',
            '[class*="post"]',
            'a[href*="/p/"]'
        ]
        
        for selector in post_selectors:
            elements = soup.select(selector)
            for elem in elements:
                post = self._parse_archive_post(elem, soup)
                if post and post.url not in [p.url for p in posts]:
                    posts.append(post)
        
        return posts
    
    def _parse_archive_post(self, elem, soup: BeautifulSoup) -> Optional[Post]:
        """Parse a post from archive HTML element."""
        try:
            # Find the post link
            if elem.name == 'a' and '/p/' in elem.get('href', ''):
                link = elem
            else:
                link = elem.find('a', href=re.compile(r'/p/'))
            
            if not link:
                return None
            
            href = link.get('href', '')
            if not href or '/p/' not in href:
                return None
            
            # Build full URL
            url = urljoin(self.config.substack_url, href)
            
            # Extract slug
            slug_match = re.search(r'/p/([^/?]+)', url)
            slug = slug_match.group(1) if slug_match else ''
            
            # Find title
            title_elem = elem.find(['h1', 'h2', 'h3', 'h4']) or link
            title = title_elem.get_text(strip=True) if title_elem else 'Untitled'
            
            # Find date
            date = None
            date_elem = elem.find(['time', '[datetime]'])
            if date_elem:
                date_str = date_elem.get('datetime') or date_elem.get_text()
                try:
                    date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass
            
            # Check if paid
            is_paid = bool(elem.find(class_=re.compile(r'paid|premium|locked|subscriber')))
            
            return Post(
                url=url,
                title=title,
                slug=slug,
                date=date,
                is_paid=is_paid,
            )
            
        except Exception:
            return None
    
    def _get_posts_from_sitemap(self) -> List[Post]:
        """Get posts from sitemap.xml."""
        posts = []
        
        sitemap_url = f"{self.config.substack_url}/sitemap.xml"
        page_source = self.browser.get_page(sitemap_url)
        
        if not page_source:
            return posts
        
        soup = BeautifulSoup(page_source, 'lxml-xml')
        
        for url_elem in soup.find_all('url'):
            loc = url_elem.find('loc')
            if loc and '/p/' in loc.get_text():
                url = loc.get_text()
                slug_match = re.search(r'/p/([^/?]+)', url)
                slug = slug_match.group(1) if slug_match else ''
                
                lastmod = url_elem.find('lastmod')
                date = None
                if lastmod:
                    try:
                        date = datetime.fromisoformat(lastmod.get_text().replace('Z', '+00:00'))
                    except ValueError:
                        pass
                
                posts.append(Post(
                    url=url,
                    title=slug.replace('-', ' ').title(),  # Placeholder title
                    slug=slug,
                    date=date,
                ))
        
        return posts
    
    def _apply_filters(self, posts: List[Post]) -> List[Post]:
        """Apply date and paid filters to posts."""
        filtered = posts
        
        if self.config.start_date:
            filtered = [
                p for p in filtered 
                if p.date is None or p.date >= self.config.start_date
            ]
        
        if self.config.end_date:
            filtered = [
                p for p in filtered 
                if p.date is None or p.date <= self.config.end_date
            ]
        
        if self.config.paid_only:
            filtered = [p for p in filtered if p.is_paid]
        
        return filtered
    
    def get_post_content(self, post: Post) -> Optional[PostContent]:
        """Fetch and parse full content of a post."""
        print(f"  Fetching: {post.title[:50]}...")
        
        page_source = self.browser.get_page(post.url)
        if not page_source:
            print(f"  [FAIL] Failed to load: {post.url}")
            return None
        
        soup = BeautifulSoup(page_source, 'lxml')
        
        # Extract main content
        content_selectors = [
            '.body.markup',
            '.post-content',
            'article .body',
            '.available-content',
            '[class*="post-content"]',
            'article'
        ]
        
        content_elem = None
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                break
        
        if not content_elem:
            print(f"  [FAIL] Could not find content for: {post.url}")
            return None
        
        # Update post metadata from page
        self._update_post_metadata(post, soup)
        
        # Clean the content
        html_content = self._clean_html(content_elem)
        
        return PostContent(
            post=post,
            html_content=str(html_content),
        )
    
    def _update_post_metadata(self, post: Post, soup: BeautifulSoup):
        """Update post metadata from the full page."""
        # Get actual title
        title_elem = soup.select_one('h1.post-title, h1[class*="title"], article h1')
        if title_elem:
            post.title = title_elem.get_text(strip=True)
        
        # Get subtitle
        subtitle_elem = soup.select_one('.subtitle, h2.post-subtitle, [class*="subtitle"]')
        if subtitle_elem:
            post.subtitle = subtitle_elem.get_text(strip=True)
        
        # Get author
        author_elem = soup.select_one('.author-name, [class*="author"]')
        if author_elem:
            post.author = author_elem.get_text(strip=True)
        
        # Get date from page if not already set
        if not post.date:
            date_elem = soup.select_one('time[datetime], .post-date')
            if date_elem:
                date_str = date_elem.get('datetime') or date_elem.get_text()
                try:
                    post.date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass
    
    def _clean_html(self, elem: BeautifulSoup) -> BeautifulSoup:
        """Clean HTML content by removing unwanted elements."""
        # Elements to remove
        remove_selectors = [
            'script',
            'style',
            'noscript',
            '.subscription-widget',
            '.subscribe-widget',
            '.paywall',
            '.share-buttons',
            '.comments',
            '[class*="share"]',
            '[class*="social"]',
            '[class*="footer"]',
            '.post-footer',
            '.publication-footer',
        ]
        
        for selector in remove_selectors:
            for tag in elem.select(selector):
                tag.decompose()
        
        return elem
    
    def extract_images(self, html_content: str) -> List[Dict[str, str]]:
        """Extract image URLs from HTML content."""
        images = []
        soup = BeautifulSoup(html_content, 'lxml')
        
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if src:
                # Handle relative URLs
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = urljoin(self.config.substack_url, src)
                
                # Skip tiny images (likely tracking pixels)
                width = img.get('width')
                height = img.get('height')
                if width and height:
                    try:
                        if int(width) < 10 or int(height) < 10:
                            continue
                    except ValueError:
                        pass
                
                images.append({
                    'url': src,
                    'alt': img.get('alt', ''),
                })
        
        return images
