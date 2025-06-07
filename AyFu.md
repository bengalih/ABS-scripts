# AyFu! - Audiobookshelf Year Fix-up!

**Author:** bengalih  

AyFu! (Audiobookshelf Year Fix-up!) is a Python script that updates the publication years of audiobooks in your [Audiobookshelf](https://www.audiobookshelf.org/) library with the actual publication year of the original book (as opposed to the publication date of a particular version of an audiobook).
It fetches publication years from either the OpenLibrary (default) or Google Books API and applies them to audiobook metadata.
The script supports filtering, sorting, caching, and optional metadata embedding.

---

## 📌 Features

- Updates audiobook publication years using or OpenLibrary (default) or Google Books APIs.
- Supports CSV backup and input for restoring original year data.
- Filters books by title, author, narrator, series, genres, or tags.
- Sorts books by metadata fields (e.g., title, author, published year).
- Caches API results in a JSON file to reduce redundant queries.
- Generates a log file and CSV report of all changes.
- Supports **dry-run** (preview without changes) and **commit** modes.
- Optionally triggers Audiobookshelf "Embed Metadata" after updates.

---

## 🚀 Requirements

- Python 3.6+
- Required packages:
  - `requests`
  - `csv`
  - `json`
  - `urllib.parse`
  - `argparse`
  - `re`

Install dependencies via:
```bash
pip install requests
```

---

## 📥 Download

To get started with AyFu!, download the script and related files from the official repository:

- **Source Repository**: Clone or download the script from [AyFu.py](AyFu.py).
  ```bash
  git clone https://github.com/bengalih/ABS-scripts.git

---

## ⚙️ Configuration

Edit the configuration block at the top of the script (`AyFu.py`):

```python
ABS_SERVER = 'https://your-audiobookshelf-url.com'
API_TOKEN = 'your-api-token'
LIBRARY_NAME = 'Audiobooks'
CACHE_FILE = 'ayfu_api_cache.json'
```

- `ABS_SERVER`: URL of your Audiobookshelf server.
- `API_TOKEN`: Your Audiobookshelf API token with permissions to access libraries and items.
- `LIBRARY_NAME`: Name of the library to process (e.g., `Audiobooks`).
- `CACHE_FILE`: File to store cached API results (default: `ayfu_api_cache.json`).  Optional, can just leave as-is.

Ensure your API token has appropriate permissions for ABS library and item operations.

---

## 📚 Providers & API Keys

**AeFu!** supports fetching publication years from two different public data sources (APIs):

### 1️⃣ Default Provider: OpenLibrary API

- By default, AeFu! uses the [OpenLibrary API](https://openlibrary.org/developers/api).
- No API key or account is required — it is a free and open API.
- You do not need to configure anything to use this provider.

### 2️⃣ Optional Provider: Google Books API 

- You can optionally use the [Google Books API](https://developers.google.com/books).
- To enable it, use the `--use-google` command-line option when running AeFu!.

**Note:** OpenLibrary appears to generally have more accurate data in my experience.  It also allows editing of its database so you can always create an account an correct any inaccurate data.

---

## 🛠️ Usage

Run the script with optional arguments:
```bash
python AyFu.py [--library LIBRARY] [--csv FILE] [--update-missing] [--filter x:value] [--sort x:asc|desc] [--commit] [--embed] [--use-google] [--no-cache] [--debug]
```

### Command-Line Arguments

| Option             | Description                                                                 |
|--------------------|-----------------------------------------------------------------------------|
| `--library`        | Override default library name in script (default: `Audiobooks`)            |
| `--csv`            | CSV backup file with item UUID and Published Year for restoring years      |
| `--update-missing` | Update books missing from CSV with API lookup (when --csv used)            |
| `--filter`         | Filter books by `title`, `author`, `narrator`, `series`, `genres`, or `tags` (e.g., `title:Potter`) |
| `--sort`           | Sort books by `title`, `titleIgnorePrefix`, `author`, `authorLF`, `narrator`, `publishedYear`, or `addedAt` (e.g., `author:desc`) |
| `--commit`         | Commit changes to the Audiobookshelf server                                 |
| `--embed`          | Trigger ABS "Embed Metadata" into audiobook files                           |
| `--use-google`     | Use Google Books API instead of OpenLibrary API                            |
| `--no-cache`       | Bypass cache and query APIs for all books (use sparingly                    |
| `--debug`          | Enable detailed debug output                                               |

> 🔁 If `--commit` is not specified, the script runs in preview mode.

---

## 🧪 Examples

### Preview updates for all books:
```bash
python AyFu.py --library Audiobooks
```
This will, by default, generate a .CSV file that can be used to restore the current export of data.
It is recommended you save the .CSV file from your first run so that you can always restore the original data.

### Update years from a CSV file and commit:
```bash
python AyFu.py --csv audiobooks_20250607_124907.csv --commit
```
This will restore all the years from the specified CSV file and commit them to the ABS database.

### Restore from CSV:
```bash
python AyFu.py --csv updates.csv --commit
```

### Restore from CSV and update missing books/years:
```bash
python AyFu.py --csv updates.csv --update-missing --commit
```
By default, when a .CSV is provided, the script only uses the CSV data and does not fetch year data for any books not listed in the CSV.
If you add --update-missing, the script will also look up publication years for any books that are missing from the CSV, but found in ABS.

### Filter by author and sort by title:
```bash
python AyFu.py --filter author:Rowling --sort title:asc 
```

### Embed metadata after updating years:
```bash
python AyFu.py --commit --embed 
```

---

## 📂 Output

Each run generates:
- 📄 A log file: `audiobooks_YYYYMMDD_HHMMSS.log`
- 📊 A CSV report: `audiobooks_YYYYMMDD_HHMMSS.csv`

The CSV includes:
- Title
- Author
- UUID
- Published Year

Example CSV row:
```csv
Title,Author,UUID,Published Year
The Metamorphosis,Franz Kafka,6142c810-72e2-4bb2-a18e-115aa8342632,2011
```

---

## 📚 Caching Mechanism

The caching mechanism is to prevent excessive load on public API servers.
While running the script, especially on large libraries you may experience network, load, or limit errors.
I have not tested the full limits of these servers, but they may throttle you after 1000 API lookups a day.
By implementing a cache mechanism you can update a collection of say 2000 books by running in two separate sessions (if throttled).

I highly recommend relying on the cache and not deleting or bypassing it in entirety.
If required you can edit or delete entries in the cache

Example cache entry:
```json
  {
    "title": "The Metamorphosis",
    "author": "Franz Kafka",
    "year": 1922,
    "api_used": "OpenLibrary",
    "api_call": "https://openlibrary.org/search.json?title=The+Metamorphosis&author=Franz+Kafka&fields=title,author_name,first_publish_year&sort=old&limit=1"
  },
```

---

## 📝 License

This project is licensed under the **GNU General Public License v3.0**.

You are free to use, modify, and distribute this software under the following conditions:
- You **must credit** the original author
- Any **modified versions must also be open source** under the same license.
- You **must include a copy** of the license in any distributions.

📄 See the full license in the [LICENSE](./LICENSE) file or at  
[https://www.gnu.org/licenses/gpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.html)

---

## 🙋‍♂️ Author

**bengalih** – passionate about audiobook automation.  
Feedback, bugs, or improvements? Feel free to open an issue or contribute!
