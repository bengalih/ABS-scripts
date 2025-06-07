# ApTaGu - Audiobookshelf Path Tag and Genre Updater
# Copyright (C) 2025 bengalih
# version: 1.0.0

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import requests
import os
import sys
import json
import argparse
from datetime import datetime
import re
import csv

# === CONFIGURATION ===
ABS_SERVER = 'https://your-audiobookshelf-url.com'
API_TOKEN = 'your-api-token'
LIBRARY_NAME = 'Audiobooks'
# === CONFIGURATION ===

SESSION = requests.Session()
SESSION.headers.update({
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json',
})

def get_library_id_by_name(library_name):
    """Fetch library ID by name."""
    url = f'{ABS_SERVER}/api/libraries'
    try:
        response = SESSION.get(url, timeout=10)
        response.raise_for_status()
        libraries = response.json().get('libraries', [])
        for lib in libraries:
            if lib.get('name', '').lower() == library_name.lower():
                return lib.get('id')
        print(f'-- Library "{library_name}" not found.')
        sys.exit(1)
    except requests.RequestException as e:
        print(f'-- Error fetching libraries: {e}')
        sys.exit(1)

def get_books(library_id):
    """Fetch all books in the library with pagination."""
    items = []
    page = 0
    limit = 100
    url = f'{ABS_SERVER}/api/libraries/{library_id}/items'
    while True:
        params = {'page': page, 'limit': limit}
        try:
            response = SESSION.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            page_items = data.get('results', [])
            if not page_items:
                break
            items.extend(page_items)
            page += 1
        except requests.RequestException as e:
            print(f'-- Error fetching books: {e}')
            sys.exit(1)
    return items

def get_book_metadata(book):
    """Extract metadata fields from a book."""
    media = book.get('media', {})
    metadata = media.get('metadata', {})
    path = book.get('path', '')
    return {
        'title': metadata.get('title', 'Unknown Title'),
        'author': metadata.get('authorName', 'Unknown Author'),
        'id': book.get('id', 'Unknown ID'),
        'tags': media.get('tags', []),
        'genres': metadata.get('genres', []),
        'audio_files': [path] if path else []
    }

def update_book_field(item_id, field, values, title, commit=False, debug=False):
    """Update tags or genres for a book."""
    if field not in ['tags', 'genres']:
        print(f'-- Invalid field "{field}" for update.')
        return False
    url = f'{ABS_SERVER}/api/items/{item_id}/media'
    payload = {"metadata": {field: values}} if field == 'genres' else {field: values}
    if not commit:
        print(f'-- Would update {field} for "{title}" to {values} (not committed)')
        return True
    try:
        response = SESSION.patch(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f'-- Updated {field} for "{title}" to {values}')
            return True
        else:
            print(f'-- Failed to update {field} for "{title}": {response.status_code} {response.text}')
            return False
    except requests.RequestException as e:
        print(f'-- Error updating {field} for "{title}": {e}')
        return False

def parse_rules(rule_args):
    """Parse rule arguments into a list of (pattern, tag/genre) pairs."""
    rules = []
    for rule in rule_args:
        if ':' not in rule:
            print(f'!! WARNING: Invalid rule "{rule}", expected pattern:tag')
            continue
        pattern, tag = rule.split(':', 1)
        pattern = pattern.strip()
        tag = tag.strip()
        if not pattern or not tag:
            print(f'!! WARNING: Empty pattern or tag in rule "{rule}"')
            continue
        try:
            re.compile(pattern)
            rules.append((pattern, tag))
        except re.error:
            print(f'!! WARNING: Invalid regex pattern "{pattern}" in rule')
    return rules

def match_path(audio_files, pattern, whole_word=False):
    """Check if any audio file path matches the pattern."""
    for path in audio_files:
        if whole_word:
            # Match whole word in path segments (e.g., /Fiction/ or \bFiction\b)
            pattern = rf'(^|[\\/])\b{re.escape(pattern)}\b([\\/]|$)'
        if re.search(pattern, path, re.IGNORECASE):
            return True
    return False

def main():
    parser = argparse.ArgumentParser(description='Update or remove audiobook tags or genres based on file path patterns.')
    parser.add_argument('--library', type=str, default=LIBRARY_NAME, help='Library name to process')
    parser.add_argument('--rule', type=str, action='append', metavar='pattern:tag', default=[], help='Regex pattern and tag/genre to apply, e.g., "Nonfiction:Non-fiction"')
    parser.add_argument('--remove', type=str, action='append', metavar='pattern:tag', default=[], help='Regex pattern and tag/genre to remove, e.g., "Nonfiction:Fiction"')
    parser.add_argument('--field', type=str, choices=['tags', 'genres'], default='tags', help='Field to update (tags or genres)')
    parser.add_argument('--whole-word', action='store_true', help='Match patterns as whole words in path segments')
    parser.add_argument('--commit', action='store_true', help='Actually commit changes to API')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()

    debug = args.debug
    commit = args.commit
    field = args.field
    whole_word = args.whole_word
    add_rules = parse_rules(args.rule)
    remove_rules = parse_rules(args.remove)
    if not add_rules and not remove_rules:
        print('!! ERROR: No valid rules provided. Use --rule or --remove with pattern:tag')
        sys.exit(1)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f'tag_genre_update_{timestamp}.log'
    output_csv = f'tag_genre_update_{timestamp}.csv'

    class Logger:
        def __init__(self, filename):
            self.terminal = sys.stdout
            self.log = open(filename, "a", encoding='utf-8')
        def write(self, message):
            self.terminal.write(message)
            self.log.write(message)
        def flush(self):
            self.terminal.flush()
            self.log.flush()

    sys.stdout = Logger(log_filename)

    library_id = get_library_id_by_name(args.library)
    books = get_books(library_id)
    print(f"Found {len(books)} book(s) in library.\n")

    with open(output_csv, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Title', 'Author', 'UUID', 'Audio Files', f'Current {field.capitalize()}', f'New {field.capitalize()}'])

        for book in books:
            meta = get_book_metadata(book)
            title, author, item_id, current_values, audio_files = meta['title'], meta['author'], meta['id'], meta[field], meta['audio_files']
            if debug:
                print(f'-- Processing "{title}" by {author}, Files: {audio_files}, Current {field}: {current_values}')

            new_values = current_values.copy()
            applied_rules = []
            # Apply remove rules first
            for pattern, tag in remove_rules:
                if match_path(audio_files, pattern, whole_word):
                    if tag in new_values:
                        new_values.remove(tag)
                        applied_rules.append((pattern, f"remove {tag}"))
                        if debug:
                            print(f'-- Matched pattern "{pattern}" for "{title}", removing {field[:-1]} "{tag}"')
            # Then apply add rules
            for pattern, tag in add_rules:
                if match_path(audio_files, pattern, whole_word):
                    if tag not in new_values:
                        new_values.append(tag)
                        applied_rules.append((pattern, f"add {tag}"))
                        if debug:
                            print(f'-- Matched pattern "{pattern}" for "{title}", adding {field[:-1]} "{tag}"')

            if applied_rules:
                writer.writerow([title, author, item_id, ';'.join(audio_files), ';'.join(current_values), ';'.join(new_values)])
                update_book_field(item_id, field, new_values, title, commit, debug)
            else:
                writer.writerow([title, author, item_id, ';'.join(audio_files), ';'.join(current_values), ';'.join(current_values)])
                if debug:
                    print(f'-- No rules matched for "{title}"')

    print(f"\nLog written to {log_filename}")
    print(f"CSV output written to {output_csv}")

if __name__ == '__main__':
    main()
