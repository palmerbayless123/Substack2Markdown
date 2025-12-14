# Substack2Markdown

A Python tool to download Substack publications (including paid content if subscribed) and convert them to Markdown format with images.

## Features

- Download entire Substack publications or specific posts
- Converts posts to clean Markdown format
- Downloads and saves images locally
- Handles paid content (requires active subscription)
- Rate limiting to avoid being blocked
- Resume capability for interrupted downloads
- Configurable via environment variables or config file

## Prerequisites

- Python 3.8+
- Chrome browser (for Selenium automation)
- ChromeDriver (automatically managed by webdriver-manager)

## Installation

1. Clone or download this repository:
```bash
cd substack2markdown
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy the example config and edit with your details:
```bash
cp .env.example .env
# Edit .env with your Substack URL and credentials
```

## Configuration

Edit the `.env` file or set environment variables:

```env
# Required: The Substack publication URL
SUBSTACK_URL=https://example.substack.com

# Optional: Login credentials (if not using browser session)
SUBSTACK_EMAIL=your-email@example.com
SUBSTACK_PASSWORD=your-password

# Optional: Output directory (default: ./output)
OUTPUT_DIR=./output

# Optional: Delay between requests in seconds (default: 5)
REQUEST_DELAY=5

# Optional: Download images (default: true)
DOWNLOAD_IMAGES=true

# Optional: Use existing browser session (default: true)
USE_BROWSER_SESSION=true

# Optional: How long to wait (in seconds) for manual login when using a
# browser session (default: 120, minimum: 30)
MANUAL_LOGIN_WAIT=120

# Optional: Point to a copied/unlocked Chrome user data directory if you want
# to reuse an existing profile. Leave blank to use a fresh temporary profile.
CHROME_USER_DATA_DIR=/path/to/copied/chrome/profile
CHROME_PROFILE=Default
```

## Usage

### Download entire publication:
```bash
python main.py
```

### Download specific post:
```bash
python main.py --url "https://example.substack.com/p/post-slug"
```

### Download with custom output directory:
```bash
python main.py --output ./my-backup
```

### Download without images:
```bash
python main.py --no-images
```

### List all available posts:
```bash
python main.py --list-only
```

### Resume interrupted download:
```bash
python main.py --resume
```

## Output Structure

```
output/
├── publication-name/
│   ├── posts/
│   │   ├── 2024-01-15-post-title.md
│   │   ├── 2024-01-10-another-post.md
│   │   └── ...
│   ├── images/
│   │   ├── img_abc123.jpg
│   │   ├── img_def456.png
│   │   └── ...
│   └── metadata.json
```

## Troubleshooting

### "Too Many Requests" Error
Increase the request delay in your `.env` file:
```env
REQUEST_DELAY=15
```

### CAPTCHA or 2FA Required
The script will pause and open a browser window for manual login. Complete the login process, then the script will continue.

### Images Not Downloading
Check your internet connection and ensure the `DOWNLOAD_IMAGES` setting is `true`.

### Chrome/ChromeDriver Issues
The script uses `webdriver-manager` to automatically download the correct ChromeDriver version. If you have issues:
```bash
pip install --upgrade webdriver-manager
```

## Legal Notice

This tool is intended for personal backup of content you have legitimate access to. Please respect copyright and Substack's terms of service. Only download content from publications you subscribe to.

## License

MIT License - See LICENSE file for details.
