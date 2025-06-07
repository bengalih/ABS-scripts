# AeFu! - Audiobookshelf Year Fix-up!
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
import csv
import os
import sys
import json
from datetime import datetime
from urllib.parse import quote_plus
import argparse
import re

# === CONFIGURATION ===
# Your Audiobookshelf server & API token
ABS_SERVER = 'https://your-audiobookshelf-url.com'
API_TOKEN = 'your-api-token'
LIBRARY_NAME = 'Audiobooks'

CACHE_FILE = 'ayfu_api_cache.json'
# === CONFIGURATION ===

ABS_SESSION = requests.Session()
ABS_SESSION.headers.update({
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json',
})

REMOTE_SESSION = requests.Session()
REMOTE_SESSION.headers.update({
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0', 
})

def load_cache():
    """Load API results from cache file."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                print(f'-- Invalid cache format in {CACHE_FILE}, expected list')
                return []
        except (json.JSONDecodeError, IOError) as e:
            print(f'-- Error loading cache from {CACHE_FILE}: {e}')
    return []

def save_cache(cache):
    """Save API results to cache file."""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2)
    except IOError as e:
        print(f'-- Error saving cache to {CACHE_FILE}: {e}')

def find_cached_year(cache, title, author):
    """Find cached year for a title and author."""
    normalized_title = normalize_title(title)
    normalized_author = normalize_title(author)
    for item in cache:
        if (normalize_title(item.get('title', '')) == normalized_title and
                normalize_title(item.get('author', '')) == normalized_author):
            return item
    return None

def get_library_id_by_name(library_name):
    url = f'{ABS_SERVER}/api/libraries'
    try:
        response = ABS_SESSION.get(url, timeout=10)
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
    items = []
    page = 0
    limit = 100
    url = f'{ABS_SERVER}/api/libraries/{library_id}/items'
    while True:
        params = {'page': page, 'limit': limit}
        response = ABS_SESSION.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        page_items = data.get('results', [])
        if not page_items:
            break
        items.extend(page_items)
        page += 1
    return items

def update_published_year(item_id, new_year, title, message_prefix="-- Updated year to", commit=False):
    if commit:
        url = f'{ABS_SERVER}/api/items/{item_id}/media'
        payload = {"metadata": {"publishedYear": new_year}}
        response = ABS_SESSION.patch(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f'{message_prefix} {new_year} for "{title}"')
        else:
            print(f'{message_prefix} failed for "{title}": {response.status_code} {response.text}')
    else:
        print(f'-- Detected year {new_year} for "{title}" (not committed)')

def embed_metadata(item_id, title, commit=False):
    if not commit:
        print(f'-- Would embed metadata for item {title} (not committed)')
        return
    url = f'{ABS_SERVER}/api/tools/item/{item_id}/embed-metadata'
    response = ABS_SESSION.post(url, timeout=10)
    if response.status_code == 200:
        print(f'-- Embedded metadata for item {title}')
    else:
        print(f'-- Failed embedding metadata for item {title}: {response.status_code} {response.text}')

def read_csv_updates(filename, debug=False):
    updates = {}
    if not os.path.exists(filename):
        print(f'-- CSV file "{filename}" not found.')
        return updates
    try:
        with open(filename, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            if 'UUID' not in reader.fieldnames or 'Published Year' not in reader.fieldnames:
                print(f'-- CSV file "{filename}" missing required headers: UUID, Published Year')
                return updates
            for row in reader:
                uuid = row.get('UUID', '').strip()
                year = row.get('Published Year', '').strip()
                title = row.get('Title', '').strip()
                if uuid and year and year.isdigit():
                    updates[uuid] = int(year)
                    if debug:
                        print(f'-- Loaded from CSV: UUID={uuid}, Year={year}, Title={title}')
                else:
                    print(f'-- Skipping invalid CSV row: UUID={uuid}, Year={year}, Title={title}')
    except csv.Error as e:
        print(f'-- Error reading CSV "{filename}": {e}')
    return updates

def fetch_year(title, author, debug, no_cache, cache, api_fn, api_name):
    """Fetch year from API with caching."""
    if cache is None:
        cache = []
    cached_item = find_cached_year(cache, title, author)
    if not no_cache and cached_item:
        if debug:
            print(f'-- Using cached year {cached_item["year"]} for "{title}" by {author} from {cached_item["api_used"]} ({cached_item["api_call"]})')
        return cached_item["year"]

    try:
        year, url = api_fn(title, author, debug)
        if year:
            cache.append({
                "title": title,
                "author": author,
                "year": year,
                "api_used": api_name,
                "api_call": url
            })
            save_cache(cache)
            return year
        else:
            print(f'!! WARNING: No publication year found for "{title}" by {author} in {api_name} API')
    except Exception as e:
        print(f'!! ERROR: querying {api_name} for "{title}" by {author}: {e}')
    return None

def fetch_year_google_api(title, author, debug):
    query = f'https://www.googleapis.com/books/v1/volumes?q=intitle:"{quote_plus(title)}"+inauthor:"{quote_plus(author)}"'
    if debug:
        print(f'-- Querying Google Books API: {query}')
    response = REMOTE_SESSION.get(query, timeout=10)
    if response.status_code == 200:
        data = response.json()
        years = []
        for item in data.get('items', []):
            pub_date = item.get('volumeInfo', {}).get('publishedDate', '')
            match = re.match(r'(\d{4})', pub_date)
            if match:
                years.append(int(match.group(1)))
        return min(years) if years else None, query
    else:
        print(f'!! WARNING: Google Books API returned status {response.status_code} for "{title}" by {author}')
    return None, query

def fetch_year_ol_api(title, author, debug):
    if isinstance(author, str):
        author_list = [a.strip() for a in author.split(",")]
    else:
        author_list = author
    query_author = author_list[0]
    base_url = 'https://openlibrary.org/search.json'
    url = f"{base_url}?title={quote_plus(title)}&author={quote_plus(query_author)}&fields=title,author_name,first_publish_year&sort=old&limit=1"
    if debug:
        print(f'-- Querying OpenLibrary API: {url}')
    response = REMOTE_SESSION.get(url, timeout=10)
    if response.status_code == 200:
        data = response.json()
        docs = data.get('docs', [])
        years = [doc.get('first_publish_year') for doc in docs if doc.get('first_publish_year') is not None]
        return min(years) if years else None, url
    else:
        print(f'-- WARNING! OpenLibrary API returned status {response.status_code} for "{title}" by {author}')
    return None, url

def normalize_title(title):
    """Normalize title by removing special characters and extra spaces for matching."""
    if not title:
        return ''
    return re.sub(r'[:,\s]+', ' ', title.strip()).lower()

def get_book_metadata(book):
    """Extract metadata fields from a book."""
    media = book.get('media', {})
    metadata = media.get('metadata', {})
    return {
        'title': metadata.get('title', 'Unknown Title'),
        'titleIgnorePrefix': metadata.get('titleIgnorePrefix', 'Unknown Title'),
        'author': metadata.get('authorName', 'Unknown Author'),
        'authorLF': metadata.get('authorNameLF', 'Author, Unknown'),
        'narrator': metadata.get('narratorName', ''),
        'series': metadata.get('seriesName', ''),
        'genres': metadata.get('genres', []),
        'tags': media.get('tags', []),
        'publishedYear': metadata.get('publishedYear'),
        'addedAt': book.get('addedAt'),
        'id': book.get('id', 'Unknown ID')
    }

def parse_filters(filter_args):
    """Parse filter arguments into a dictionary of criteria."""
    filters = {}
    valid_keys = {'title', 'author', 'narrator', 'series', 'genres', 'tags'}
    for arg in filter_args:
        if ':' not in arg:
            print(f'!! WARNING: Invalid filter "{arg}", expected key:value')
            continue
        key, value = arg.split(':', 1)
        key = key.lower().strip()
        if key not in valid_keys:
            print(f'!! WARNING: Unsupported filter key "{key}"')
            continue
        if not value.strip():
            print(f'!! WARNING: Empty filter value for "{key}"')
            continue
        filters[key] = value.strip()
    return filters

def filter_books(books, filters, debug=False):
    """Filter books based on criteria."""
    if not filters:
        return books
    filter_fns = {
        'title': lambda m, v: v.lower() in m['title'].lower(),
        'author': lambda m, v: v.lower() in m['author'].lower(),
        'narrator': lambda m, v: v.lower() in m['narrator'].lower(),
        'series': lambda m, v: any(v.lower() in s.lower() for s in [s.strip() for s in m['series'].split(',') if s.strip()]),
        'genres': lambda m, v: any(v.lower() in g.lower() for g in m['genres']),
        'tags': lambda m, v: any(v.lower() in t.lower() for t in m['tags'])
    }
    filtered_books = []
    for book in books:
        meta = get_book_metadata(book)
        if debug and 'tags' in filters:
            print(f'-- Tags for "{meta["title"]}": {meta["tags"]}')
        if all(filter_fns[key](meta, value) for key, value in filters.items()):
            filtered_books.append(book)
    return filtered_books

def get_sort_key(field):
    def key(book):
        val = get_book_metadata(book).get(field)
        if isinstance(val, str):
            return val.split(',')[0].strip().lower()
        return val if val is not None else ''
    return key

def parse_sort_args(sort_args):
    # Known valid fields from metadata
    metadata_keys = list(get_book_metadata({}).keys())
    key_map = {k.lower(): k for k in metadata_keys}

    sort_fields = []

    for arg in sort_args:
        if ':' in arg:
            field, direction = arg.split(':', 1)
        else:
            field, direction = arg, 'asc'

        field_lc = field.lower()
        if field_lc not in key_map:
            raise ValueError(f"Invalid sort field: {field}")
        resolved_field = key_map[field_lc]
        reverse = direction.lower() == 'desc'

        sort_fields.append((resolved_field, reverse))

    return sort_fields


def apply_sorting(books, sort_args):
    sort_fields = parse_sort_args(sort_args)
    for field, reverse in reversed(sort_fields):  # sort least to most significant
        books.sort(key=get_sort_key(field), reverse=reverse)


def main():
    parser = argparse.ArgumentParser(description='Update audiobook published years.')
    parser.add_argument('--library', type=str, default=LIBRARY_NAME, help='Library name to process')
    parser.add_argument('--csv', type=str, help='CSV file with backup data')
    parser.add_argument('--update-missing', action='store_true', help='Update books missing from CSV with API lookup')
    parser.add_argument('--filter', type=str, action='append', metavar='x:value', default=[], help='x = title, author, narrator, series, genres, tags')
    parser.add_argument('--sort', type=str, action='append', metavar='x:asc|desc', default=[], help='x = title, titleIgnorePrefix, author, authorLF, narrator, publishedYear, addedAt'),
    parser.add_argument('--commit', action='store_true', help='Actually commit changes to API')
    parser.add_argument('--embed', action='store_true', help='Embed metadata after updating year')
    parser.add_argument('--use-google', action='store_true', help='Use Google Books API instead of OpenLibrary')
    parser.add_argument('--no-cache', action='store_true', help='Bypass cache and query APIs for all entries')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()

    debug = args.debug
    commit = args.commit
    embed = args.embed
    use_csv_input = args.csv is not None and os.path.exists(args.csv)
    use_google = args.use_google
    update_missing = args.update_missing
    no_cache = args.no_cache

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f'audiobooks_{timestamp}.log'
    output_csv = f'audiobooks_{timestamp}.csv'

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

    cache = load_cache()
    library_id = get_library_id_by_name(args.library)
    csv_updates = read_csv_updates(args.csv, debug=debug) if use_csv_input else {}
    books = get_books(library_id)

    filters = parse_filters(args.filter)
    books = filter_books(books, filters, debug)

    default_sort = [('author', False), ('title', False)]
    apply_sorting(books, args.sort)

    print(f"Found {len(books)} book(s) in library after filtering.\n")

    with open(output_csv, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Title', 'Author', 'UUID', 'Published Year'])

        for book in books:
            meta = get_book_metadata(book)
            title, author, current_year, item_id = meta['title'], meta['author'], meta['publishedYear'], meta['id']
            print(f"- {title} by {author} ({current_year})")
            writer.writerow([title, author, item_id, current_year])

            new_year = None
            message_prefix = "-- Updated year to"
            if use_csv_input and item_id in csv_updates:
                new_year = csv_updates[item_id]
                message_prefix = "-- Restored year to"
            elif (not use_csv_input) or (use_csv_input and update_missing and item_id not in csv_updates):
                fetch_fn = fetch_year_google_api if use_google else fetch_year_ol_api
                new_year = fetch_year(title, author, debug, no_cache, cache, fetch_fn, "Google Books" if use_google else "OpenLibrary")

            if new_year:
                try:
                    current_year_int = int(current_year) if current_year else None
                    if current_year_int != new_year:
                        update_published_year(item_id, new_year, title, message_prefix, commit)
                        if embed:
                            embed_metadata(item_id, title, commit)
                except (ValueError, TypeError):
                    update_published_year(item_id, new_year, title, message_prefix, commit)
                    if embed:
                        embed_metadata(item_id, title, commit)

if __name__ == '__main__':
    main()
