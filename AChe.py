# AChE - Audiobookshelf Chapter Editor
# Copyright (C) 2025 bengalih
# version: 0.4.1

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
import json
import os
import re
import urllib
import subprocess
import platform

# === CONFIGURATION ===
ABS_SERVER = 'https://your-audiobookshelf-url.com'
API_TOKEN = 'your-api-token'
LIBRARY_NAME = 'Audiobooks'
EXPORT_TXT_DIR = "chapter-export"
EXPORT_JSON_DIR = "chapter-json"
IMPORT_DIR = "chapter-import"
USE_HHMMSS = True
SEARCH_LIMIT = 20
DEFAULT_EDITOR_WINDOWS = "notepad.exe"
DEFAULT_EDITOR_LINUX = "nano"  # Or "gedit", "kate", etc.
# === CONFIGURATION ===

# Auto-select default editor based on platform
if platform.system() == "Windows":
    DEFAULT_EDITOR = DEFAULT_EDITOR_WINDOWS
else:
    DEFAULT_EDITOR = DEFAULT_EDITOR_LINUX

# Allow override via ENV variable, optional
EDITOR = os.environ.get("AUDIOBOOK_EDITOR", DEFAULT_EDITOR)

SESSION = requests.Session()
SESSION.headers.update({
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json',
})

def seconds_to_hhmmss(seconds):
    seconds = int(round(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def hhmmss_to_seconds(hms):
    parts = hms.strip().split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h)*3600 + int(m)*60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m)*60 + float(s)
    else:
        return float(hms)

def get_library_id():
    url = f"{ABS_SERVER}/api/libraries"
    r = SESSION.get(url)
    r.raise_for_status()
    libs = r.json().get("libraries", [])
    for lib in libs:
        if lib.get("name", "").lower() == LIBRARY_NAME.lower():
            return lib.get("id")
    raise Exception(f"Library '{LIBRARY_NAME}' not found")

def search_books(library_id, query):
    url = f"{ABS_SERVER}/api/libraries/{library_id}/search"
    params = {
    "q": query,
    "limit": SEARCH_LIMIT
    }


    try:
        r = SESSION.get(url, params=params)
        # print(f"DEBUG: API Response Status: {r.status_code}")
        r.raise_for_status()
        data = r.json()
        items = data.get("book", [])

        matches = []
        for item in items:
            lib_item = item.get("libraryItem", {})
            md = lib_item.get("media", {}).get("metadata", {})
            matches.append({
                "id": lib_item.get("id", ""),
                "title": md.get("title", "Unknown"),
                "author": md.get("authorName", "Unknown Author"),
                "asin": md.get("asin", ""),
                "isbn": md.get("isbn", "")
            })

        return matches

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e.response.status_code} - {e.response.text}")
        return []
    except requests.RequestException as e:
        print(f"Search error: {e}")
        return []

def validate_book_id(book_id):
    url = f"{ABS_SERVER}/api/items/{book_id}"
    try:
        r = SESSION.get(url)
        r.raise_for_status()  # will raise error if not found (404)
        item = r.json()
        # Optionally check the top-level item ID matches:
        returned_id = item.get("id")
        return returned_id == book_id
    except requests.RequestException:
        return False


def fetch_chapters(book_id):
    url = f"{ABS_SERVER}/api/items/{book_id}?expanded=1"
    r = SESSION.get(url)
    r.raise_for_status()
    item = r.json()
    chapters = item.get("media", {}).get("chapters", [])
    return chapters

def set_chapters(book_id, chapters):
    url = f"{ABS_SERVER}/api/items/{book_id}/chapters"
    payload = { "chapters": chapters }
    r = SESSION.post(url, json=payload)
    r.raise_for_status()
    chapter_count = len(chapters)
    print(f"Updated {chapter_count} chapter(s) for book id {book_id}")

def sanitize_filename(name):
    # Replace invalid characters with underscore
    return re.sub(r'[\/:*?"<>|]', '_', name)

def export_chapters_json(book, chapters, filename):
    metadata = {
        "title": book['title'],
        "author": book['author'],
        "item_id": book['id'],
        "asin": book['asin'],
        "isbn": book['isbn']
    }
    export_data = {
        "__metadata__": metadata,
        "chapters": chapters
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2)
   
