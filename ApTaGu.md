# ApTaGu – Audiobookshelf Path Tag and Genre Updater

ApTaGu is a Python script that updates or removes tags and genres for audiobooks in your [Audiobookshelf](https://www.audiobookshelf.org/) library based on file path patterns. This tool helps you apply consistent metadata based on your folder structure or filename conventions.

---

## 📌 Features

- Automatically apply or remove **tags** or **genres** based on regex path patterns
- Supports **dry-run** (preview without changes) and **commit** modes
- Generates a **log file** and **CSV report** of all changes
- Filters by **whole word path segments** (optional)

---

## 🚀 Requirements

- Python 3.7+
- `requests` package

Install dependencies via:

```bash
pip install requests
```
---
## 📥 Download

To get started with ApTaGu, download the script and related files from the official repository:

- **Source Repository**: Clone or download the script from [ApTaGu.py](ApTaGu.py).
  ```bash
  git clone https://github.com/bengalih/ABS-scripts.git

---

## ⚙️ Configuration

Edit the script’s configuration block before running:

```python
ABS_SERVER = 'https://your-audiobookshelf-url.com'
API_TOKEN = 'your-api-token'
LIBRARY_NAME = 'Audiobooks'
```

Make sure your API token has permission to access users, libraries, and items.

---

## 🛠️ Usage

```bash
python aptagu.py --rule "Fiction:Fiction" --rule "Nonfiction:Non-fiction" --field tags --commit
```

### Common Options

| Option               | Description                                                                 |
|----------------------|-----------------------------------------------------------------------------|
| `--rule`             | Add rule in the form `pattern:tag_or_genre` (can repeat)                    |
| `--remove`           | Remove tag/genre using the same pattern syntax                              |
| `--field`            | Choose to update `tags` or `genres` (default: `tags`)                       |
| `--whole-word`       | Match patterns as whole words in folder paths                               |
| `--commit`           | Actually commit the changes to the server                                   |
| `--debug`            | Print detailed debug output                                                 |
| `--library`          | Optional override of library name                                           |

> 🔁 If `--commit` is not specified, the script runs in preview mode.

---

## 🧪 Examples

### Preview changes:
```bash
python aptagu.py --rule "SciFi:Sci-Fi" --field genres
```

### Commit changes:
```bash
python aptagu.py --rule "Nonfiction:Non-fiction" --remove "Fiction:Non-fiction" --field tags --commit
```

### Match as whole path segments:
```bash
python aptagu.py --rule "Mystery:Mystery" --whole-word
```

---

## 📂 Output

Each run will generate:
- 📄 A log file: `tag_genre_update_YYYYMMDD_HHMMSS.log`
- 📊 A CSV report: `tag_genre_update_YYYYMMDD_HHMMSS.csv`

The CSV includes:
- Title
- Author
- UUID
- Audio file paths
- Original tags/genres
- Updated tags/genres

---

## 🧾 License

This project is licensed under the **GNU General Public License v3.0**.

You are free to use, modify, and distribute this software under the following conditions:

- You **must credit** the original author
- Any **modified versions must also be open source** under the same license
- You **must include a copy** of the license in any distributions

📄 See the full license in the [LICENSE](./LICENSE) file or at  
[https://www.gnu.org/licenses/gpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.html)

---

## 🙋‍♂️ Author

**bengalih** 
Feedback, bugs, or improvements?
Feel free to open an issue or contribute!

