#!/usr/bin/env python3
"""
Substack2Markdown - Download Substack publications to Markdown

Usage:
    python main.py                      # Download all posts
    python main.py --url <post-url>     # Download specific post
    python main.py --list-only          # List available posts
    python main.py --resume             # Resume interrupted download
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from tqdm import tqdm
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from config import config, Config
from browser import SubstackBrowser
from scraper import SubstackScraper, Post, PostContent
from converter import MarkdownConverter, generate_filename


console = Console()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Download Substack publications to Markdown format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py                          Download entire publication
    python main.py --url https://x.substack.com/p/post-slug  Download single post
    python main.py --list-only              Show available posts
    python main.py --output ./backup        Custom output directory
    python main.py --no-images              Skip image downloads
    python main.py --resume                 Resume interrupted download
        """
    )
    
    parser.add_argument(
        '--url',
        help='Download a specific post URL instead of entire publication'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output directory (overrides config)'
    )
    parser.add_argument(
        '--list-only', '-l',
        action='store_true',
        help='List available posts without downloading'
    )
    parser.add_argument(
        '--no-images',
        action='store_true',
        help='Skip downloading images'
    )
    parser.add_argument(
        '--resume', '-r',
        action='store_true',
        help='Resume interrupted download (skip already downloaded posts)'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode'
    )
    parser.add_argument(
        '--delay',
        type=int,
        help='Delay between requests in seconds (overrides config)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of posts to download'
    )
    
    return parser.parse_args()


def apply_args_to_config(args: argparse.Namespace):
    """Apply command line arguments to config."""
    if args.output:
        config.output_dir = Path(args.output)
    
    if args.no_images:
        config.download_images = False
    
    if args.headless:
        config.headless = True
    
    if args.delay:
        config.request_delay = args.delay


def get_downloaded_posts(config: Config) -> set:
    """Get set of already downloaded post slugs."""
    downloaded = set()
    
    if not config.posts_dir.exists():
        return downloaded
    
    for md_file in config.posts_dir.glob('*.md'):
        # Extract slug from filename (format: date-slug.md)
        name = md_file.stem
        parts = name.split('-', 3)
        if len(parts) >= 4:
            slug = parts[3]  # date parts + slug
            downloaded.add(slug)
        else:
            downloaded.add(name)
    
    return downloaded


def display_posts_table(posts: List[Post]):
    """Display posts in a formatted table."""
    table = Table(title="Available Posts", show_lines=True)
    
    table.add_column("#", style="dim", width=4)
    table.add_column("Date", style="cyan", width=12)
    table.add_column("Title", style="white", max_width=50)
    table.add_column("Paid", style="yellow", width=6)
    table.add_column("URL", style="dim", max_width=40)
    
    for i, post in enumerate(posts, 1):
        date_str = post.date.strftime('%Y-%m-%d') if post.date else 'Unknown'
        paid_str = '✓' if post.is_paid else ''
        
        table.add_row(
            str(i),
            date_str,
            post.title[:50],
            paid_str,
            post.slug
        )
    
    console.print(table)


def save_metadata(config: Config, posts: List[Post]):
    """Save publication metadata to JSON."""
    metadata = {
        'publication': config.publication_name,
        'url': config.substack_url,
        'downloaded_at': datetime.now().isoformat(),
        'total_posts': len(posts),
        'posts': [post.to_dict() for post in posts]
    }
    
    metadata_path = config.publication_output_dir / 'metadata.json'
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    console.print(f"✓ Saved metadata to {metadata_path}")


