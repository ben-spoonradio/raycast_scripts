#!/usr/bin/env python3
"""
Confluence Documents Downloader
Downloads all Korean documents from Confluence Space SM using local API key
Filters out Japanese documents automatically
Supports incremental updates (--update flag)
"""

import os
import json
import re
import time
import sys
import requests
import yaml
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote
from datetime import datetime
import base64
from pathlib import Path

# Default configuration file path
DEFAULT_CONFIG_PATH = "confluence_config.yaml"

def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> Dict:
    """Load configuration from YAML file"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# Load configuration
config = load_config()

# Extract configuration values
CONFLUENCE_BASE_URL = config['confluence']['base_url']
SPACE_KEY = config['confluence']['space_key']
CONFLUENCE_EMAIL = config['confluence']['email']
CONFLUENCE_API_TOKEN = os.getenv('CONFLUENCE_KEY')  # Set this environment variable

# Output configuration
OUTPUT_BASE_DIR = config['output']['base_dir']
USE_HIERARCHY = config['output']['use_hierarchy']
MAX_HIERARCHY_DEPTH = config['output']['max_depth']

# Download configuration
BATCH_SIZE = config['download']['batch_size']
RATE_LIMIT = config['download']['rate_limit']
MAX_RETRIES = config['download']['max_retries']
REQUEST_TIMEOUT = config['download']['timeout']

# Filtering configuration
SKIP_JAPANESE = config['filtering']['skip_japanese']
SKIP_PATTERNS = config['filtering']['skip_patterns']
INCLUDE_PATTERNS = config['filtering']['include_patterns']

# Test mode configuration
TEST_MODE_ENABLED = config['download']['test_mode']['enabled']
TEST_PAGE_IDS = config['download']['test_mode']['page_ids']
TEST_MAX_PAGES = config['download']['test_mode']['max_pages']

# Legacy folder mapping - kept as fallback for specific page categorization
# Update with your own Confluence page IDs and folder names
LEGACY_FOLDER_MAPPING = {
    # "page_id": "Folder_Name",
    # Example:
    # "1234567890": "Feature_Policy",
    # "1234567891": "Weekly_Reviews",
}

class ConfluenceDownloader:
    MANIFEST_FILENAME = ".confluence_manifest.json"

    def __init__(self, update_mode: bool = False):
        if not CONFLUENCE_API_TOKEN:
            raise ValueError("CONFLUENCE_KEY environment variable is required")

        # Setup authentication
        auth_string = f"{CONFLUENCE_EMAIL}:{CONFLUENCE_API_TOKEN}"
        self.auth_header = base64.b64encode(auth_string.encode()).decode()

        self.headers = {
            "Authorization": f"Basic {self.auth_header}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # Statistics
        self.downloaded_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.unchanged_count = 0

        # Current page context for relative path calculation
        self.current_page_folder = None

        # Incremental update mode
        self.update_mode = update_mode
        self.manifest = self._load_manifest() if update_mode else {}

    def _get_manifest_path(self) -> str:
        """Get absolute path for the manifest file"""
        if os.path.isabs(OUTPUT_BASE_DIR):
            return os.path.join(OUTPUT_BASE_DIR, self.MANIFEST_FILENAME)
        return os.path.join(os.getcwd(), OUTPUT_BASE_DIR, self.MANIFEST_FILENAME)

    def _load_manifest(self) -> Dict:
        """Load the manifest of previously downloaded pages.
        If no manifest exists, build one from existing .md files."""
        manifest_path = self._get_manifest_path()
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"📋 Loaded manifest: {len(data)} pages tracked")
                return data
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️  Failed to load manifest ({e}), rebuilding from local files...")

        # No manifest found - try to build from existing downloaded .md files
        return self._build_manifest_from_files()

    def _build_manifest_from_files(self) -> Dict:
        """Scan existing .md files and build a manifest from their metadata headers.
        Each file contains '문서 ID' and '최종 업데이트' in the front matter."""
        base_dir = OUTPUT_BASE_DIR if os.path.isabs(OUTPUT_BASE_DIR) else os.path.join(os.getcwd(), OUTPUT_BASE_DIR)

        if not os.path.exists(base_dir):
            print("📋 No manifest and no existing files found, will download all pages")
            return {}

        print("📋 No manifest found, scanning existing .md files to build manifest...")

        manifest = {}
        md_files = list(Path(base_dir).rglob("*.md"))

        for md_path in md_files:
            try:
                # Read only the first 10 lines (metadata header)
                with open(md_path, 'r', encoding='utf-8') as f:
                    header_lines = [f.readline() for _ in range(10)]

                page_id = None
                updated_date = None
                title = None

                for line in header_lines:
                    line = line.strip()
                    if line.startswith('# ') and title is None:
                        title = line[2:].strip()
                    elif line.startswith('**문서 ID:**'):
                        page_id = line.replace('**문서 ID:**', '').strip()
                    elif line.startswith('**최종 업데이트:**'):
                        updated_date = line.replace('**최종 업데이트:**', '').strip()

                if page_id and updated_date and updated_date != 'Unknown':
                    manifest[page_id] = {
                        'version': 0,  # Unknown - will fetch from API on first check
                        'updated_date': updated_date,
                        'file_path': str(md_path),
                        'title': title or 'Unknown',
                        'downloaded_at': datetime.fromtimestamp(md_path.stat().st_mtime).isoformat(),
                    }
            except (IOError, UnicodeDecodeError):
                continue

        if manifest:
            print(f"📋 Built manifest from {len(manifest)} existing files")
            # Save it immediately so next run is faster
            manifest_path = self._get_manifest_path()
            os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            print(f"📋 Saved initial manifest to {manifest_path}")
        else:
            print("📋 No existing files with metadata found, will download all pages")

        return manifest

    def _save_manifest(self):
        """Save the manifest of downloaded pages"""
        manifest_path = self._get_manifest_path()
        os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
        try:
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(self.manifest, f, ensure_ascii=False, indent=2)
            print(f"📋 Manifest saved: {len(self.manifest)} pages tracked")
        except IOError as e:
            print(f"⚠️  Failed to save manifest: {e}")

    def _is_page_updated(self, page_id: str, remote_version: int, remote_updated: str) -> bool:
        """Check if a page needs to be re-downloaded based on version or updated date"""
        if page_id not in self.manifest:
            return True  # New page

        local_info = self.manifest[page_id]
        local_version = local_info.get('version', 0)

        # If we have a real version number, compare directly
        if local_version > 0:
            return remote_version > local_version

        # Fallback: manifest was built from files (version=0), compare updated dates
        local_updated = local_info.get('updated_date', '')
        if local_updated and remote_updated:
            try:
                # Normalize remote_updated (ISO format from API) to comparable format
                if 'T' in str(remote_updated):
                    remote_dt = datetime.fromisoformat(str(remote_updated).replace('Z', '+00:00'))
                    remote_str = remote_dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    remote_str = str(remote_updated)
                return remote_str != local_updated
            except (ValueError, TypeError):
                pass

        # If we can't compare, re-download to be safe
        return True

    def _update_manifest_entry(self, page_id: str, version: int, updated_date: str, file_path: str, title: str):
        """Update manifest with page download info"""
        self.manifest[page_id] = {
            'version': version,
            'updated_date': updated_date,
            'file_path': file_path,
            'title': title,
            'downloaded_at': datetime.now().isoformat(),
        }

    def is_japanese_document(self, title: str, content: str = "") -> bool:
        """Determine if a document is primarily Japanese content"""
        if not SKIP_JAPANESE:
            return False

        # Check custom skip patterns
        for pattern in SKIP_PATTERNS:
            if pattern in title:
                return True

        return False

    def should_include_document(self, title: str) -> bool:
        """Check if document should be included based on include patterns"""
        if not INCLUDE_PATTERNS:
            return True

        for pattern in INCLUDE_PATTERNS:
            if pattern in title:
                return True

        return False

    def sanitize_filename(self, filename: str) -> str:
        """Convert title to safe filename"""
        # Replace problematic characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)
        filename = filename.strip('_')

        # Limit length
        if len(filename) > 100:
            filename = filename[:100]

        return filename

    def build_hierarchy_path(self, page_data: Dict) -> str:
        """Build folder path from page hierarchy using ancestors"""
        if not USE_HIERARCHY:
            return OUTPUT_BASE_DIR

        # Get space information - use space name instead of key
        space = page_data.get('space', {})
        space_name = space.get('name', space.get('key', SPACE_KEY))
        space_folder = self.sanitize_filename(space_name)

        ancestors = page_data.get('ancestors', [])

        # Start with base dir and space name
        path_parts = [OUTPUT_BASE_DIR, space_folder]

        # Add ancestor hierarchy
        for ancestor in ancestors:
            title = ancestor.get('title', 'Unknown')
            # Skip very generic titles but keep meaningful ones
            if title.lower() in ['home', 'homepage', 'space home']:
                continue
            folder_name = self.sanitize_filename(title)
            if folder_name and len(folder_name) > 0:
                path_parts.append(folder_name)

        # Limit depth to avoid overly nested structures
        if MAX_HIERARCHY_DEPTH > 0 and len(path_parts) > MAX_HIERARCHY_DEPTH + 1:
            path_parts = path_parts[:MAX_HIERARCHY_DEPTH + 1]

        return os.path.join(*path_parts)

    def get_folder_path(self, parent_id: str) -> str:
        """Get folder path based on parent ID (fallback method)"""
        return LEGACY_FOLDER_MAPPING.get(parent_id, "Root_Documents")

    def get_all_pages_content_api(self) -> List[Dict]:
        """Get all pages using content API (alternative method)"""
        all_pages = []
        start = 0
        limit = BATCH_SIZE

        print("Getting all pages using Content API...")

        max_iterations = 100  # Increased safety limit
        iteration = 0

        while iteration < max_iterations:
            url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content"
            params = {
                'spaceKey': SPACE_KEY,
                'type': 'page',
                'start': start,
                'limit': limit,
                'expand': 'space,version,ancestors'
            }

            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                pages = data.get('results', [])
                size = data.get('size', 0)

                if not pages or size == 0:
                    print(f"No more pages found at start={start}")
                    break

                print(f"Retrieved {len(pages)} pages (batch {iteration + 1}, total so far: {len(all_pages) + len(pages)})")
                all_pages.extend(pages)

                # Check if we got fewer pages than the limit (last page)
                if len(pages) < limit:
                    print(f"Retrieved final batch - total pages: {len(all_pages)}")
                    break

                start += limit
                iteration += 1

                # Rate limiting - slightly faster since we're using the direct API
                time.sleep(0.3)

            except requests.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    print(f"Rate limited - waiting 10 seconds...")
                    time.sleep(10)
                    continue  # Retry same request
                else:
                    print(f"HTTP error {e.response.status_code}: {e}")
                    break

            except requests.RequestException as e:
                print(f"Error getting pages via Content API: {e}")
                break

        print(f"Content API: Total pages found: {len(all_pages)}")
        return all_pages

    def search_all_pages(self) -> List[Dict]:
        """Search for all pages in the space with improved pagination"""
        all_pages = []
        start = 0
        limit = BATCH_SIZE

        print("Searching for all pages in Confluence space using Search API...")

        max_iterations = 100  # Increased safety limit
        iteration = 0

        while iteration < max_iterations:
            url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/search"
            params = {
                'cql': f'space = "{SPACE_KEY}" AND type = page',
                'start': start,
                'limit': limit,
                'expand': 'content.space,content.version,content.ancestors'
            }

            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                pages = data.get('results', [])
                total_size = data.get('totalSize', 0)

                if not pages:
                    print(f"No more pages found at start={start}")
                    break

                print(f"Found {len(pages)} pages (batch {iteration + 1}, total so far: {len(all_pages) + len(pages)}) - API reports {total_size} total")
                all_pages.extend(pages)

                # Check if we got all pages
                if len(all_pages) >= total_size or len(pages) < limit:
                    print(f"Retrieved all available pages: {len(all_pages)}")
                    break

                start += limit
                iteration += 1

                # Rate limiting
                time.sleep(0.5)

            except requests.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    print(f"Rate limited - waiting 10 seconds...")
                    time.sleep(10)
                    continue  # Retry same request
                else:
                    print(f"HTTP error {e.response.status_code}: {e}")
                    start += limit
                    iteration += 1
                    time.sleep(2)

            except requests.RequestException as e:
                print(f"Error searching pages: {e}")
                # Try continuing with next batch in case of temporary error
                start += limit
                iteration += 1
                time.sleep(2)  # Longer wait on error

        if iteration >= max_iterations:
            print("Warning: Reached maximum iteration limit. There might be more pages.")

        print(f"Search API: Total pages found: {len(all_pages)}")
        return all_pages

    def get_all_pages_combined(self) -> List[Dict]:
        """Combine both methods to ensure we get all pages"""
        print("Using combined approach to get all pages...")

        # Try Content API first
        content_pages = self.get_all_pages_content_api()

        # Try Search API as well
        search_pages = self.search_all_pages()

        # Combine and deduplicate
        seen_ids = set()
        all_pages = []

        # Add from content API
        for page in content_pages:
            page_id = page.get('id')
            if page_id and page_id not in seen_ids:
                seen_ids.add(page_id)
                all_pages.append(page)

        # Add from search API (if not already present)
        for page in search_pages:
            # Search API wraps pages in 'content' field
            page_data = page.get('content', page)
            page_id = page_data.get('id')
            if page_id and page_id not in seen_ids:
                seen_ids.add(page_id)
                # Normalize structure to match content API
                all_pages.append(page_data)

        print(f"Combined result: {len(all_pages)} unique pages")
        print(f"- Content API found: {len(content_pages)}")
        print(f"- Search API found: {len(search_pages)}")

        return all_pages

    def get_page_content(self, page_id: str) -> Optional[Dict]:
        """Get full page content including body with retry logic"""
        url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content/{page_id}"
        params = {
            'expand': 'body.atlas_doc_format,version,space,ancestors,history'
        }

        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                return response.json()

            except requests.Timeout:
                print(f"Timeout getting page content for {page_id} (attempt {attempt + 1}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff

            except requests.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    print(f"Rate limited for page {page_id} (attempt {attempt + 1}/{MAX_RETRIES})")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(5 * (attempt + 1))  # Longer wait for rate limits
                elif e.response.status_code == 404:
                    print(f"Page {page_id} not found (404)")
                    return None
                else:
                    print(f"HTTP error {e.response.status_code} getting page content for {page_id}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(2 ** attempt)

            except requests.RequestException as e:
                print(f"Error getting page content for {page_id} (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)

        print(f"Failed to get page content for {page_id} after {MAX_RETRIES} attempts")
        return None

    def get_page_comments(self, page_id: str) -> List[Dict]:
        """Get all comments (inline and footer) for a page"""
        comments = []

        # Get footer comments (page-level comments)
        footer_url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content/{page_id}/child/comment"
        params = {
            'expand': 'body.atlas_doc_format,version,history.lastUpdated,extensions.inlineProperties',
            'limit': 100
        }

        try:
            response = self.session.get(footer_url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            for comment in data.get('results', []):
                # Check if it's an inline comment
                extensions = comment.get('extensions', {})
                inline_props = extensions.get('inlineProperties', {})

                # Determine comment type and location
                comment_type = 'footer'
                location_info = ''

                if inline_props:
                    comment_type = 'inline'
                    # Extract inline comment location information
                    marker_ref = inline_props.get('markerRef', '')
                    original_selection = inline_props.get('originalSelection', '')

                    if original_selection:
                        location_info = f" (위치: \"{original_selection[:50]}...\")" if len(original_selection) > 50 else f" (위치: \"{original_selection}\")"

                comment_data = {
                    'type': comment_type,
                    'id': comment.get('id'),
                    'author': comment.get('history', {}).get('createdBy', {}).get('displayName', 'Unknown'),
                    'created': comment.get('history', {}).get('createdDate', ''),
                    'updated': comment.get('version', {}).get('when', ''),
                    'body': comment.get('body', {}).get('atlas_doc_format', {}).get('value', ''),
                    'location_info': location_info,
                }
                comments.append(comment_data)

        except requests.RequestException as e:
            print(f"Error getting comments for page {page_id}: {e}")

        return comments

    def _fetch_page_title(self, url: str) -> Optional[str]:
        """Fetch the page title from a URL"""
        try:
            # Set a reasonable timeout
            response = self.session.get(url, timeout=10, allow_redirects=True)
            response.raise_for_status()

            # Parse HTML to extract title
            from html.parser import HTMLParser

            class TitleParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.title = None
                    self.in_title = False

                def handle_starttag(self, tag, attrs):
                    if tag == 'title':
                        self.in_title = True

                def handle_data(self, data):
                    if self.in_title and data.strip():
                        self.title = data.strip()

                def handle_endtag(self, tag):
                    if tag == 'title':
                        self.in_title = False

            parser = TitleParser()
            parser.feed(response.text)

            if parser.title:
                # Clean up the title (remove common suffixes)
                title = parser.title
                # Remove common website suffixes
                for suffix in [' - YouTube', ' | Facebook', ' - Twitter', ' | LinkedIn']:
                    if title.endswith(suffix):
                        title = title[:-len(suffix)].strip()

                return title

            return None

        except Exception as e:
            print(f"Could not fetch page title from {url}: {e}")
            return None

    def _download_media(self, media_id: str, collection: str, alt_text: str) -> Optional[str]:
        """Download media file and return relative path for markdown"""
        try:
            # Extract content ID from collection (e.g., "contentId-4328194130" -> "4328194130")
            content_id = collection.replace('contentId-', '')

            # Create images directory
            images_dir = os.path.join(OUTPUT_BASE_DIR, 'images', content_id)
            os.makedirs(images_dir, exist_ok=True)

            # The media_id in Atlas format is not directly usable - we need to:
            # 1. Get all attachments for the page
            # 2. Find the attachment by matching the filename from alt_text
            # 3. Use the attachment's download URL

            # First, try to get attachment list for this page
            attachments_url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content/{content_id}/child/attachment"
            params = {'limit': 100}

            attachments_response = self.session.get(attachments_url, params=params)
            attachments_response.raise_for_status()
            attachments_data = attachments_response.json()

            # Find matching attachment by filename (from alt_text)
            target_attachment = None
            if alt_text:
                for attachment in attachments_data.get('results', []):
                    if attachment.get('title', '') == alt_text:
                        target_attachment = attachment
                        break

            # If we didn't find by alt_text, try the media_id (unlikely to work but worth a try)
            if not target_attachment:
                for attachment in attachments_data.get('results', []):
                    if attachment.get('id', '') == media_id:
                        target_attachment = attachment
                        break

            if not target_attachment:
                print(f"Could not find attachment for media {media_id} (alt: {alt_text})")
                return None

            # Get the download URL from the attachment
            download_link = target_attachment.get('_links', {}).get('download', '')
            if not download_link:
                print(f"No download link for attachment {target_attachment.get('title', '')}")
                return None

            # Construct full download URL with /wiki prefix
            # The API returns relative URLs like "/download/attachments/..."
            # We need to add the wiki context path
            download_url = f"{CONFLUENCE_BASE_URL}/wiki{download_link}"

            # Get filename from attachment title
            filename = target_attachment.get('title', f'image-{media_id}')
            file_path = os.path.join(images_dir, filename)

            # Download the image
            print(f"Downloading image: {filename}...")
            img_response = self.session.get(download_url, stream=True)
            img_response.raise_for_status()

            # Save the image
            with open(file_path, 'wb') as f:
                for chunk in img_response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"Saved image: {filename}")

            # Calculate relative path from markdown file to image
            # Current page folder: e.g., "docs/confluence_docs/Spoon_Series/Spoon_Series/Product_&_Design"
            # Image folder: "docs/confluence_docs/images/4328194130"
            # Need to go up to "docs/confluence_docs" then down to "images"

            if self.current_page_folder:
                # Count directory levels from OUTPUT_BASE_DIR
                page_folder_parts = self.current_page_folder.split(os.sep)
                base_parts = OUTPUT_BASE_DIR.split(os.sep)

                # Find relative depth (how many levels to go up)
                depth = len(page_folder_parts) - len(base_parts)

                # Build relative path with correct number of "../"
                # URL encode the filename to handle Korean characters properly
                up_levels = '../' * depth
                encoded_filename = quote(filename)
                relative_path = f"{up_levels}images/{content_id}/{encoded_filename}"
            else:
                # Fallback to default with URL encoded filename
                encoded_filename = quote(filename)
                relative_path = f"../../images/{content_id}/{encoded_filename}"

            return relative_path

        except Exception as e:
            print(f"Error downloading media {media_id}: {e}")
            return None

    def atlas_doc_to_markdown(self, atlas_content: Dict) -> str:
        """Convert Atlas Document Format to Markdown"""
        # Parse JSON string if needed
        if isinstance(atlas_content, str):
            try:
                atlas_content = json.loads(atlas_content)
            except json.JSONDecodeError:
                return "Error: Invalid Atlas JSON format"
        
        if atlas_content.get('type') == 'doc':
            content = atlas_content.get('content', [])
            
            # First pass: collect all headings for TOC
            headings = []
            for node in content:
                if node.get('type') == 'heading':
                    level = node.get('attrs', {}).get('level', 1)
                    text = self._extract_text_from_node(node)
                    if text.strip():
                        headings.append({'level': level, 'text': text.strip()})
            
            # Second pass: convert content with TOC injection
            atlas_content = self._convert_content_to_markdown_with_toc(content, headings)
            return atlas_content
        return ""

    def _convert_content_to_markdown_with_toc(self, content: List[Dict], headings: List[Dict]) -> str:
        """Recursively convert content nodes to markdown, injecting TOC where needed
        
        Args:
            content: List of content nodes from Atlas document
            headings: List of collected headings with {'level': int, 'text': str}
        """
        markdown = []
        last_was_label = False  # Track if last paragraph was a short label

        for i, node in enumerate(content):
            node_type = node.get('type')

            if node_type == 'paragraph':
                text = self._extract_text_from_node(node)
                if text.strip():
                    markdown.append(text)
                    last_was_label = False
                else:
                    last_was_label = False

            elif node_type == 'heading':
                level = node.get('attrs', {}).get('level', 1)
                text = self._extract_text_from_node(node)
                if text.strip():
                    markdown.append('#' * level + ' ' + text)
                last_was_label = False

            elif node_type == 'bulletList':
                list_items = []
                for item in node.get('content', []):
                    if item.get('type') == 'listItem':
                        item_content = item.get('content', [])
                        item_lines = []

                        # Process each content node in the listItem
                        for content_node in item_content:
                            content_type = content_node.get('type')

                            if content_type == 'paragraph':
                                # Extract the main paragraph text
                                text = self._extract_text_from_node(content_node)
                                if text.strip():
                                    if not item_lines:
                                        # First paragraph becomes the bullet item
                                        item_lines.append(f"• {text}")
                                    else:
                                        # Additional paragraphs are indented
                                        item_lines.append(f"  {text}")

                            elif content_type == 'bulletList':
                                # Handle nested bullet list with indentation
                                for bullet_item in content_node.get('content', []):
                                    if bullet_item.get('type') == 'listItem':
                                        bullet_text = self._extract_text_from_node(bullet_item)
                                        if bullet_text.strip():
                                            # Indent nested bullets with 2 spaces
                                            item_lines.append(f"  - {bullet_text}")

                        # Add all lines for this bullet list item
                        if item_lines:
                            list_items.extend(item_lines)

                if list_items:
                    markdown.extend(list_items)
                last_was_label = False

            elif node_type == 'orderedList':
                list_items = []
                for idx, item in enumerate(node.get('content', []), 1):
                    if item.get('type') == 'listItem':
                        item_content = item.get('content', [])
                        item_lines = []

                        # Process each content node in the listItem
                        for content_node in item_content:
                            content_type = content_node.get('type')

                            if content_type == 'paragraph':
                                # Extract the main paragraph text (usually the title)
                                text = self._extract_text_from_node(content_node)
                                if text.strip():
                                    if not item_lines:
                                        # First paragraph becomes the numbered item
                                        item_lines.append(f"{idx}. {text}")
                                    else:
                                        # Additional paragraphs are indented
                                        item_lines.append(f"   {text}")

                            elif content_type == 'bulletList':
                                # Handle nested bullet list with indentation
                                for bullet_item in content_node.get('content', []):
                                    if bullet_item.get('type') == 'listItem':
                                        bullet_text = self._extract_text_from_node(bullet_item)
                                        if bullet_text.strip():
                                            # Indent nested bullets with 3 spaces
                                            item_lines.append(f"   - {bullet_text}")

                        # Add all lines for this ordered list item
                        if item_lines:
                            list_items.extend(item_lines)

                if list_items:
                    markdown.extend(list_items)
                last_was_label = False

            elif node_type == 'table':
                table_md = self._convert_table_to_markdown(node)
                if table_md.strip():
                    markdown.append(table_md.strip())
                last_was_label = False

            elif node_type == 'codeBlock':
                language = node.get('attrs', {}).get('language', '')
                text = self._extract_text_from_node(node)
                if text.strip():
                    markdown.append(f"```{language}\n{text}\n```")
                last_was_label = False

            elif node_type == 'rule':
                # Horizontal rule
                markdown.append('---')
                last_was_label = False

            elif node_type == 'mediaSingle':
                # Handle images wrapped in mediaSingle
                text = self._extract_text_from_node(node)
                if text.strip():
                    markdown.append(text)
                last_was_label = False

            elif node_type == 'layoutSection':
                # Handle layout sections (columns)
                text = self._extract_text_from_node(node)
                if text.strip():
                    markdown.append(text)
                last_was_label = False

            elif node_type == 'expand':
                # Handle expand/collapse sections
                attrs = node.get('attrs', {})
                title = attrs.get('title', 'Details')

                # Add the expand title as a heading
                markdown.append(f"### {title}")

                # Process the content inside the expand section
                expand_content = node.get('content', [])
                for content_node in expand_content:
                    content_type = content_node.get('type')

                    if content_type == 'paragraph':
                        text = self._extract_text_from_node(content_node)
                        if text.strip():
                            markdown.append(text)

                    elif content_type == 'heading':
                        level = content_node.get('attrs', {}).get('level', 1)
                        text = self._extract_text_from_node(content_node)
                        if text.strip():
                            # Increase heading level by 1 to maintain hierarchy
                            markdown.append(f"{'#' * (level + 1)} {text}")

                    elif content_type == 'bulletList':
                        list_items = []
                        for item in content_node.get('content', []):
                            if item.get('type') == 'listItem':
                                item_content = item.get('content', [])
                                item_lines = []

                                for item_node in item_content:
                                    item_node_type = item_node.get('type')

                                    if item_node_type == 'paragraph':
                                        text = self._extract_text_from_node(item_node)
                                        if text.strip():
                                            if not item_lines:
                                                item_lines.append(f"• {text}")
                                            else:
                                                item_lines.append(f"  {text}")

                                    elif item_node_type == 'bulletList':
                                        for bullet_item in item_node.get('content', []):
                                            if bullet_item.get('type') == 'listItem':
                                                bullet_text = self._extract_text_from_node(bullet_item)
                                                if bullet_text.strip():
                                                    item_lines.append(f"  - {bullet_text}")

                                if item_lines:
                                    list_items.extend(item_lines)

                        if list_items:
                            markdown.extend(list_items)

                    elif content_type == 'orderedList':
                        list_items = []
                        for idx, item in enumerate(content_node.get('content', []), 1):
                            if item.get('type') == 'listItem':
                                text = self._extract_text_from_node(item)
                                if text.strip():
                                    list_items.append(f"{idx}. {text}")

                        if list_items:
                            markdown.extend(list_items)

                    elif content_type == 'rule':
                        markdown.append("---")

                    elif content_type == 'table':
                        table_md = self._convert_table_to_markdown(content_node)
                        if table_md:
                            markdown.append(table_md)

                    elif content_type == 'codeBlock':
                        language = content_node.get('attrs', {}).get('language', '')
                        code_text = self._extract_text_from_node(content_node)
                        if code_text.strip():
                            markdown.append(f"```{language}\n{code_text}\n```")

                    else:
                        # Handle other content types generically
                        text = self._extract_text_from_node(content_node)
                        if text.strip():
                            markdown.append(text)

                last_was_label = False

            elif node_type == 'extension':
                # Handle Confluence macros (TOC, etc.)
                extension_key = node.get('attrs', {}).get('extensionKey', '')
                
                if extension_key == 'toc' and headings:
                    # Generate actual TOC from collected headings with anchor links
                    # Confluence TOC typically shows only up to level 3
                    toc_lines = ["## 목차", ""]

                    for heading in headings:
                        level = heading['level']
                        text = heading['text']

                        # Only include headings up to level 3 in TOC
                        if level > 3:
                            continue

                        # Create anchor link from heading text
                        # Most markdown processors convert headings to lowercase and replace spaces with hyphens
                        # Remove markdown formatting (**, *, `, etc.) and special characters from anchor
                        clean_text = text.replace('**', '').replace('*', '').replace('`', '').replace('"', '').replace("'", '')
                        anchor = clean_text.lower().replace(' ', '-').replace('.', '').replace('/', '').replace('(', '').replace(')', '').replace('&', '').replace(':', '')

                        # Create indented list item with anchor link (no numbering prefix since heading text already has it)
                        indent = "   " * (level - 2)  # Level 2 has no indent, level 3 has one indent
                        toc_lines.append(f"{indent}- [{text}](#{anchor})")

                    markdown.append('\n'.join(toc_lines))
                else:
                    # Fallback to generic extension handling
                    text = self._extract_extension_content(node)
                    if text.strip():
                        markdown.append(text)
                        
                last_was_label = False

            elif node_type == 'embedCard':
                # Handle embedded content (YouTube videos, Figma, etc.)
                attrs = node.get('attrs', {})
                url = attrs.get('url', '')
                if url:
                    # Try to extract meaningful title from URL
                    try:
                        from urllib.parse import unquote
                        decoded_url = unquote(url)

                        # For Figma links, extract the design name
                        if 'figma.com' in url:
                            parts = decoded_url.split('/')
                            for i, part in enumerate(parts):
                                if part == 'design' and i + 2 < len(parts):
                                    title = parts[i + 2].split('?')[0]
                                    # Clean up the title (remove leading dash)
                                    if title.startswith('-'):
                                        title = title[1:]
                                    # Replace dashes with spaces for readability
                                    title = title.replace('-', ' ')
                                    markdown.append(f"**Figma:** [{title}]({url})")
                                    break
                            else:
                                # If pattern not found, use generic format
                                markdown.append(f"[{url}]({url})")
                        else:
                            # For other embedded content, use generic format
                            markdown.append(f"[{url}]({url})")
                    except Exception:
                        markdown.append(f"[{url}]({url})")
                last_was_label = False

        # Join with double newlines for proper paragraph separation
        return '\n\n'.join(filter(None, markdown))

    def _convert_content_to_markdown(self, content: List[Dict]) -> str:
        """Recursively convert content nodes to markdown"""
        markdown = []
        last_was_label = False  # Track if last paragraph was a short label

        for i, node in enumerate(content):
            node_type = node.get('type')

            if node_type == 'paragraph':
                text = self._extract_text_from_node(node)
                if text.strip():
                    markdown.append(text)
                    last_was_label = False
                else:
                    last_was_label = False

            elif node_type == 'heading':
                level = node.get('attrs', {}).get('level', 1)
                text = self._extract_text_from_node(node)
                if text.strip():
                    markdown.append('#' * level + ' ' + text)
                last_was_label = False

            elif node_type == 'bulletList':
                list_items = []
                for item in node.get('content', []):
                    if item.get('type') == 'listItem':
                        item_content = item.get('content', [])
                        item_lines = []

                        # Process each content node in the listItem
                        for content_node in item_content:
                            content_type = content_node.get('type')

                            if content_type == 'paragraph':
                                # Extract the main paragraph text
                                text = self._extract_text_from_node(content_node)
                                if text.strip():
                                    if not item_lines:
                                        # First paragraph becomes the bullet item
                                        item_lines.append(f"• {text}")
                                    else:
                                        # Additional paragraphs are indented
                                        item_lines.append(f"  {text}")

                            elif content_type == 'bulletList':
                                # Handle nested bullet list with indentation
                                for bullet_item in content_node.get('content', []):
                                    if bullet_item.get('type') == 'listItem':
                                        bullet_text = self._extract_text_from_node(bullet_item)
                                        if bullet_text.strip():
                                            # Indent nested bullets with 2 spaces
                                            item_lines.append(f"  - {bullet_text}")

                        # Add all lines for this bullet list item
                        if item_lines:
                            list_items.extend(item_lines)

                if list_items:
                    markdown.extend(list_items)
                last_was_label = False

            elif node_type == 'orderedList':
                list_items = []
                for idx, item in enumerate(node.get('content', []), 1):
                    if item.get('type') == 'listItem':
                        item_content = item.get('content', [])
                        item_lines = []

                        # Process each content node in the listItem
                        for content_node in item_content:
                            content_type = content_node.get('type')

                            if content_type == 'paragraph':
                                # Extract the main paragraph text (usually the title)
                                text = self._extract_text_from_node(content_node)
                                if text.strip():
                                    if not item_lines:
                                        # First paragraph becomes the numbered item
                                        item_lines.append(f"{idx}. {text}")
                                    else:
                                        # Additional paragraphs are indented
                                        item_lines.append(f"   {text}")

                            elif content_type == 'bulletList':
                                # Handle nested bullet list with indentation
                                for bullet_item in content_node.get('content', []):
                                    if bullet_item.get('type') == 'listItem':
                                        bullet_text = self._extract_text_from_node(bullet_item)
                                        if bullet_text.strip():
                                            # Indent nested bullets with 3 spaces
                                            item_lines.append(f"   - {bullet_text}")

                        # Add all lines for this ordered list item
                        if item_lines:
                            list_items.extend(item_lines)

                if list_items:
                    markdown.extend(list_items)
                last_was_label = False

            elif node_type == 'table':
                table_md = self._convert_table_to_markdown(node)
                if table_md.strip():
                    markdown.append(table_md.strip())
                last_was_label = False

            elif node_type == 'codeBlock':
                language = node.get('attrs', {}).get('language', '')
                text = self._extract_text_from_node(node)
                if text.strip():
                    markdown.append(f"```{language}\n{text}\n```")
                last_was_label = False

            elif node_type == 'rule':
                # Horizontal rule
                markdown.append('---')
                last_was_label = False

            elif node_type == 'mediaSingle':
                # Handle images wrapped in mediaSingle
                text = self._extract_text_from_node(node)
                if text.strip():
                    markdown.append(text)
                last_was_label = False

            elif node_type == 'layoutSection':
                # Handle layout sections (columns)
                text = self._extract_text_from_node(node)
                if text.strip():
                    markdown.append(text)
                last_was_label = False

            elif node_type == 'expand':
                # Handle expand/collapse sections
                attrs = node.get('attrs', {})
                title = attrs.get('title', 'Details')

                # Add the expand title as a heading
                markdown.append(f"### {title}")

                # Process the content inside the expand section
                expand_content = node.get('content', [])
                for content_node in expand_content:
                    content_type = content_node.get('type')

                    if content_type == 'paragraph':
                        text = self._extract_text_from_node(content_node)
                        if text.strip():
                            markdown.append(text)

                    elif content_type == 'heading':
                        level = content_node.get('attrs', {}).get('level', 1)
                        text = self._extract_text_from_node(content_node)
                        if text.strip():
                            # Increase heading level by 1 to maintain hierarchy
                            markdown.append(f"{'#' * (level + 1)} {text}")

                    elif content_type == 'bulletList':
                        list_items = []
                        for item in content_node.get('content', []):
                            if item.get('type') == 'listItem':
                                item_content = item.get('content', [])
                                item_lines = []

                                for item_node in item_content:
                                    item_node_type = item_node.get('type')

                                    if item_node_type == 'paragraph':
                                        text = self._extract_text_from_node(item_node)
                                        if text.strip():
                                            if not item_lines:
                                                item_lines.append(f"• {text}")
                                            else:
                                                item_lines.append(f"  {text}")

                                    elif item_node_type == 'bulletList':
                                        for bullet_item in item_node.get('content', []):
                                            if bullet_item.get('type') == 'listItem':
                                                bullet_text = self._extract_text_from_node(bullet_item)
                                                if bullet_text.strip():
                                                    item_lines.append(f"  - {bullet_text}")

                                if item_lines:
                                    list_items.extend(item_lines)

                        if list_items:
                            markdown.extend(list_items)

                    elif content_type == 'orderedList':
                        list_items = []
                        for idx, item in enumerate(content_node.get('content', []), 1):
                            if item.get('type') == 'listItem':
                                text = self._extract_text_from_node(item)
                                if text.strip():
                                    list_items.append(f"{idx}. {text}")

                        if list_items:
                            markdown.extend(list_items)

                    elif content_type == 'rule':
                        markdown.append("---")

                    elif content_type == 'table':
                        table_md = self._convert_table_to_markdown(content_node)
                        if table_md:
                            markdown.append(table_md)

                    elif content_type == 'codeBlock':
                        language = content_node.get('attrs', {}).get('language', '')
                        code_text = self._extract_text_from_node(content_node)
                        if code_text.strip():
                            markdown.append(f"```{language}\n{code_text}\n```")

                    else:
                        # Handle other content types generically
                        text = self._extract_text_from_node(content_node)
                        if text.strip():
                            markdown.append(text)

                last_was_label = False

            elif node_type == 'extension':
                # Handle Confluence macros (TOC, etc.)
                text = self._extract_extension_content(node)
                if text.strip():
                    markdown.append(text)
                last_was_label = False

            elif node_type == 'embedCard':
                # Handle embedded content (YouTube videos, Figma, etc.)
                attrs = node.get('attrs', {})
                url = attrs.get('url', '')
                if url:
                    # Try to extract meaningful title from URL
                    try:
                        from urllib.parse import unquote
                        decoded_url = unquote(url)

                        # For Figma links, extract the design name
                        if 'figma.com' in url:
                            parts = decoded_url.split('/')
                            for i, part in enumerate(parts):
                                if part == 'design' and i + 2 < len(parts):
                                    title = parts[i + 2].split('?')[0]
                                    # Clean up the title (remove leading dash)
                                    if title.startswith('-'):
                                        title = title[1:]
                                    # Replace dashes with spaces for readability
                                    title = title.replace('-', ' ')
                                    markdown.append(f"**Figma:** [{title}]({url})")
                                    break
                            else:
                                # If pattern not found, use generic format
                                markdown.append(f"[{url}]({url})")
                        else:
                            # For other embedded content, use generic format
                            markdown.append(f"[{url}]({url})")
                    except Exception:
                        markdown.append(f"[{url}]({url})")
                last_was_label = False

        # Join with double newlines for proper paragraph separation
        return '\n\n'.join(filter(None, markdown))

    def _extract_text_from_node(self, node: Dict, context: Dict = None) -> str:
        """Extract plain text from a node

        Args:
            node: The current node to process
            context: Optional context dict that can contain 'preceding_text' for inlineCard handling
        """
        if not node:
            return ""

        if context is None:
            context = {}

        node_type = node.get('type')

        # Handle extension nodes (macros)
        if node_type == 'extension':
            return self._extract_extension_content(node)

        # Handle text nodes
        if node_type == 'text':
            text = node.get('text', '')
            marks = node.get('marks', [])

            # Check for link mark first
            for mark in marks:
                mark_type = mark.get('type')
                if mark_type == 'link':
                    url = mark.get('attrs', {}).get('href', '')
                    return f"[{text}]({url})"

            # Apply other text formatting
            for mark in marks:
                mark_type = mark.get('type')
                if mark_type == 'strong':
                    # Strip whitespace and apply bold
                    text = f"**{text.strip()}**"
                elif mark_type == 'em':
                    text = f"*{text.strip()}*"
                elif mark_type == 'code':
                    text = f"`{text.strip()}`"

            return text

        # Handle status nodes (status lozenge)
        elif node_type == 'status':
            text = node.get('attrs', {}).get('text', '')
            return text

        # Handle inline card (Jira links, Confluence links, etc.)
        elif node_type == 'inlineCard':
            url = node.get('attrs', {}).get('url', '')
            if not url:
                return ''

            # Check if we have preceding text from context (for proper link formatting)
            preceding_text = context.get('preceding_text', '').strip()

            # If we have preceding text that's more than just "출처 :", use it as the link title
            if preceding_text and preceding_text not in ['출처 :', '출처:', '출처', 'Source:', 'Source']:
                return f"[{preceding_text}]({url})"

            # Try to fetch the actual page title from the URL
            page_title = self._fetch_page_title(url)
            if page_title:
                # If we have preceding text like "출처 :", include it
                if preceding_text:
                    return f"{preceding_text} [{page_title}]({url})"
                else:
                    return f"[{page_title}]({url})"

            # If preceding text exists (even if it's just "출처 :"), use it
            if preceding_text:
                return f"[{preceding_text}]({url})"

            # Otherwise, try to decode URL-encoded Korean text for better readability
            try:
                from urllib.parse import unquote
                decoded_url = unquote(url)

                # Extract meaningful title from URL
                # For Figma links, extract the design name
                if 'figma.com' in url:
                    # Extract design name from Figma URL
                    parts = decoded_url.split('/')
                    for i, part in enumerate(parts):
                        if part == 'design' and i + 2 < len(parts):
                            title = parts[i + 2].split('?')[0]
                            # Clean up the title
                            if title.startswith('-'):
                                title = title[1:]
                            return f"[{title}]({url})"

                # For Confluence links
                elif 'atlassian.net/wiki' in url:
                    # Try to extract page title from URL
                    if '/pages/' in decoded_url:
                        parts = decoded_url.split('/')
                        for i, part in enumerate(parts):
                            if part == 'pages' and i + 2 < len(parts):
                                title = parts[i + 2].split('?')[0]
                                return f"[{title}]({url})"

                # For Slack links
                elif 'slack.com' in url:
                    channel_id = url.split('/')[-1]
                    return f"[Slack Channel: {channel_id}]({url})"

                # Default: use last part of URL
                title = url.split('/')[-1].split('?')[0]
                if len(title) > 50:
                    title = title[:50] + '...'
                return f"[{title}]({url})"

            except Exception:
                # Fallback to simple link
                return f"[Link]({url})"

        # Handle mention nodes
        elif node_type == 'mention':
            text = node.get('attrs', {}).get('text', '@user')
            return text

        # Handle emoji nodes
        elif node_type == 'emoji':
            attrs = node.get('attrs', {})
            emoji_id = attrs.get('id', '')
            shortName = attrs.get('shortName', '')

            # Handle standard Unicode emojis
            if emoji_id and not emoji_id.startswith('atlassian-'):
                try:
                    # Try to convert hex emoji ID to actual emoji character
                    # e.g., "1f5d3" -> 📆 (calendar)
                    emoji_codepoint = int(emoji_id, 16)
                    emoji_char = chr(emoji_codepoint)
                    return emoji_char
                except Exception:
                    pass

            # Handle Atlassian custom emojis with CDN images
            if emoji_id and emoji_id.startswith('atlassian-'):
                # Extract emoji name from ID (e.g., "atlassian-check_mark" -> "check_mark")
                emoji_name = emoji_id.replace('atlassian-', '')

                # Map common Atlassian emoji names to their CDN paths
                atlassian_emoji_map = {
                    'check_mark': 'check',
                    'note': 'page',  # note emoji uses 'page' in CDN
                    'warning': 'warning',
                    'question': 'question',
                    'info': 'info',
                    'star': 'star',
                    'thumbs_up': 'thumbsup',
                    'thumbs_down': 'thumbsdown',
                }

                cdn_name = atlassian_emoji_map.get(emoji_name, emoji_name)
                # Generate CDN URL for Atlassian emoji
                emoji_url = f"https://pf-emoji-service--cdn.us-east-1.prod.public.atl-paas.net/atlassian/productivityEmojis/{cdn_name}-32px.png"

                # Return as markdown image with alt text
                alt_text = shortName.strip(':').replace('_', ' ').title()
                return f"![{alt_text}]({emoji_url})"

            # Fallback to shortName for custom user emojis or unknown types
            return shortName

        # Handle date nodes
        elif node_type == 'date':
            from datetime import datetime
            attrs = node.get('attrs', {})
            timestamp = attrs.get('timestamp', '')

            if timestamp:
                try:
                    # Convert timestamp from milliseconds to seconds
                    timestamp_sec = int(timestamp) / 1000
                    # Convert to datetime
                    dt = datetime.fromtimestamp(timestamp_sec)
                    # Format as Korean date (2025년 9월 17일)
                    return dt.strftime('%Y년 %m월 %d일')
                except Exception:
                    pass

            return ''

        # Handle hardBreak (line break)
        elif node_type == 'hardBreak':
            return '\n'

        # Handle embedCard (embedded content like YouTube videos, Figma, etc.)
        elif node_type == 'embedCard':
            attrs = node.get('attrs', {})
            url = attrs.get('url', '')
            if url:
                # Try to extract meaningful title from URL
                try:
                    from urllib.parse import unquote
                    decoded_url = unquote(url)

                    # For Figma links, extract the design name
                    if 'figma.com' in url:
                        parts = decoded_url.split('/')
                        for i, part in enumerate(parts):
                            if part == 'design' and i + 2 < len(parts):
                                title = parts[i + 2].split('?')[0]
                                # Clean up the title (remove leading dash)
                                if title.startswith('-'):
                                    title = title[1:]
                                # Replace dashes with spaces for readability
                                title = title.replace('-', ' ')
                                return f"**Figma:** [{title}]({url})"

                    # For other embedded content, use generic format
                    return f"[{url}]({url})"
                except Exception:
                    return f"[{url}]({url})"
            return ''

        # Handle media nodes (images)
        elif node_type == 'media':
            attrs = node.get('attrs', {})
            media_id = attrs.get('id', '')
            alt_text = attrs.get('alt', '')
            collection = attrs.get('collection', '')

            if media_id and collection:
                # Download image and get local path
                image_path = self._download_media(media_id, collection, alt_text)
                if image_path:
                    return f"![{alt_text}]({image_path})"

            return ''

        # Handle mediaSingle nodes (wrapper for media)
        elif node_type == 'mediaSingle':
            # Extract media and caption from content
            media_text = ''
            caption_text = ''

            for child in node.get('content', []):
                if child.get('type') == 'media':
                    media_text = self._extract_text_from_node(child)
                elif child.get('type') == 'caption':
                    # Extract caption text
                    caption_parts = []
                    for caption_child in child.get('content', []):
                        caption_parts.append(self._extract_text_from_node(caption_child))
                    caption_text = ''.join(caption_parts)

            # Combine media and caption in markdown format
            if media_text and caption_text:
                return f"{media_text}\n*{caption_text}*"
            return media_text

        # Handle layoutSection nodes (layout containers)
        elif node_type == 'layoutSection':
            # Process layout sections recursively
            parts = []
            for child in node.get('content', []):
                parts.append(self._extract_text_from_node(child, context))
            return '\n\n'.join(filter(None, parts))

        # Handle layoutColumn nodes (layout columns)
        elif node_type == 'layoutColumn':
            # Process layout columns recursively
            parts = []
            for child in node.get('content', []):
                parts.append(self._extract_text_from_node(child, context))
            return '\n\n'.join(filter(None, parts))

        # Handle paragraph nodes - special case to detect text + inlineCard patterns
        elif node_type == 'paragraph':
            children = node.get('content', [])
            text_parts = []

            for i, child in enumerate(children):
                child_type = child.get('type')

                # Special handling: if current node is inlineCard and previous was text
                if child_type == 'inlineCard' and i > 0:
                    prev_child = children[i - 1]
                    if prev_child.get('type') == 'text':
                        # Get the preceding text to use as link title
                        preceding_text = prev_child.get('text', '').strip()
                        # Remove the last text part (we'll replace it with a link)
                        if text_parts and preceding_text:
                            text_parts.pop()
                            # Process inlineCard with context
                            link_text = self._extract_text_from_node(child, {'preceding_text': preceding_text})
                            text_parts.append(link_text)
                            continue

                # Normal processing
                text_parts.append(self._extract_text_from_node(child, context))

            # Join with proper spacing
            result = []
            for i, part in enumerate(text_parts):
                result.append(part)
                if i < len(text_parts) - 1 and part:
                    if part.endswith(('**', '*', '`')) and text_parts[i + 1]:
                        result.append(' ')

            return ''.join(result)

        # Recursively extract text from child content
        text_parts = []
        for child in node.get('content', []):
            text_parts.append(self._extract_text_from_node(child, context))

        # Join text parts with proper spacing
        # Add space after formatted text (ending with **, *, or `) when followed by more text
        result = []
        for i, part in enumerate(text_parts):
            result.append(part)
            # Add space if current part ends with formatting marker and next part exists
            if i < len(text_parts) - 1 and part:
                if part.endswith(('**', '*', '`')) and text_parts[i + 1]:
                    result.append(' ')

        return ''.join(result)

    def _extract_extension_content(self, node: Dict) -> str:
        """Extract content from Confluence macro extension nodes"""
        attrs = node.get('attrs', {})
        extension_key = attrs.get('extensionKey', '')

        # Handle Table of Contents (TOC) macro
        if extension_key == 'toc':
            # Return a simple TOC placeholder that indicates where the TOC was
            # The actual TOC generation would require parsing all headings in the document
            # which is complex for this extraction context
            return "## 목차\n\n*이 위치에 자동 생성된 목차가 표시됩니다.*"

        # Handle profile macro (user profile display)
        if extension_key == 'profile':
            params = attrs.get('parameters', {})
            macro_output = params.get('macroOutput', '')

            if macro_output:
                # Parse the HTML output to extract user name
                # The macroOutput contains HTML like: <a class="confluence-userlink">User Name</a>
                from html.parser import HTMLParser

                class UserNameParser(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.user_name = ''
                        self.in_link = False

                    def handle_starttag(self, tag, attrs):
                        if tag == 'a':
                            for attr, value in attrs:
                                if attr == 'class' and 'confluence-userlink' in value:
                                    self.in_link = True

                    def handle_data(self, data):
                        if self.in_link and data.strip():
                            self.user_name = data.strip()

                    def handle_endtag(self, tag):
                        if tag == 'a':
                            self.in_link = False

                parser = UserNameParser()
                try:
                    parser.feed(macro_output)
                    if parser.user_name:
                        return parser.user_name
                except:
                    pass

        # For other extensions, return empty string
        return ''

    def _extract_list_item_content(self, item: Dict, indent_level: int = 0) -> List[str]:
        """Extract content from a list item, handling nested lists

        Returns list of strings, each representing a line with proper indentation
        """
        lines = []
        indent = '  ' * indent_level  # 2 spaces per level

        for content_node in item.get('content', []):
            node_type = content_node.get('type')

            if node_type == 'paragraph':
                # Get paragraph text
                para_text = self._extract_text_from_node(content_node)
                if para_text.strip():
                    lines.append(indent + para_text)

            elif node_type == 'bulletList':
                # Handle nested bullet list
                for nested_item in content_node.get('content', []):
                    if nested_item.get('type') == 'listItem':
                        # Recursively process nested items with increased indentation
                        nested_lines = self._extract_list_item_content(nested_item, indent_level + 1)
                        for nested_line in nested_lines:
                            lines.append(nested_line)

            elif node_type == 'orderedList':
                # Handle nested ordered list
                for i, nested_item in enumerate(content_node.get('content', []), 1):
                    if nested_item.get('type') == 'listItem':
                        # Recursively process nested items with increased indentation
                        nested_lines = self._extract_list_item_content(nested_item, indent_level + 1)
                        for nested_line in nested_lines:
                            lines.append(nested_line)

        return lines

    def _extract_cell_content(self, cell: Dict) -> str:
        """Extract content from table cell, handling complex structures"""
        if not cell:
            return ""

        content_parts = []
        for content_node in cell.get('content', []):
            if content_node.get('type') == 'paragraph':
                # Handle paragraph content within cell
                para_text = self._extract_text_from_node(content_node)
                content_parts.append(para_text)
            elif content_node.get('type') == 'bulletList':
                # Handle bullet lists within cell with proper nesting
                list_lines = []
                for item in content_node.get('content', []):
                    if item.get('type') == 'listItem':
                        # Get first paragraph as the main item text
                        item_content = item.get('content', [])
                        if item_content:
                            # Extract all content from listItem including images
                            first_para = None
                            nested_content = []
                            media_content = []

                            for content in item_content:
                                if content.get('type') == 'paragraph' and first_para is None:
                                    first_para = self._extract_text_from_node(content)
                                elif content.get('type') in ['bulletList', 'orderedList']:
                                    nested_content.append(content)
                                elif content.get('type') == 'mediaSingle':
                                    # Handle images within list items
                                    image_md = self._convert_content_to_markdown([content])
                                    if image_md.strip():
                                        media_content.append(image_md.strip())

                            # Add media content first if present
                            for media in media_content:
                                list_lines.append(media)

                            # Add main item
                            if first_para:
                                list_lines.append(f"• {first_para}")

                            # Add nested lists - process recursively to handle deep nesting
                            def process_nested_list(nested_list, indent_level=1):
                                """Recursively process nested lists with proper indentation"""
                                indent = "&nbsp;&nbsp;" * indent_level

                                if nested_list.get('type') == 'bulletList':
                                    for nested_item in nested_list.get('content', []):
                                        if nested_item.get('type') == 'listItem':
                                            nested_item_content = nested_item.get('content', [])

                                            # Process first paragraph
                                            first_para_text = None
                                            deeper_nested = []

                                            for content in nested_item_content:
                                                if content.get('type') == 'paragraph' and first_para_text is None:
                                                    first_para_text = self._extract_text_from_node(content)
                                                elif content.get('type') in ['bulletList', 'orderedList']:
                                                    deeper_nested.append(content)

                                            # Add the paragraph text
                                            if first_para_text and first_para_text.strip():
                                                list_lines.append(f"{indent}◦ {first_para_text}")

                                            # Recursively process any deeper nested lists
                                            for deeper in deeper_nested:
                                                process_nested_list(deeper, indent_level + 1)

                                elif nested_list.get('type') == 'orderedList':
                                    order = nested_list.get('attrs', {}).get('order', 1)
                                    for nested_item in nested_list.get('content', []):
                                        if nested_item.get('type') == 'listItem':
                                            nested_item_content = nested_item.get('content', [])

                                            # Process first paragraph
                                            first_para_text = None
                                            deeper_nested = []

                                            for content in nested_item_content:
                                                if content.get('type') == 'paragraph' and first_para_text is None:
                                                    first_para_text = self._extract_text_from_node(content)
                                                elif content.get('type') in ['bulletList', 'orderedList']:
                                                    deeper_nested.append(content)

                                            # Add the paragraph text with alphabet format
                                            if first_para_text and first_para_text.strip():
                                                letter = chr(ord('a') + order - 1)
                                                list_lines.append(f"{indent}{letter}. {first_para_text}")

                                            # Recursively process any deeper nested lists
                                            for deeper in deeper_nested:
                                                process_nested_list(deeper, indent_level + 1)

                            # Process all nested content
                            for nested in nested_content:
                                process_nested_list(nested)

                content_parts.append('<br>'.join(list_lines))
            elif content_node.get('type') == 'orderedList':
                # Handle ordered lists within cell - use <br> for line breaks in markdown tables
                list_items = []
                for i, item in enumerate(content_node.get('content', []), 1):
                    if item.get('type') == 'listItem':
                        item_text = self._extract_text_from_node(item)
                        list_items.append(f"{i}. {item_text}")
                content_parts.append('<br>'.join(list_items))
            elif content_node.get('type') == 'codeBlock':
                # Handle code blocks within cell - wrap in backticks
                code_text = self._extract_text_from_node(content_node)
                if code_text.strip():
                    # Use single backticks for inline code in table cells
                    content_parts.append(f"`{code_text}`")
            else:
                # Handle other content types
                text = self._extract_text_from_node(content_node)
                if text.strip():
                    content_parts.append(text)

        # Join paragraphs with <br> for proper line breaks in table cells
        return '<br>'.join(content_parts)

    def _convert_table_to_markdown(self, table_node: Dict) -> str:
        """Convert table node to markdown table with rowspan/colspan handling"""
        rows = []
        is_header_row = True
        rowspan_tracker = {}  # Track cells that span multiple rows: {col_index: (remaining_rows, content)}

        for row_index, row in enumerate(table_node.get('content', [])):
            if row.get('type') == 'tableRow':
                cells = []
                row_is_header = False
                col_index = 0

                for cell in row.get('content', []):
                    if cell.get('type') in ['tableCell', 'tableHeader']:
                        # Skip columns that are occupied by rowspan from previous rows
                        while col_index in rowspan_tracker and rowspan_tracker[col_index][0] > 0:
                            # Use empty cell for rowspan continuation
                            cells.append('')
                            rowspan_tracker[col_index] = (rowspan_tracker[col_index][0] - 1, rowspan_tracker[col_index][1])
                            if rowspan_tracker[col_index][0] == 0:
                                del rowspan_tracker[col_index]
                            col_index += 1

                        if cell.get('type') == 'tableHeader':
                            row_is_header = True

                        # Extract cell content
                        cell_content = self._extract_cell_content(cell)
                        cell_content = cell_content.replace('|', '\\|').replace('\n', ' ').strip()
                        if not cell_content:
                            cell_content = ' '

                        # Handle rowspan
                        attrs = cell.get('attrs', {})
                        rowspan = attrs.get('rowspan', 1)
                        colspan = attrs.get('colspan', 1)

                        # Add cell
                        cells.append(cell_content)

                        # Track rowspan for future rows
                        if rowspan > 1:
                            rowspan_tracker[col_index] = (rowspan - 1, cell_content)

                        # Handle colspan by adding empty cells
                        for _ in range(colspan - 1):
                            col_index += 1
                            cells.append('')

                        col_index += 1

                # Fill remaining columns if rowspan cells occupy them
                while col_index in rowspan_tracker and rowspan_tracker[col_index][0] > 0:
                    cells.append('')
                    rowspan_tracker[col_index] = (rowspan_tracker[col_index][0] - 1, rowspan_tracker[col_index][1])
                    if rowspan_tracker[col_index][0] == 0:
                        del rowspan_tracker[col_index]
                    col_index += 1

                if cells:
                    rows.append('| ' + ' | '.join(cells) + ' |')

                    # Add header separator after header row or first row
                    if (row_is_header or (is_header_row and row_index == 0)) and len(rows) == 1:
                        separator = ['---'] * len(cells)
                        rows.append('| ' + ' | '.join(separator) + ' |')
                        is_header_row = False

        return '\n'.join(rows) + '\n\n' if rows else ''

    def download_page(self, page_info: Dict) -> bool:
        """Download a single page"""
        content_info = page_info.get('content', page_info)
        page_id = content_info.get('id')
        title = content_info.get('title', 'Untitled')

        # Check if should skip (Japanese or custom patterns)
        if self.is_japanese_document(title):
            print(f"Skipping document (filtered): {title}")
            self.skipped_count += 1
            return True

        # Check if should include (custom include patterns)
        if not self.should_include_document(title):
            print(f"Skipping document (not in include list): {title}")
            self.skipped_count += 1
            return True

        # In update mode, check if page has changed since last download
        if self.update_mode:
            version_info = content_info.get('version', {})
            remote_version = version_info.get('number', 0)
            remote_updated = version_info.get('when', '')
            if not self._is_page_updated(page_id, remote_version, remote_updated):
                self.unchanged_count += 1
                return True

        print(f"Downloading: {title}")

        # Get full page content
        page_data = self.get_page_content(page_id)
        if not page_data:
            print(f"Failed to get content for: {title}")
            self.failed_count += 1
            return False

        # Determine folder using hierarchy
        folder_path = self.build_hierarchy_path(page_data)

        # Create folder if it doesn't exist
        # Convert relative path to absolute if needed
        if not os.path.isabs(folder_path):
            full_folder_path = os.path.join(os.getcwd(), folder_path)
        else:
            full_folder_path = folder_path

        os.makedirs(full_folder_path, exist_ok=True)

        # Store current page folder for image relative path calculation
        self.current_page_folder = folder_path

        # Prepare content
        body = page_data.get('body', {})
        atlas_body = body.get('atlas_doc_format', {})

        if atlas_body and atlas_body.get('value'):
            # Save atlas.json for debugging (optional - can be disabled later)
            debug_folder = os.path.join(full_folder_path, 'debug')
            os.makedirs(debug_folder, exist_ok=True)
            atlas_debug_path = os.path.join(debug_folder, f"{page_id}_atlas.json")
            with open(atlas_debug_path, 'w', encoding='utf-8') as f:
                f.write(atlas_body['value'])

            content = self.atlas_doc_to_markdown(atlas_body['value'])
        else:
            content = "Content could not be retrieved or converted."

        # Create markdown document - Extract dates properly
        version_info = page_data.get('version', {})
        history_info = page_data.get('history', {})

        # Try multiple possible date fields
        created_date = (
            history_info.get('createdDate') or
            page_data.get('createdAt') or
            history_info.get('created', {}).get('when') or
            'Unknown'
        )

        updated_date = version_info.get('when', 'Unknown')

        # Extract creator information
        created_by = history_info.get('createdBy', {})
        creator_name = created_by.get('displayName', created_by.get('publicName', 'Unknown'))

        # Format dates if they exist and are not 'Unknown'
        if created_date != 'Unknown':
            try:
                # Parse ISO format and make it more readable
                if 'T' in str(created_date):
                    dt = datetime.fromisoformat(str(created_date).replace('Z', '+00:00'))
                    created_date = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass  # Keep original if parsing fails

        if updated_date != 'Unknown':
            try:
                if 'T' in str(updated_date):
                    dt = datetime.fromisoformat(str(updated_date).replace('Z', '+00:00'))
                    updated_date = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass

        # Get comments for this page
        comments = self.get_page_comments(page_id)
        comments_section = ""

        if comments:
            comments_section = "\n\n---\n\n## 💬 댓글 및 코멘트\n\n"
            for comment in comments:
                comment_body = self.atlas_doc_to_markdown(comment['body']) if comment['body'] else "*(내용 없음)*"
                comment_date = comment['created']
                if 'T' in str(comment_date):
                    try:
                        dt = datetime.fromisoformat(str(comment_date).replace('Z', '+00:00'))
                        comment_date = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass

                # Add comment type indicator
                comment_type_icon = "📌" if comment['type'] == 'inline' else "💭"
                location = comment.get('location_info', '')

                comments_section += f"""### {comment_type_icon} {comment['author']} - {comment_date}{location}

