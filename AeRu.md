# AeRu? – Audiobookshelf Email Report Update

**Author:** bengalih  

AeRu? is a Python script that connects to an [Audiobookshelf](https://www.audiobookshelf.org/) server, checks for newly added audiobooks in a specified library within a defined time period, and emails a summary report to all registered users with valid email addresses (or just a test address in test mode).

---

## 📌 Features

- Connects to your Audiobookshelf server using the API
- Fetches all users and validates email addresses
- Retrieves new audiobooks added within the past N days
- Sends a formatted email (plain text and HTML) with book summaries
- Supports test mode for email preview/testing
- Logs status and reports directly to the console

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

To get started with AeRu?, download the script and related files from the official repository:

- **Source Repository**: Clone or download the script from [AeRu.py](AeRu.py).
  ```bash
  git clone https://github.com/bengalih/ABS-scripts.git

---

## ⚙️ Configuration

Edit the configuration section at the top of the script to match your environment:

```python
ABS_SERVER = 'https://your-audiobookshelf-url.com'
API_TOKEN = 'your-api-token'
LIBRARY_NAME = 'Audiobooks'

SMTP_SERVER = 'smtp.yourserver.com'
SMTP_PORT = 587
SMTP_USERNAME = 'you@example.com'
SMTP_PASSWORD = 'your-password'
SMTP_USE_TLS = True

EMAIL_FROM = 'you@example.com'
DISPLAY_NAME = 'Audiobookshelf'
EMAIL_SUBJECT = 'Weekly AudioBook Update Report'

DEFAULT_TEST_MODE = True
TEST_EMAIL_TO = 'you@example.com'
```

---

## 🛠️ Usage

```bash
python aeru.py --days 7 --test
```

### Options

| Option      | Description                                                              |
|-------------|--------------------------------------------------------------------------|
| `--days`    | Number of days back to check for new books (default is set in script)   |
| `--test`    | If present, only sends the report to the test email address             |

---

## 📧 Email Content

The email includes:
- Subject line defined by `EMAIL_SUBJECT`
- Body text listing each newly added book:
  - Title
  - Author
  - Date added
- Formatted in both plain text and HTML

---

## 🔐 Authentication

- Requires an Audiobookshelf API token (`API_TOKEN`)
- Make sure the token has permission to read users and libraries

---

## 🧪 Test Mode

When `--test` flag is enabled (or `DEFAULT_TEST_MODE` is set to `True`), the report is only sent to `TEST_EMAIL_TO` instead of all users.

---

## 📦 Example Output

```text
== Books Added in the Past 7 Days (2 total) ==
- "The Hobbit" by J.R.R. Tolkien, added on 2025-06-01
- "Dune" by Frank Herbert, added on 2025-06-03

TEST MODE is ON. Email will only be sent to: you@example.com
Email sent to: you@example.com
```

---

## 🧾 License

This project is licensed under the **GNU General Public License v3.0**.

You are free to use, modify, and distribute this software under the following conditions:

- You **must credit** the original author
- Any **modified versions must also be open source** under the same license
- You **must include a copy** of the license in any distributions

📄 See the full license text in the [LICENSE](./LICENSE) file or at  
[https://www.gnu.org/licenses/gpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.html)


---

## 🙋‍♂️ Author

Made by **bengalih**.  
Questions or suggestions? Feel free to open an issue or contact the author.
