# AeRu? - Audiobookshelf Email Report Update
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
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage
import re
import argparse

# === CONFIGURATION ===
# Your Audiobookshelf server & API token
ABS_SERVER = 'https://your-audiobookshelf-url.com'
API_TOKEN = 'your-api-token'

# Library name to report on
LIBRARY_NAME = 'Audiobooks'

# SMTP settings for sending email
SMTP_SERVER = 'smtp.yourserver.com'
SMTP_PORT = 587
SMTP_USERNAME = 'you@example.com'
SMTP_PASSWORD = 'your-password'
SMTP_USE_TLS = True

# Email sender/display
EMAIL_FROM = 'you@example.com'
DISPLAY_NAME = 'Audiobookshelf'

# Test mode defaults
DEFAULT_TEST_MODE = True
TEST_EMAIL_TO = 'you@example.com'

# Email subject
EMAIL_SUBJECT = 'Weekly AudioBook Update Report'

# === CONFIGURATION ===

SESSION = requests.Session()
SESSION.headers.update({
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/json',
})

def get_valid_user_emails():
    """Fetch all users and return list of valid email addresses."""
    url = f'{ABS_SERVER}/api/users'
    valid_emails = []
    email_regex = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
    try:
        response = SESSION.get(url, timeout=10)
        response.raise_for_status()
        users = response.json().get('users', [])
        print(f'\n== Users ({len(users)} total) ==')
        for user in users:
            username = user.get('username', 'Unknown')
            email = user.get('email', '')
            print(f'- Username: {username}, Email: {email}')
            if email and email_regex.match(email):
                valid_emails.append(email)
    except requests.RequestException as e:
        print(f'Error fetching users: {e}')
    return valid_emails

def get_library_id_by_name(library_name):
    """Fetch library ID for a given library name."""
    url = f'{ABS_SERVER}/api/libraries'
    try:
        response = SESSION.get(url, timeout=10)
        response.raise_for_status()
        libraries = response.json().get('libraries', [])
        for lib in libraries:
            if lib.get('name', '').lower() == library_name.lower():
                return lib.get('id')
        print(f'-- Library "{library_name}" not found.')
    except requests.RequestException as e:
        print(f'Error fetching libraries: {e}')
    return None

def get_books_added_in_past_days(library_id, days_back):
    """Fetch and print books added in the past N days. Returns list of (title, author, added_at_str)."""
    url = f'{ABS_SERVER}/api/libraries/{library_id}/items'
    page = 0
    limit = 100
    recent_books = []
    since_date = datetime.utcnow() - timedelta(days=days_back)

    while True:
        params = {'page': page, 'limit': limit}
        response = SESSION.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        items = data.get('results', [])
        if not items:
            break
        for book in items:
            added_at_raw = book.get('addedAt')
            if added_at_raw is None:
                continue
            try:
                if isinstance(added_at_raw, int):
                    added_at = datetime.utcfromtimestamp(added_at_raw / 1000)
                else:
                    added_at = datetime.fromisoformat(added_at_raw.replace('Z', '+00:00'))
            except Exception as e:
                print(f'Warning: Could not parse addedAt "{added_at_raw}": {e}')
                continue

            if added_at >= since_date:
                title = book.get('media', {}).get('metadata', {}).get('title', 'Unknown Title')
                author = book.get('media', {}).get('metadata', {}).get('authorName', 'Unknown Author')
                added_str = added_at.strftime('%Y-%m-%d')
                recent_books.append((title, author, added_str))
        page += 1

    print(f'\n== Books Added in the Past {days_back} Days ({len(recent_books)} total) ==')
    for title, author, added_at_str in recent_books:
        print(f'- "{title}" by {author}, added on {added_at_str}')

    return recent_books

def send_email_with_books(subject, body_text, books, from_addr, to_addrs, smtp_server, smtp_port, smtp_username, smtp_password, use_tls):
    """Send email with recent books list in HTML body."""
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f'{DISPLAY_NAME} <{from_addr}>'
    msg['To'] = ', '.join(to_addrs)

    plain_books_body = ''
    html_books_body = '<h2>Recent Books Added</h2><ul>'

    for title, author, added_at_str in books:
        plain_books_body += f'- "{title}" by {author}, added on {added_at_str}\n'
        html_books_body += f'<li><b><i>{title}</i></b> by {author}, added on {added_at_str}</li>'
    html_books_body += '</ul>'

    msg.set_content(body_text + '\n\n' + plain_books_body)
    msg.add_alternative(f"""\
    <html>
      <body>
        <p>{body_text}</p>
        {html_books_body}
      </body>
    </html>
    """, subtype='html')

    try:
        if use_tls:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)

        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        print(f'\nEmail sent to: {", ".join(to_addrs)}')
    except Exception as e:
        print(f'Error sending email: {e}')

def main():
    parser = argparse.ArgumentParser(description='Send ABS new books report.')
    parser.add_argument('--test', action='store_true', help='Enable test mode (send only to test address)')
    parser.add_argument('--days', type=int, default=DEFAULT_DAYS_BACK, help='Days back to check for new books')
    args = parser.parse_args()

    test_mode = args.test or DEFAULT_TEST_MODE
    days_back = args.days

    valid_user_emails = get_valid_user_emails()

    library_id = get_library_id_by_name(LIBRARY_NAME)
    if library_id:
        recent_books = get_books_added_in_past_days(library_id, days_back)

        if not recent_books:
            print('\nNo new books detected — no email will be sent.')
            return

        if test_mode:
            recipients = [TEST_EMAIL_TO]
            print(f'\nTEST MODE is ON. Email will only be sent to: {TEST_EMAIL_TO}')
        else:
            recipients = valid_user_emails
            print(f'\nProduction mode — Email will be sent to {len(recipients)} users.')

        if recipients:
            send_email_with_books(
                subject=EMAIL_SUBJECT,
                body_text=f'The following audiobooks have been added in the past {days_back} days:',
                books=recent_books,
                from_addr=EMAIL_FROM,
                to_addrs=recipients,
                smtp_server=SMTP_SERVER,
                smtp_port=SMTP_PORT,
                smtp_username=SMTP_USERNAME,
                smtp_password=SMTP_PASSWORD,
                use_tls=SMTP_USE_TLS
            )
        else:
            print('\nNo valid email recipients found — no email will be sent.')
    else:
        print('-- Cannot proceed without valid library ID.')

if __name__ == '__main__':
    main()