{comment_body}

"""

        markdown_content = f"""# {title}

**문서 ID:** {page_id}
**작성자:** {creator_name}
**작성일:** {created_date}
**최종 업데이트:** {updated_date}
**폴더 경로:** {folder_path}

---

{content}{comments_section}

---

*원본 Confluence 페이지: {CONFLUENCE_BASE_URL}/wiki/spaces/{SPACE_KEY}/pages/{page_id}*"""

        # Save file
        filename = f"{self.sanitize_filename(title)}.md"
        file_path = os.path.join(full_folder_path, filename)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            print(f"Saved: {file_path}")
            self.downloaded_count += 1

            # Update manifest with version info
            page_version = page_data.get('version', {}).get('number', 0)
            self._update_manifest_entry(page_id, page_version, updated_date, file_path, title)

            return True

        except Exception as e:
            print(f"Error saving file {filename}: {e}")
            self.failed_count += 1
            return False

    def get_pages_by_ids(self, page_ids: List[str]) -> List[Dict]:
        """Get specific pages by their IDs"""
        pages = []
        print(f"Test mode: Fetching {len(page_ids)} specific pages...")

        for page_id in page_ids:
            page_data = self.get_page_content(page_id)
            if page_data:
                pages.append(page_data)
                print(f"  ✓ Fetched: {page_data.get('title', 'Untitled')} (ID: {page_id})")
            else:
                print(f"  ✗ Failed to fetch page ID: {page_id}")

        return pages

    def download_all(self):
        """Download all documents from the space using improved retrieval"""
        print(f"Starting download from Confluence Space: {SPACE_KEY}")
        print(f"Base URL: {CONFLUENCE_BASE_URL}")
        if self.update_mode:
            print("🔄 UPDATE MODE: Only downloading new/changed pages")
        print("=" * 60)

        # Check test mode
        if TEST_MODE_ENABLED and TEST_PAGE_IDS:
            print("🔧 TEST MODE: Downloading specific pages only")
            print(f"Page IDs: {TEST_PAGE_IDS}")
            print("=" * 60)
            pages = self.get_pages_by_ids(TEST_PAGE_IDS)
        else:
            # Use combined approach to get all pages
            pages = self.get_all_pages_combined()

            # Apply max_pages limit if set
            if TEST_MAX_PAGES > 0 and len(pages) > TEST_MAX_PAGES:
                print(f"🔧 TEST MODE: Limiting to first {TEST_MAX_PAGES} pages")
                pages = pages[:TEST_MAX_PAGES]

        if not pages:
            print("No pages found!")
            return

        print(f"\nProcessing {len(pages)} pages...")
        print("=" * 60)

        # Download each page with progress tracking
        for i, page in enumerate(pages, 1):
            print(f"\n[{i}/{len(pages)}] ({(i/len(pages)*100):.1f}%)", end=" ")
            success = self.download_page(page)

            # Show current stats every 10 pages
            if i % 10 == 0 or not success:
                stats = f"Downloaded={self.downloaded_count}, Skipped={self.skipped_count}, Failed={self.failed_count}"
                if self.update_mode:
                    stats += f", Unchanged={self.unchanged_count}"
                print(f"  >> Progress: {stats}")

            # Rate limiting from config
            time.sleep(RATE_LIMIT)

        # Save manifest after download completes
        self._save_manifest()

        # Summary
        print("\n" + "=" * 60)
        print("DOWNLOAD SUMMARY")
        print("=" * 60)
        print(f"Total pages found: {len(pages)}")
        print(f"Successfully downloaded: {self.downloaded_count}")
        if self.update_mode:
            print(f"Unchanged (skipped): {self.unchanged_count}")
        print(f"Skipped (filtered): {self.skipped_count}")
        print(f"Failed: {self.failed_count}")

        success_rate = (self.downloaded_count / len(pages) * 100) if pages else 0
        print(f"Success rate: {success_rate:.1f}%")

        if self.update_mode and self.downloaded_count > 0:
            print(f"\n📝 Updated pages:")
            for pid, info in self.manifest.items():
                # Show only pages downloaded in this run
                try:
                    dl_time = datetime.fromisoformat(info.get('downloaded_at', ''))
                    if (datetime.now() - dl_time).total_seconds() < 3600:  # within last hour
                        print(f"   - {info.get('title', 'Unknown')} (v{info.get('version', '?')})")
                except (ValueError, TypeError):
                    pass

        if self.failed_count > 0:
            print(f"\nNote: {self.failed_count} pages failed to download. Check the error messages above.")

        print("=" * 60)

def main():
    """Main function"""
    # Parse command line arguments
    update_mode = '--update' in sys.argv or '-u' in sys.argv
    show_help = '--help' in sys.argv or '-h' in sys.argv

    if show_help:
        print("Confluence Document Downloader")
        print()
        print("Usage: python confluence_downloader.py [OPTIONS]")
        print()
        print("Options:")
        print("  (no args)     Full download - download all pages")
        print("  --update, -u  Incremental update - only download new/changed pages")
        print("  --help, -h    Show this help message")
        print()
        print("The --update flag uses a manifest file (.confluence_manifest.json)")
        print("to track page versions and only re-downloads pages that have been")
        print("modified since the last download.")
        return

    try:
        print("=" * 60)
        print("Confluence Document Downloader")
        print("=" * 60)
        print(f"Configuration loaded from: {DEFAULT_CONFIG_PATH}")
        print(f"Output directory: {OUTPUT_BASE_DIR}")
        print(f"Hierarchy mode: {'Enabled' if USE_HIERARCHY else 'Disabled'}")
        print(f"Max hierarchy depth: {MAX_HIERARCHY_DEPTH if MAX_HIERARCHY_DEPTH > 0 else 'Unlimited'}")
        print(f"Skip Japanese docs: {SKIP_JAPANESE}")

        # Test mode info
        if TEST_MODE_ENABLED and TEST_PAGE_IDS:
            print(f"🔧 TEST MODE: Specific pages ({len(TEST_PAGE_IDS)} pages)")
        elif TEST_MAX_PAGES > 0:
            print(f"🔧 TEST MODE: Limited to {TEST_MAX_PAGES} pages")
        elif update_mode:
            print("🔄 UPDATE MODE: Incremental download (new/changed only)")
        else:
            print("📥 Full download mode")

        print("=" * 60)
        print()

        downloader = ConfluenceDownloader(update_mode=update_mode)
        downloader.download_all()

    except FileNotFoundError as e:
        print(f"Configuration file error: {e}")
        print("\nPlease create a configuration file at: confluence_config.yaml")

    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nTo use this script:")
        print("1. Set your CONFLUENCE_KEY environment variable")
        print("   export CONFLUENCE_KEY='your-api-token-here'")
        print("2. Update confluence_config.yaml with your settings")

    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()