def download_single_post(
    url: str,
    scraper: SubstackScraper,
    converter: MarkdownConverter,
    config: Config
) -> bool:
    """Download a single post by URL."""
    console.print(f"\n[bold]Downloading single post:[/bold] {url}")
    
    # Create a Post object from the URL
    import re
    slug_match = re.search(r'/p/([^/?]+)', url)
    slug = slug_match.group(1) if slug_match else 'unknown'
    
    post = Post(
        url=url,
        title=slug.replace('-', ' ').title(),
        slug=slug,
    )
    
    # Fetch content
    content = scraper.get_post_content(post)
    if not content:
        console.print("[red]✗ Failed to fetch post content[/red]")
        return False
    
    # Convert to Markdown
    converter.convert(content)
    
    # Download images
    if config.download_images:
        converter.download_images(content)
        converter.update_image_paths(content)
    
    # Save to file
    filename = generate_filename(content.post)
    filepath = config.posts_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content.markdown_content)
    
    console.print(f"[green]✓ Saved:[/green] {filepath}")
    
    # Save HTML if configured
    if config.save_html:
        html_path = filepath.with_suffix('.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(content.html_content)
        console.print(f"[green]✓ Saved HTML:[/green] {html_path}")
    
    return True


def download_all_posts(
    posts: List[Post],
    scraper: SubstackScraper,
    converter: MarkdownConverter,
    config: Config,
    resume: bool = False,
    limit: Optional[int] = None
) -> tuple:
    """Download all posts from the publication."""
    downloaded = 0
    failed = 0
    skipped = 0
    
    # Get already downloaded posts if resuming
    existing = get_downloaded_posts(config) if resume else set()
    if existing:
        console.print(f"[dim]Found {len(existing)} already downloaded posts[/dim]")
    
    # Apply limit
    if limit:
        posts = posts[:limit]
    
    # Progress bar
    with tqdm(total=len(posts), desc="Downloading posts", unit="post") as pbar:
        for post in posts:
            pbar.set_postfix_str(post.title[:30])
            
            # Skip if already downloaded (resume mode)
            if resume and post.slug in existing:
                skipped += 1
                pbar.update(1)
                continue
            
            try:
                # Fetch content
                content = scraper.get_post_content(post)
                if not content:
                    failed += 1
                    pbar.update(1)
                    continue
                
                # Convert to Markdown
                converter.convert(content)
                
                # Download images
                if config.download_images:
                    converter.download_images(content, progress=False)
                    converter.update_image_paths(content)
                
                # Save to file
                filename = generate_filename(content.post)
                filepath = config.posts_dir / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content.markdown_content)
                
                # Save HTML if configured
                if config.save_html:
                    html_path = filepath.with_suffix('.html')
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(content.html_content)
                
                downloaded += 1
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Download interrupted by user[/yellow]")
                break
            except Exception as e:
                console.print(f"\n[red]Error processing {post.title}:[/red] {e}")
                failed += 1
            
            pbar.update(1)
    
    return downloaded, failed, skipped


def main():
    """Main entry point."""
    args = parse_args()
    apply_args_to_config(args)
    
    # Display header
    console.print(Panel.fit(
        "[bold cyan]Substack2Markdown[/bold cyan]\n"
        "Download Substack publications to Markdown",
        border_style="cyan"
    ))
    
    # Validate config
    if not config.validate():
        console.print("[red]Configuration error. Please check your .env file.[/red]")
        sys.exit(1)
    
    console.print(f"\n[bold]Publication:[/bold] {config.substack_url}")
    console.print(f"[bold]Output:[/bold] {config.publication_output_dir}")
    
    # Ensure output directories exist
    config.ensure_directories()
    
    # Initialize browser
    browser = SubstackBrowser(config)
    if not browser.setup():
        console.print("[red]Failed to initialize browser[/red]")
        sys.exit(1)
    
    try:
        # Login
        if not browser.login():
            console.print("[red]Login failed. Please check your credentials or browser session.[/red]")
            sys.exit(1)
        
        # Initialize scraper and converter
        scraper = SubstackScraper(config, browser)
        converter = MarkdownConverter(config)
        
        # Single post mode
        if args.url:
            success = download_single_post(args.url, scraper, converter, config)
            sys.exit(0 if success else 1)
        
        # Get post list
        posts = scraper.get_all_posts()
        
        if not posts:
            console.print("[yellow]No posts found[/yellow]")
            sys.exit(0)
        
        # List only mode
        if args.list_only:
            display_posts_table(posts)
            console.print(f"\n[bold]Total posts:[/bold] {len(posts)}")
            sys.exit(0)
        
        # Download all posts
        console.print(f"\n[bold]Starting download of {len(posts)} posts...[/bold]\n")
        
        downloaded, failed, skipped = download_all_posts(
            posts, 
            scraper, 
            converter, 
            config,
            resume=args.resume,
            limit=args.limit
        )
        
        # Save metadata
        save_metadata(config, posts)
        
        # Summary
        console.print("\n" + "="*50)
        console.print(Panel.fit(
            f"[bold green]Download Complete[/bold green]\n\n"
            f"Downloaded: {downloaded}\n"
            f"Skipped: {skipped}\n"
            f"Failed: {failed}\n"
            f"Total: {len(posts)}",
            border_style="green" if failed == 0 else "yellow"
        ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise
    finally:
        browser.close()


if __name__ == '__main__':
    main()
