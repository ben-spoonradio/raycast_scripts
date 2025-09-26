#!/usr/bin/env python3
"""
Confluence Documents Downloader
Downloads all Korean documents from Confluence Space SM using local API key
Filters out Japanese documents automatically
"""

import os
import json
import re
import time
import requests
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote
from datetime import datetime
import base64

# Configuration
CONFLUENCE_BASE_URL = "https://your-domain.atlassian.net"
SPACE_KEY = "AM"
CONFLUENCE_EMAIL = "your-email@example.com"  # Update with your email
CONFLUENCE_API_TOKEN = os.getenv('CONFLUENCE_KEY')  # Set this environment variable

# Legacy folder mapping - kept as fallback for specific page categorization
LEGACY_FOLDER_MAPPING = {
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
}

class ConfluenceDownloader:
    def __init__(self):
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

    def is_japanese_document(self, title: str, content: str = "") -> bool:
        """Determine if a document is primarily Japanese content"""
        # Explicit Japanese markers
        if title.startswith('[JP]') or '[JP]' in title:
            return True

        # Japanese-only titles or heavy Japanese content indicators
        japanese_indicators = [
            '日本', 'JP Market', 'IP確保에 관한 사항',
            'Japanese', 'Japan', '일본', 'JP ver.'
        ]

        for indicator in japanese_indicators:
            if indicator in title:
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
        ancestors = page_data.get('ancestors', [])

        if not ancestors:
            return "Root_Documents"

        path_parts = []
        for ancestor in ancestors:
            title = ancestor.get('title', 'Unknown')
            # Skip space homepage or very generic titles
            if title.lower() in ['home', 'homepage', 'space home', 'sm']:
                continue
            folder_name = self.sanitize_filename(title)
            if folder_name and len(folder_name) > 0:
                path_parts.append(folder_name)

        if not path_parts:
            return "Root_Documents"

        # Limit depth to avoid overly nested structures
        if len(path_parts) > 3:
            path_parts = path_parts[:3]

        return os.path.join(*path_parts)

    def get_folder_path(self, parent_id: str) -> str:
        """Get folder path based on parent ID (fallback method)"""
        return LEGACY_FOLDER_MAPPING.get(parent_id, "Root_Documents")

    def get_all_pages_content_api(self) -> List[Dict]:
        """Get all pages using content API (alternative method)"""
        all_pages = []
        start = 0
        limit = 100  # Increased limit

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
        limit = 100  # Increased limit

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

    def get_page_content(self, page_id: str, max_retries: int = 3) -> Optional[Dict]:
        """Get full page content including body with retry logic"""
        url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content/{page_id}"
        params = {
            'expand': 'body.atlas_doc_format,version,space,ancestors,history'
        }

        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                return response.json()

            except requests.Timeout:
                print(f"Timeout getting page content for {page_id} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff

            except requests.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    print(f"Rate limited for page {page_id} (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(5 * (attempt + 1))  # Longer wait for rate limits
                elif e.response.status_code == 404:
                    print(f"Page {page_id} not found (404)")
                    return None
                else:
                    print(f"HTTP error {e.response.status_code} getting page content for {page_id}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)

            except requests.RequestException as e:
                print(f"Error getting page content for {page_id} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        print(f"Failed to get page content for {page_id} after {max_retries} attempts")
        return None

    def atlas_doc_to_markdown(self, atlas_content: str) -> str:
        """Convert Atlas Document Format to Markdown (simplified)"""
        try:
            doc = json.loads(atlas_content)
            return self._convert_content_to_markdown(doc.get('content', []))
        except json.JSONDecodeError:
            print("Warning: Could not parse Atlas Document Format, returning as plain text")
            return atlas_content

    def _convert_content_to_markdown(self, content: List[Dict]) -> str:
        """Recursively convert content nodes to markdown"""
        markdown = []

        for node in content:
            node_type = node.get('type')

            if node_type == 'paragraph':
                text = self._extract_text_from_node(node)
                if text.strip():
                    markdown.append(text)

            elif node_type == 'heading':
                level = node.get('attrs', {}).get('level', 1)
                text = self._extract_text_from_node(node)
                if text.strip():
                    markdown.append('#' * level + ' ' + text)

            elif node_type == 'bulletList':
                list_items = []
                for item in node.get('content', []):
                    if item.get('type') == 'listItem':
                        text = self._extract_text_from_node(item)
                        if text.strip():
                            list_items.append(f"• {text}")
                if list_items:
                    markdown.extend(list_items)

            elif node_type == 'orderedList':
                list_items = []
                for i, item in enumerate(node.get('content', []), 1):
                    if item.get('type') == 'listItem':
                        text = self._extract_text_from_node(item)
                        if text.strip():
                            list_items.append(f"{i}. {text}")
                if list_items:
                    markdown.extend(list_items)

            elif node_type == 'table':
                table_md = self._convert_table_to_markdown(node)
                if table_md.strip():
                    markdown.append(table_md.strip())

            elif node_type == 'codeBlock':
                language = node.get('attrs', {}).get('language', '')
                text = self._extract_text_from_node(node)
                if text.strip():
                    markdown.append(f"```{language}\n{text}\n```")

            elif node_type == 'rule':
                # Horizontal rule
                markdown.append('---')

        # Join with double newlines for proper paragraph separation
        return '\n\n'.join(filter(None, markdown))

    def _extract_text_from_node(self, node: Dict) -> str:
        """Extract plain text from a node"""
        if not node:
            return ""

        if node.get('type') == 'text':
            text = node.get('text', '')
            marks = node.get('marks', [])

            for mark in marks:
                mark_type = mark.get('type')
                if mark_type == 'strong':
                    text = f"**{text}**"
                elif mark_type == 'em':
                    text = f"*{text}*"
                elif mark_type == 'code':
                    text = f"`{text}`"

            return text

        # Recursively extract text from child content
        text_parts = []
        for child in node.get('content', []):
            text_parts.append(self._extract_text_from_node(child))

        return ''.join(text_parts)

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
                # Handle bullet lists within cell
                for item in content_node.get('content', []):
                    if item.get('type') == 'listItem':
                        item_text = self._extract_text_from_node(item)
                        content_parts.append(f"• {item_text}")
            elif content_node.get('type') == 'orderedList':
                # Handle ordered lists within cell
                for i, item in enumerate(content_node.get('content', []), 1):
                    if item.get('type') == 'listItem':
                        item_text = self._extract_text_from_node(item)
                        content_parts.append(f"{i}. {item_text}")
            else:
                # Handle other content types
                text = self._extract_text_from_node(content_node)
                if text.strip():
                    content_parts.append(text)

        return ' '.join(content_parts)

    def _convert_table_to_markdown(self, table_node: Dict) -> str:
        """Convert table node to markdown table"""
        rows = []
        is_header_row = True

        for row_index, row in enumerate(table_node.get('content', [])):
            if row.get('type') == 'tableRow':
                cells = []
                row_is_header = False

                for cell in row.get('content', []):
                    if cell.get('type') in ['tableCell', 'tableHeader']:
                        if cell.get('type') == 'tableHeader':
                            row_is_header = True

                        # Extract cell content more carefully
                        cell_content = self._extract_cell_content(cell)
                        # Clean up the content and escape pipes
                        cell_content = cell_content.replace('|', '\\|').replace('\n', ' ').strip()
                        if not cell_content:
                            cell_content = ' '
                        cells.append(cell_content)

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

        # Check if Japanese document
        if self.is_japanese_document(title):
            print(f"Skipping Japanese document: {title}")
            self.skipped_count += 1
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
        full_folder_path = os.path.join(os.getcwd(), folder_path)
        os.makedirs(full_folder_path, exist_ok=True)

        # Prepare content
        body = page_data.get('body', {})
        atlas_body = body.get('atlas_doc_format', {})

        if atlas_body and atlas_body.get('value'):
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

        markdown_content = f"""# {title}

**문서 ID:** {page_id}
**작성일:** {created_date}
**최종 업데이트:** {updated_date}
**폴더 경로:** {folder_path}

---

{content}

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
            return True

        except Exception as e:
            print(f"Error saving file {filename}: {e}")
            self.failed_count += 1
            return False

    def download_all(self):
        """Download all documents from the space using improved retrieval"""
        print(f"Starting download from Confluence Space: {SPACE_KEY}")
        print(f"Base URL: {CONFLUENCE_BASE_URL}")
        print("=" * 60)

        # Use combined approach to get all pages
        pages = self.get_all_pages_combined()

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
                print(f"  >> Progress: Downloaded={self.downloaded_count}, Skipped={self.skipped_count}, Failed={self.failed_count}")

            # Rate limiting - slightly increased for better throughput
            time.sleep(0.8)

        # Summary
        print("\n" + "=" * 60)
        print("DOWNLOAD SUMMARY")
        print("=" * 60)
        print(f"Total pages found: {len(pages)}")
        print(f"Successfully downloaded: {self.downloaded_count}")
        print(f"Skipped (Japanese): {self.skipped_count}")
        print(f"Failed: {self.failed_count}")

        success_rate = (self.downloaded_count / len(pages) * 100) if pages else 0
        print(f"Success rate: {success_rate:.1f}%")

        if self.failed_count > 0:
            print(f"\nNote: {self.failed_count} pages failed to download. Check the error messages above.")

        print("=" * 60)

def main():
    """Main function"""
    try:
        downloader = ConfluenceDownloader()
        downloader.download_all()

    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nTo use this script:")
        print("1. Set your CONFLUENCE_KEY environment variable")
        print("   export CONFLUENCE_KEY='your-api-token-here'")
        print("2. Update CONFLUENCE_EMAIL in the script with your email")

    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()