def export_chapters_editable(book, chapters, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# Title: {book['title']}\n")
        f.write(f"# Author: {book['author']}\n")
        f.write(f"# Item ID: {book['id']}\n")
        f.write(f"# ASIN: {book['asin']}\n")
        f.write(f"# ISBN: {book['isbn']}\n")
        f.write("\n")

        for ch in chapters:
            title = ch.get("title", "")
            start = ch.get("start", 0)
            start_str = seconds_to_hhmmss(start) if USE_HHMMSS else str(start)
            f.write(f"{title}\t{start_str}\n")

    print(f"Exported {len(chapters)} chapter(s) to '{filename}'")
    
    while True:
        user_input = input("==> (E)dit this file then Enter to import or e(x)it... ").strip().lower()
        
        if user_input in ("e", "x", ""):
            break
        
        print("Invalid input. Please enter 'E', 'x', or just press Enter to import.")

    if user_input == "x":
        print("Skipping import. You can import later via chapter-import folder.")
        exit(0)

    if user_input == "e":
        print(f"Opening editor for '{filename}'...")
        try:
            if platform.system() == "Windows":
                os.startfile(filename)
            else:
                subprocess.Popen([EDITOR, filename])
        except Exception as e:
            print(f"Failed to open editor: {e}")

        # Wait for user to confirm after editing
        input("Press Enter after you finish editing to import chapters...")


def import_chapters_from_cue(filename):
    chapters = []
    current_title = None
    current_start = None
    idx = 0

    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.upper().startswith("TITLE") and not line.upper().startswith("FILE"):
                # Extract title
                current_title = line.split("TITLE", 1)[1].strip().strip('"')
            elif line.upper().startswith("INDEX 01"):
                # Extract time
                time_str = line.split("INDEX 01", 1)[1].strip()
                # Convert MM:SS:FF → seconds
                m, s, f_ = map(int, time_str.split(":"))
                start_seconds = m * 60 + s + (f_ / 75.0)

                # Add chapter entry
                chapters.append({
                    "id": idx,
                    "start": start_seconds,
                    "title": current_title or f"Chapter {idx+1}",
                    "end": 0  # will be fixed below
                })
                idx += 1

    # Fix 'end' times
    for i in range(len(chapters) - 1):
        chapters[i]["end"] = chapters[i+1]["start"]
    if chapters:
        chapters[-1]["end"] = chapters[-1]["start"] + 600  # last chapter

    return chapters


def import_chapters_editable(filename):
    # If it's a CUE file, parse it via CUE parser
    if filename.lower().endswith(".cue"):
        print(f"Importing chapters from CUE file: {filename}")
        return import_chapters_from_cue(filename)

    chapters = []
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Skip header lines
    lines = [line for line in lines if not line.startswith("#") and line.strip()]

    for idx, line in enumerate(lines):
        line = line.strip()
        if "\t" not in line:
            print(f"Skipping malformed line {idx+1}: {line}")
            continue
        title, time_str = line.split("\t", 1)
        if re.match(r"^\d+:\d{2}:\d{2}$", time_str) or re.match(r"^\d+:\d{2}$", time_str):
            start = hhmmss_to_seconds(time_str)
        else:
            try:
                start = float(time_str)
            except:
                print(f"Invalid time format on line {idx+1}: {time_str}, skipping")
                continue
        chapters.append({
            "id": idx,
            "start": start,
            "title": title.strip(),
            "end": 0
        })

    for i in range(len(chapters) - 1):
        chapters[i]["end"] = chapters[i+1]["start"]
    if chapters:
        chapters[-1]["end"] = chapters[-1]["start"] + 600

    return chapters


def scan_import_folder(library_id):
    if not os.path.isdir(IMPORT_DIR):
        return

    files = [f for f in os.listdir(IMPORT_DIR) if f.lower().endswith((".txt", ".cue"))]
    if not files:
        return

    print(f"Found {len(files)} files in '{IMPORT_DIR}'.")
    print("- Checking headers")

    import_candidates = []

    for filename in files:
        path = os.path.join(IMPORT_DIR, filename)
        with open(path, 'r', encoding='utf-8') as f:
            # Read first 5 lines (or fewer if file is short)
            header_lines = []
            for _ in range(5):
                line = f.readline()
                if not line:
                    break
                header_lines.append(line.strip())

        # Only consider lines starting with "#"
        header_lines = [line for line in header_lines if line.startswith("#")]

        meta = {}
        for line in header_lines:
            try:
                key, value = line[2:].split(":", 1)
                meta[key.strip().lower()] = value.strip()
            except ValueError:
                # Skip malformed header lines
                continue

        if "item id" in meta:
            import_candidates.append({
                "filename": filename,
                "path": path,
                "meta": meta
            })

    if not import_candidates:
        print("No valid import files found.")
        return


    print("\nImport candidates:")
    for idx, c in enumerate(import_candidates):
        meta = c['meta']
        title = meta.get('title') or "Unknown Title"
        author = meta.get('author') or "Unknown Author"
        item_id = meta.get('item id') or "ID Unknown"
        asin = meta.get('asin') or "Unknown"
        isbn = meta.get('isbn') or "Unknown"

        print(f"{idx+1}. {c['filename']} - {title} by {author} (Item ID: {item_id}, ASIN: {asin}, ISBN: {isbn})")

    while True:
        mode = input("\nImport chapters from these books? (a)ll/(s)tep/(n)o/(q)uit: ").strip().lower()
        if mode in ("a", "s", "n", "q"):
            break
        print("Invalid input. Please enter 'a', 's', or 'n'.")

    if mode == "q":
        exit(0);
    if mode == "n":
        return


    for c in import_candidates:
        if mode == "s":
            single = input(f"Import '{c['filename']}'? (y/n): ").strip().lower()
            if single != "y":
                continue

        book_id = c['meta'].get("item id")
        book_name = c['meta'].get('title')
        
        # Verify book exists

        match = validate_book_id(book_id)

        if match:
            print(f"{book_name} found in library, importing.")
        else:
            print(f"{book_name} with Item ID {book_id} not found in library, skipping.")
            continue


        new_chapters = import_chapters_editable(c['path'])
        set_chapters(book_id, new_chapters)

def main():
    os.makedirs(EXPORT_JSON_DIR, exist_ok=True)
    os.makedirs(EXPORT_TXT_DIR, exist_ok=True)
    os.makedirs(IMPORT_DIR, exist_ok=True)

    library_id = get_library_id()

    # First, scan import folder
    scan_import_folder(library_id)

    # Proceed with search
    user_query = input("Search ASIN, Title, or (q)uit: ").strip().lower()
    if user_query == "q":
        exit()

    matches = search_books(library_id, user_query)

    if not matches:
        print("No matches found.")
        return

    if len(matches) == 1:
        book = matches[0]
    else:
        print("\nMultiple matches found:")
        for idx, m in enumerate(matches):
            print(f"{idx+1}. {m['title']} by {m['author']} (ASIN: {m['asin']})")
        while True:
            choice = input(f"Select book [1-{len(matches)}] or (q)uit: ").strip().lower()
            
            if choice == "q":
                exit(0)
            
            if choice.isdigit():
                num = int(choice)
                if 1 <= num <= len(matches):
                    book = matches[num - 1]
                    break  # valid choice → break loop
            
            print(f"Invalid input. Please enter a number between 1 and {len(matches)}, or 'q' to quit.")


    print(f"\nSelected book: {book['title']} (ASIN: {book['asin']}) by {book['author']}")

    short_book_id = book['id'].split('-')[0]

    json_filename = sanitize_filename(os.path.join(EXPORT_JSON_DIR, f"{book['title']}_{short_book_id}_chapters.json"))
    txt_filename = sanitize_filename(os.path.join(EXPORT_TXT_DIR, f"{book['title']}_{short_book_id}_chapters.txt"))

    chapters = fetch_chapters(book["id"])

    export_chapters_json(book, chapters, json_filename)
    export_chapters_editable(book, chapters, txt_filename)

    new_chapters = import_chapters_editable(txt_filename)

    set_chapters(book["id"], new_chapters)

if __name__ == "__main__":
    main()
