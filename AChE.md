# AChE – Audiobookshelf Chapter Editor

**Author:** bengalih  

AChE is a Python script that downloads chapters from audiobooks for easy editng and importation back into ABS.

---

## 📌 Features

- Search for books based on standard ABS search (Title, ASIN, ISBN)
- Select from multiple matches
- Download chapter listings to simple TAB format file
- Update chapter list on the fly and re-import immediately
- Copy export files to import location and import them individually or in bulk
- Import from .CUE files

---

## 🚀 Requirements

- Python 3.7+
  
Install dependencies via:

```bash
pip install requests
```
---
## 📥 Download

To get started with AChE, download the script and related files from the official repository:

- **Source Repository**: Clone or download the script from [AChE.py](AChE.py).

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
and optionally:
```python
EXPORT_TXT_DIR = "chapter-export"
EXPORT_JSON_DIR = "chapter-json"
IMPORT_DIR = "chapter-import"
USE_HHMMSS = True
SEARCH_LIMIT = 20
# User-configurable editor (default)
DEFAULT_EDITOR_WINDOWS = "notepad.exe"
#DEFAULT_EDITOR_WINDOWS = "C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE"   # Double slashes needed
DEFAULT_EDITOR_LINUX = "nano"  # Or "gedit", "kate", etc.
```

Make sure your API token has permission to access users, libraries, and items.

---

## 🛠️ Usage

```bash
python ache.py 
```

## 📂 Output

On first run the export and import folder will be created.
Search for a book (usually via Title or ASIN) and the chapter list will be downloaded to the export folder.
You can edit directly with an editor of your choice and then immediately upload it.
Alternatively, you can move it to the import folder and on next run it will be validated for importation.

---

## ⚙️ File Structure

The script exports chapter files with a header in the format:

<pre>
# Title: The Metamorphosis
# Author: Franz Kafka
# Item ID: 6142c810-72e2-4bb2-a18e-115aa8342632
# ASIN: B004Y0K5V6
# ISBN: None
</pre>

Only the `Item ID` header line is required when importing, the rest are informational.
You can create your own files for import as long as they have the `Item ID` header line and are in the proper TAB separated format.
.CUE file format is also supported, but you must add the header line to the top of the .CUE file.

The script requires, and only matches on, `Item ID` as it is the only unique field to ensure no conflicts.

The easiest ways to find the `Item ID` are:

- Export the chapters and grab the header line.
- Open for the book in ABS and the URL will display the `Item ID`:
  
  audiobookshelf.mydomain.com/audiobookshelf/item/**bbb7c502-e262-4e8b-b8de-503da6d93a71**

---

## ⚙️ Editors

When downloading a chapter list, you can press (E) to edit the file immediately.
This will open up the user configured editor program and pass the filename.
Sending this to an editor which supports TAB separated fields, like Excel, will allow you to past in a column for just the chapters without modifying the times.
If your editor locks the file down, be sure to close it before trying to over-write.

You can choose not to use the (E)dit function and simply open the file through other means, edit, and upload.
You can also edit it later and put it in the import directory for parsing on next run.

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

## 🙋‍♂️ Issues
 
Feedback, bugs, or improvements? Feel free to open an issue or contribute!
