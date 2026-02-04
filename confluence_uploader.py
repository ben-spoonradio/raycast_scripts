#!/usr/bin/env python3
"""
Confluence Document Uploader
Uploads Markdown documents and images to Confluence using Storage Format (XHTML).
Supports page creation, update, image attachments, and dry-run mode.
"""

import os
import re
import sys
import time
import json
import mimetypes
import argparse
import requests
import yaml
import base64
from typing import Dict, List, Optional, Tuple
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

CONFLUENCE_BASE_URL = config['confluence']['base_url']
SPACE_KEY = config['confluence']['space_key']
CONFLUENCE_EMAIL = config['confluence']['email']
CONFLUENCE_API_TOKEN = os.getenv('CONFLUENCE_KEY')

MAX_RETRIES = config['download']['max_retries']
REQUEST_TIMEOUT = config['download']['timeout']
RATE_LIMIT = config['download']['rate_limit']


class MarkdownToStorageConverter:
    """Converts Markdown text to Confluence Storage Format (XHTML)."""

    def __init__(self):
        self.images: List[str] = []  # collected image paths

    def convert(self, markdown_text: str) -> str:
        """Convert full markdown body to Confluence storage format."""
        self.images = []
        lines = markdown_text.split('\n')
        html_parts = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Fenced code block
            if line.strip().startswith('```'):
                block, i = self._parse_code_block(lines, i)
                html_parts.append(block)
                continue

            # Horizontal rule
            if re.match(r'^---+\s*$', line.strip()):
                html_parts.append('<hr/>')
                i += 1
                continue

            # Heading
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                level = len(heading_match.group(1))
                text = self._convert_inline(heading_match.group(2))
                html_parts.append(f'<h{level}>{text}</h{level}>')
                i += 1
                continue

            # Table
            if '|' in line and i + 1 < len(lines) and re.match(r'^[\s|:-]+$', lines[i + 1]):
                table, i = self._parse_table(lines, i)
                html_parts.append(table)
                continue

            # Unordered list
            if re.match(r'^[\s]*[-*+]\s', line):
                block, i = self._parse_list(lines, i, ordered=False)
                html_parts.append(block)
                continue

            # Ordered list
            if re.match(r'^[\s]*\d+\.\s', line):
                block, i = self._parse_list(lines, i, ordered=True)
                html_parts.append(block)
                continue

            # Blockquote
            if line.strip().startswith('>'):
                block, i = self._parse_blockquote(lines, i)
                html_parts.append(block)
                continue

            # Empty line
            if not line.strip():
                i += 1
                continue

            # Regular paragraph
            text = self._convert_inline(line)
            html_parts.append(f'<p>{text}</p>')
            i += 1

        return '\n'.join(html_parts)

    def _parse_code_block(self, lines: List[str], start: int) -> Tuple[str, int]:
        """Parse a fenced code block."""
        first_line = lines[start].strip()
        lang_match = re.match(r'^```(\w*)', first_line)
        lang = lang_match.group(1) if lang_match else ''

        code_lines = []
        i = start + 1
        while i < len(lines):
            if lines[i].strip() == '```':
                i += 1
                break
            code_lines.append(lines[i])
            i += 1

        code_content = '\n'.join(code_lines)

        if lang:
            html = (
                f'<ac:structured-macro ac:name="code">'
                f'<ac:parameter ac:name="language">{lang}</ac:parameter>'
                f'<ac:plain-text-body><![CDATA[{code_content}]]></ac:plain-text-body>'
                f'</ac:structured-macro>'
            )
        else:
            html = (
                f'<ac:structured-macro ac:name="code">'
                f'<ac:plain-text-body><![CDATA[{code_content}]]></ac:plain-text-body>'
                f'</ac:structured-macro>'
            )
        return html, i

    def _parse_table(self, lines: List[str], start: int) -> Tuple[str, int]:
        """Parse a markdown table."""
        header_cells = [c.strip() for c in lines[start].strip().strip('|').split('|')]
        i = start + 2  # skip separator line

        rows_html = []
        # Header row
        header_html = '<tr>' + ''.join(
            f'<th>{self._convert_inline(c)}</th>' for c in header_cells
        ) + '</tr>'
        rows_html.append(header_html)

        # Data rows
        while i < len(lines) and '|' in lines[i] and lines[i].strip():
            cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
            row_html = '<tr>' + ''.join(
                f'<td>{self._convert_inline(c)}</td>' for c in cells
            ) + '</tr>'
            rows_html.append(row_html)
            i += 1

        return '<table>' + ''.join(rows_html) + '</table>', i

    def _parse_list(self, lines: List[str], start: int, ordered: bool) -> Tuple[str, int]:
        """Parse an ordered or unordered list (single level)."""
        tag = 'ol' if ordered else 'ul'
        pattern = r'^[\s]*\d+\.\s+(.+)$' if ordered else r'^[\s]*[-*+]\s+(.+)$'
        items = []
        i = start

        while i < len(lines):
            m = re.match(pattern, lines[i])
            if m:
                items.append(self._convert_inline(m.group(1)))
                i += 1
            else:
                break

        items_html = ''.join(f'<li>{item}</li>' for item in items)
        return f'<{tag}>{items_html}</{tag}>', i

    def _parse_blockquote(self, lines: List[str], start: int) -> Tuple[str, int]:
        """Parse a blockquote block."""
        quote_lines = []
        i = start

        while i < len(lines) and lines[i].strip().startswith('>'):
            text = re.sub(r'^>\s?', '', lines[i])
            quote_lines.append(text)
            i += 1

        inner = self._convert_inline('\n'.join(quote_lines))
        return f'<blockquote><p>{inner}</p></blockquote>', i

    def _convert_inline(self, text: str) -> str:
        """Convert inline markdown elements to HTML."""
        # Images: ![alt](path) or ![alt|width=600](path)
        def replace_image(m):
            alt_raw = m.group(1)
            path = m.group(2)
            filename = os.path.basename(path)
            self.images.append(path)
            # Parse optional width: ![alt|width=600](path)
            width_attr = ''
            alt = alt_raw
            width_match = re.match(r'^(.+?)\|width=(\d+)$', alt_raw)
            if width_match:
                alt = width_match.group(1)
                width_attr = f' ac:width="{width_match.group(2)}"'
            return (
                f'<ac:image ac:alt="{self._escape_xml(alt)}"{width_attr}>'
                f'<ri:attachment ri:filename="{self._escape_xml(filename)}"/>'
                f'</ac:image>'
            )

        text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_image, text)

        # Links: [text](url)
        text = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            lambda m: f'<a href="{self._escape_xml(m.group(2))}">{m.group(1)}</a>',
            text
        )

        # Bold: **text** or __text__
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)

        # Italic: *text* or _text_
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'<em>\1</em>', text)

        # Strikethrough: ~~text~~
        text = re.sub(r'~~(.+?)~~', r'<del>\1</del>', text)

        # Inline code: `code`
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

        # Line break: <br> from markdown <br> or trailing double space
        text = re.sub(r'<br\s*/?>', '<br/>', text)

        return text

    @staticmethod
    def _escape_xml(text: str) -> str:
        """Escape XML special characters."""
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        return text


