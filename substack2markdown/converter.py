"""
HTML to Markdown converter module.
Converts Substack HTML content to clean Markdown format.
"""

import re
import hashlib
from typing import Dict, List, Optional
from pathlib import Path
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import markdownify
import requests
from tqdm import tqdm

from config import Config
from scraper import Post, PostContent


class MarkdownConverter:
    """Converts HTML content to Markdown with image handling."""
    
    def __init__(self, config: Config):
        self.config = config
        self._image_map: Dict[str, str] = {}  # URL -> local filename
    
    def convert(self, content: PostContent) -> str:
        """Convert PostContent HTML to Markdown."""
        html = content.html_content
        
        # Pre-process HTML
        html = self._preprocess_html(html)
        
        # Convert to Markdown
        md = markdownify.markdownify(
            html,
            heading_style='atx',
            bullets='-',
            code_language='',
            strip=['script', 'style'],
            escape_asterisks=False,
            escape_underscores=False,
        )
        
        # Post-process Markdown
        md = self._postprocess_markdown(md)
        
        # Add frontmatter
        md = self._add_frontmatter(content.post, md)
        
        content.markdown_content = md
        return md
    
    def _preprocess_html(self, html: str) -> str:
        """Pre-process HTML before conversion."""
        soup = BeautifulSoup(html, 'lxml')
        
        # Handle Substack-specific elements
        
        # Convert button elements to links
        for button in soup.find_all('button'):
            link = button.find('a')
            if link:
                button.replace_with(link)
        
        # Handle embedded content (tweets, videos, etc.)
        for embed in soup.find_all(class_=re.compile(r'embed|iframe')):
            src = embed.get('src', '')
            if src:
                placeholder = soup.new_tag('p')
                placeholder.string = f'[Embedded content: {src}]'
                embed.replace_with(placeholder)
        
        # Handle Substack buttons
        for btn in soup.find_all(class_=re.compile(r'button-wrapper|subscribe-btn')):
            btn.decompose()
        
        # Convert figure elements
        for figure in soup.find_all('figure'):
            img = figure.find('img')
            figcaption = figure.find('figcaption')
            
            if img:
                if figcaption:
                    # Add caption below image
                    caption_text = figcaption.get_text(strip=True)
                    caption = soup.new_tag('em')
                    caption.string = caption_text
                    figure.append(soup.new_tag('br'))
                    figure.append(caption)
                    figcaption.decompose()
                
                # Keep the figure structure simple
                figure.unwrap()
        
        # Handle code blocks
        for pre in soup.find_all('pre'):
            code = pre.find('code')
            if code:
                # Get language from class
                lang = ''
                code_classes = code.get('class', [])
                for cls in code_classes:
                    if cls.startswith('language-'):
                        lang = cls.replace('language-', '')
                        break
                
                # Mark for proper conversion
                pre['data-language'] = lang
        
        # Handle blockquotes
        for bq in soup.find_all('blockquote'):
            # Remove nested blockquotes styling issues
            for nested in bq.find_all('blockquote'):
                nested.unwrap()
        
        # Clean up empty paragraphs
        for p in soup.find_all('p'):
            if not p.get_text(strip=True) and not p.find('img'):
                p.decompose()
        
        return str(soup)
    
    def _postprocess_markdown(self, md: str) -> str:
        """Post-process Markdown after conversion."""
        # Fix multiple blank lines
        md = re.sub(r'\n{3,}', '\n\n', md)
        
        # Fix heading spacing
        md = re.sub(r'(\n#+\s)', r'\n\1', md)
        
        # Fix list formatting
        md = re.sub(r'(\n\s*[-*]\s)', r'\n\1', md)
        
        # Clean up escaped characters
        md = md.replace(r'\[', '[').replace(r'\]', ']')
        md = md.replace(r'\(', '(').replace(r'\)', ')')
        
        # Fix double asterisks not on word boundaries
        md = re.sub(r'\*\*\s+', '** ', md)
        md = re.sub(r'\s+\*\*', ' **', md)
        
        # Remove trailing whitespace
        md = '\n'.join(line.rstrip() for line in md.split('\n'))
        
        # Ensure single newline at end
        md = md.strip() + '\n'
        
        return md
    
    def _add_frontmatter(self, post: Post, md: str) -> str:
        """Add YAML frontmatter to Markdown."""
        frontmatter_lines = [
            '---',
            f'title: "{self._escape_yaml(post.title)}"',
        ]
        
        if post.subtitle:
            frontmatter_lines.append(f'subtitle: "{self._escape_yaml(post.subtitle)}"')
        
        if post.author:
            frontmatter_lines.append(f'author: "{self._escape_yaml(post.author)}"')
        
        if post.date:
            frontmatter_lines.append(f'date: {post.date.strftime("%Y-%m-%d")}')
        
        frontmatter_lines.append(f'url: "{post.url}"')
        
        if post.is_paid:
            frontmatter_lines.append('paid: true')
        
        if post.word_count:
            frontmatter_lines.append(f'word_count: {post.word_count}')
        
        frontmatter_lines.append('---')
        frontmatter_lines.append('')
        
        return '\n'.join(frontmatter_lines) + md
    
    def _escape_yaml(self, text: str) -> str:
        """Escape text for YAML string."""
        if not text:
            return ''
        return text.replace('"', '\\"').replace('\n', ' ')
    
    def download_images(
        self, 
        content: PostContent, 
        progress: bool = True
    ) -> List[Dict[str, str]]:
        """Download images and update content with local paths."""
        if not self.config.download_images:
            return []
        
        # Extract images from HTML
        soup = BeautifulSoup(content.html_content, 'lxml')
        images = []
        
        img_tags = soup.find_all('img')
        if progress and img_tags:
            img_tags = tqdm(img_tags, desc="    Downloading images", leave=False)
        
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            if not src:
                continue
            
            # Skip data URIs
            if src.startswith('data:'):
                continue
            
            # Normalize URL
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = urljoin(self.config.substack_url, src)
            
            # Skip already processed
            if src in self._image_map:
                images.append({
                    'url': src,
                    'local_path': self._image_map[src],
                    'alt': img.get('alt', ''),
                })
                continue
            
            # Download image
            local_path = self._download_image(src)
            if local_path:
                self._image_map[src] = local_path
                images.append({
                    'url': src,
                    'local_path': local_path,
                    'alt': img.get('alt', ''),
                })
        
        content.images = images
        return images
    
    def _download_image(self, url: str) -> Optional[str]:
        """Download a single image and return local filename."""
        try:
            response = requests.get(
                url, 
                timeout=30,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            response.raise_for_status()
            
            # Determine file extension
            content_type = response.headers.get('Content-Type', '')
            ext = self._get_extension(url, content_type)
            
            # Generate filename from URL hash
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            filename = f"img_{url_hash}{ext}"
            
            # Save file
            filepath = self.config.images_dir / filename
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            return filename
            
        except Exception as e:
            print(f"    [FAIL] Failed to download image: {url[:50]}... ({e})")
            return None
    
    def _get_extension(self, url: str, content_type: str) -> str:
        """Determine image file extension."""
        # Try content type first
        type_map = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'image/svg+xml': '.svg',
        }
        
        for mime, ext in type_map.items():
            if mime in content_type:
                return ext
        
        # Try URL extension
        parsed = urlparse(url)
        path = parsed.path.lower()
        for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
            if path.endswith(ext):
                return ext
        
        return '.jpg'  # Default
    
    def update_image_paths(self, content: PostContent) -> str:
        """Update image paths in Markdown to use local files."""
        md = content.markdown_content
        
        for img in content.images:
            if img.get('local_path'):
                old_path = img['url']
                new_path = f"../images/{img['local_path']}"
                md = md.replace(old_path, new_path)
        
        content.markdown_content = md
        return md


def generate_filename(post: Post) -> str:
    """Generate a filename for a post."""
    # Start with date if available
    if post.date:
        prefix = post.date.strftime('%Y-%m-%d')
    else:
        prefix = 'undated'
    
    # Sanitize title for filename
    slug = post.slug or post.title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = slug.strip('-')[:50]  # Limit length
    
    return f"{prefix}-{slug}.md"