class ConfluenceUploader:
    """Uploads Markdown documents and images to Confluence."""

    def __init__(self):
        if not CONFLUENCE_API_TOKEN:
            raise ValueError("CONFLUENCE_KEY environment variable is required")

        auth_string = f"{CONFLUENCE_EMAIL}:{CONFLUENCE_API_TOKEN}"
        self.auth_header = base64.b64encode(auth_string.encode()).decode()

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Basic {self.auth_header}",
            "Accept": "application/json",
        })

        self.converter = MarkdownToStorageConverter()

    # ------------------------------------------------------------------
    # Markdown parsing helpers
    # ------------------------------------------------------------------

    def parse_markdown_file(self, filepath: str) -> Tuple[Dict, str]:
        """Parse a markdown file into metadata dict and body text.

        Returns (metadata, body) where metadata may contain:
          - title, doc_id, author, created, updated, folder_path
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')
        metadata: Dict[str, str] = {}
        body_start = 0

        # Parse metadata header
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('# ') and 'title' not in metadata:
                metadata['title'] = stripped[2:].strip()
            elif stripped.startswith('**문서 ID:**'):
                metadata['doc_id'] = stripped.replace('**문서 ID:**', '').strip()
            elif stripped.startswith('**작성자:**'):
                metadata['author'] = stripped.replace('**작성자:**', '').strip()
            elif stripped.startswith('**작성일:**'):
                metadata['created'] = stripped.replace('**작성일:**', '').strip()
            elif stripped.startswith('**최종 업데이트:**'):
                metadata['updated'] = stripped.replace('**최종 업데이트:**', '').strip()
            elif stripped.startswith('**폴더 경로:**'):
                metadata['folder_path'] = stripped.replace('**폴더 경로:**', '').strip()
            elif stripped == '---':
                body_start = idx + 1
                break
            elif stripped == '' and idx > 0 and not metadata:
                continue

        # If no --- separator found, use everything after metadata lines
        if body_start == 0:
            body_start = len(metadata) + 1  # rough fallback

        body = '\n'.join(lines[body_start:])
        return metadata, body

    # ------------------------------------------------------------------
    # Confluence API methods
    # ------------------------------------------------------------------

    def _api_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make an API request with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                resp = self.session.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
                if resp.status_code == 429:
                    wait = int(resp.headers.get('Retry-After', 10))
                    print(f"  Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    print(f"  Request failed ({e}), retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise
        raise RuntimeError("Max retries exceeded")

    def find_page_by_title(self, title: str, space_key: str = SPACE_KEY) -> Optional[Dict]:
        """Find an existing page by title in the space."""
        url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content"
        params = {
            'title': title,
            'spaceKey': space_key,
            'expand': 'version',
        }
        resp = self._api_request('GET', url, params=params)
        results = resp.json().get('results', [])
        return results[0] if results else None

    def find_page_by_id(self, page_id: str) -> Optional[Dict]:
        """Get page info by ID."""
        url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content/{page_id}"
        params = {'expand': 'version'}
        try:
            resp = self._api_request('GET', url, params=params)
            return resp.json()
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            raise

    def find_parent_page(self, parent_title: str = None, parent_id: str = None) -> Optional[Dict]:
        """Resolve parent page by title or ID."""
        if parent_id:
            return self.find_page_by_id(parent_id)
        if parent_title:
            return self.find_page_by_title(parent_title)
        return None

    def create_page(self, title: str, body_storage: str,
                    space_key: str = SPACE_KEY,
                    parent_id: str = None) -> Dict:
        """Create a new Confluence page."""
        url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content"
        payload = {
            'type': 'page',
            'title': title,
            'space': {'key': space_key},
            'body': {
                'storage': {
                    'value': body_storage,
                    'representation': 'storage',
                }
            },
        }
        if parent_id:
            payload['ancestors'] = [{'id': str(parent_id)}]

        resp = self._api_request('POST', url, json=payload)
        return resp.json()

    def update_page(self, page_id: str, title: str, body_storage: str,
                    current_version: int) -> Dict:
        """Update an existing Confluence page."""
        url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content/{page_id}"
        payload = {
            'id': str(page_id),
            'type': 'page',
            'title': title,
            'body': {
                'storage': {
                    'value': body_storage,
                    'representation': 'storage',
                }
            },
            'version': {
                'number': current_version + 1,
            },
        }
        resp = self._api_request('PUT', url, json=payload)
        return resp.json()

    def get_existing_attachments(self, page_id: str) -> Dict[str, Dict]:
        """Get map of filename -> attachment info for a page."""
        url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content/{page_id}/child/attachment"
        params = {'limit': 200}
        resp = self._api_request('GET', url, params=params)
        results = resp.json().get('results', [])
        return {att['title']: att for att in results}

    def upload_attachment(self, page_id: str, filepath: str, existing_attachments: Dict = None) -> bool:
        """Upload a file as an attachment to a Confluence page.

        Skips upload if an attachment with the same filename already exists
        (unless the file size differs).
        Returns True if uploaded, False if skipped.
        """
        filepath = str(filepath)
        filename = os.path.basename(filepath)

        if not os.path.isfile(filepath):
            print(f"  ⚠️  Image file not found: {filepath}")
            return False

        # Check for existing attachment
        if existing_attachments and filename in existing_attachments:
            local_size = os.path.getsize(filepath)
            remote_size = existing_attachments[filename].get('extensions', {}).get('fileSize', -1)
            if remote_size != -1 and int(remote_size) == local_size:
                print(f"  ⏭️  Attachment already exists (same size): {filename}")
                return False

        mime_type = mimetypes.guess_type(filepath)[0] or 'application/octet-stream'

        url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content/{page_id}/child/attachment"

        # Attachment upload requires special header and no JSON content-type
        headers = {
            'X-Atlassian-Token': 'nocheck',
        }

        with open(filepath, 'rb') as f:
            files = {'file': (filename, f, mime_type)}
            resp = self._api_request('POST', url, headers=headers, files=files)

        print(f"  📎 Uploaded: {filename}")
        return True

    # ------------------------------------------------------------------
    # High-level upload workflow
    # ------------------------------------------------------------------

    def upload(self, filepath: str,
               parent_title: str = None,
               parent_id: str = None,
               update: bool = False,
               dry_run: bool = False) -> None:
        """Main upload workflow for a single markdown file."""
        filepath = os.path.abspath(filepath)
        file_dir = os.path.dirname(filepath)

        print(f"\n📄 Processing: {filepath}")

        # 1. Parse markdown
        metadata, body = self.parse_markdown_file(filepath)
        title = metadata.get('title', Path(filepath).stem.replace('_', ' '))
        doc_id = metadata.get('doc_id')

        print(f"  Title: {title}")
        if doc_id:
            print(f"  Document ID: {doc_id}")

        # 2. Convert to storage format
        storage_html = self.converter.convert(body)
        image_refs = self.converter.images  # relative paths collected during conversion

        # 3. Resolve image file paths
        image_files = []
        for ref in image_refs:
            # Try relative to markdown file directory
            img_path = os.path.normpath(os.path.join(file_dir, ref))
            if os.path.isfile(img_path):
                image_files.append(img_path)
            elif os.path.isfile(ref):  # absolute or cwd-relative
                image_files.append(os.path.abspath(ref))
            else:
                print(f"  ⚠️  Image not found: {ref}")

        if image_files:
            print(f"  🖼️  Found {len(image_files)} image(s) to upload")

        # 4. Dry-run: print converted HTML and exit
        if dry_run:
            print("\n--- Dry Run: Confluence Storage Format ---")
            print(storage_html)
            print("--- End ---")
            if image_files:
                print(f"\nImages to upload ({len(image_files)}):")
                for img in image_files:
                    print(f"  - {img}")
            return

        # 5. Check for existing page
        existing_page = None
        if update and doc_id:
            existing_page = self.find_page_by_id(doc_id)
        if not existing_page and update:
            existing_page = self.find_page_by_title(title)

        # 6. Create or update page
        if existing_page:
            page_id = existing_page['id']
            current_version = existing_page['version']['number']
            print(f"  🔄 Updating existing page (id={page_id}, version={current_version})")
            result = self.update_page(page_id, title, storage_html, current_version)
        else:
            # Resolve parent
            parent = self.find_parent_page(parent_title=parent_title, parent_id=parent_id)
            resolved_parent_id = parent['id'] if parent else None
            if parent:
                print(f"  📁 Parent page: {parent.get('title', parent_id)} (id={parent['id']})")
            print(f"  ✨ Creating new page...")
            result = self.create_page(title, storage_html, parent_id=resolved_parent_id)
            page_id = result['id']

        time.sleep(RATE_LIMIT)

        # 7. Upload images
        if image_files:
            existing_atts = self.get_existing_attachments(page_id)
            uploaded = 0
            for img in image_files:
                if self.upload_attachment(page_id, img, existing_atts):
                    uploaded += 1
                time.sleep(RATE_LIMIT)
            print(f"  🖼️  Images uploaded: {uploaded}/{len(image_files)}")

        # 8. Print result
        page_url = f"{CONFLUENCE_BASE_URL}/wiki/spaces/{SPACE_KEY}/pages/{page_id}"
        link = result.get('_links', {}).get('base', CONFLUENCE_BASE_URL) + result.get('_links', {}).get('webui', '')
        if link and link != CONFLUENCE_BASE_URL:
            page_url = link

        action = "Updated" if existing_page else "Created"
        print(f"\n✅ {action} page: {title}")
        print(f"   URL: {page_url}")


def main():
    parser = argparse.ArgumentParser(
        description='Upload Markdown documents to Confluence'
    )
    parser.add_argument('file', help='Path to the Markdown file to upload')
    parser.add_argument('--parent', help='Parent page title')
    parser.add_argument('--parent-id', help='Parent page ID')
    parser.add_argument('--update', action='store_true',
                        help='Update existing page if found (by doc ID or title)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Convert and print storage format without uploading')

    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    uploader = ConfluenceUploader()
    uploader.upload(
        filepath=args.file,
        parent_title=args.parent,
        parent_id=args.parent_id,
        update=args.update,
        dry_run=args.dry_run,
    )


if __name__ == '__main__':
    main()
