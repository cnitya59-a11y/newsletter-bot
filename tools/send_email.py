"""
Email sending tool: sends the newsletter as an HTML email to subscribers from a Google Sheet.
Input: .tmp/newsletter_copy.json (subject, newsletter_copy, articles)
Usage:
  python tools/send_email.py             # send to all subscribers
  python tools/send_email.py --dry-run   # save HTML preview, no send
  python tools/send_email.py --subject "Override subject"
"""

import argparse
import json
import os
import re
import smtplib
import ssl
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import certifi
import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

GMAIL_ADDRESS        = os.getenv("GMAIL_ADDRESS", "").strip()
GMAIL_APP_PASSWORD   = os.getenv("GMAIL_APP_PASSWORD", "").strip()
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")
SUBSCRIBERS_SHEET_ID = os.getenv("SUBSCRIBERS_SHEET_ID", "").strip()
SUBSCRIBERS_SHEET_NAME = os.getenv("SUBSCRIBERS_SHEET_NAME", "Sheet1")


def md_to_html(text: str) -> str:
    """Convert the subset of markdown used by the newsletter to HTML."""
    lines = text.splitlines()
    html_lines = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        is_bullet = stripped.startswith("* ") or stripped.startswith("- ")

        if is_bullet:
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            item = stripped[2:]
            item = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", item)
            html_lines.append(f"  <li>{item}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if not stripped:
                html_lines.append("")
            else:
                chunk = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
                html_lines.append(f"<p>{chunk}</p>")

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def build_html(subject: str, newsletter_copy: str, articles: list, recipient_name: str = "Friend") -> str:
    body_html = md_to_html(newsletter_copy)

    article_items = "\n".join(
        f'  <li><a href="{a.get("link","#")}">{a.get("title","")}</a>'
        f' <span class="source">— {a.get("source","")}</span></li>'
        for a in articles[:20]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{subject}</title>
<style>
  body {{ margin: 0; padding: 0; background: #f4f4f4; font-family: Georgia, serif; color: #222; }}
  .wrapper {{ max-width: 620px; margin: 32px auto; background: #fff; border-radius: 6px; overflow: hidden; }}
  .header {{ background: #111; padding: 28px 36px; }}
  .header h1 {{ margin: 0; color: #fff; font-size: 22px; font-weight: 700; line-height: 1.3; }}
  .header p  {{ margin: 6px 0 0; color: #aaa; font-size: 13px; }}
  .body {{ padding: 32px 36px; }}
  .body p  {{ font-size: 15px; line-height: 1.7; margin: 0 0 14px; }}
  .body ul {{ padding-left: 20px; margin: 0 0 14px; }}
  .body li {{ font-size: 15px; line-height: 1.7; margin-bottom: 6px; }}
  .body strong {{ color: #111; }}
  .divider {{ border: none; border-top: 1px solid #eee; margin: 28px 0; }}
  .sources h2 {{ font-size: 14px; text-transform: uppercase; letter-spacing: .06em; color: #888; margin: 0 0 12px; }}
  .sources ul {{ padding-left: 18px; margin: 0; }}
  .sources li {{ font-size: 13px; line-height: 1.6; margin-bottom: 4px; }}
  .sources a  {{ color: #555; text-decoration: none; }}
  .sources a:hover {{ text-decoration: underline; }}
  .source {{ color: #999; font-size: 12px; }}
  .footer {{ background: #f9f9f9; padding: 18px 36px; font-size: 12px; color: #aaa; text-align: center; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>{subject}</h1>
    <p>Hi {recipient_name} — here's your AI &amp; tech briefing.</p>
  </div>
  <div class="body">
    {body_html}
    <hr class="divider">
    <div class="sources">
      <h2>This week's sources</h2>
      <ul>
{article_items}
      </ul>
    </div>
  </div>
  <div class="footer">You're receiving this because you subscribed. Reply to unsubscribe.</div>
</div>
</body>
</html>"""


def fetch_recipients() -> list[dict]:
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_JSON, scopes=scopes)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(SUBSCRIBERS_SHEET_ID).worksheet(SUBSCRIBERS_SHEET_NAME)
    recipients = []
    for row in sheet.get_all_values()[1:]:
        if len(row) >= 2 and row[1].strip():
            recipients.append({"name": row[0].strip() or "Friend", "email": row[1].strip()})
    return recipients


def main():
    parser = argparse.ArgumentParser(description="Send newsletter via Gmail SMTP")
    parser.add_argument("--subject", default=None, help="Override email subject line")
    parser.add_argument("--dry-run", action="store_true", help="Save HTML preview, don't send")
    args = parser.parse_args()

    newsletter_path = Path(".tmp/newsletter_copy.json")
    if not newsletter_path.exists():
        print("ERROR: .tmp/newsletter_copy.json not found. Run write_newsletter.py first.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(newsletter_path.read_text())
    newsletter_copy = data["newsletter_copy"]
    subject = args.subject or data["subject"]
    articles = data["articles"]

    if args.dry_run:
        html = build_html(subject, newsletter_copy, articles, recipient_name="Preview Reader")
        preview = Path(".tmp/email_preview.html")
        preview.write_text(html)
        print(f"Dry run — preview saved: {preview}")
        print(f"Subject: {subject}")
        return

    for var in ["GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "SUBSCRIBERS_SHEET_ID"]:
        if not os.getenv(var, "").strip():
            print(f"ERROR: {var} not set in .env", file=sys.stderr)
            sys.exit(1)

    print("Fetching subscribers from Google Sheet...")
    recipients = fetch_recipients()
    if not recipients:
        print("No recipients found.")
        return
    print(f"Found {len(recipients)} subscriber(s)")

    ctx = ssl.create_default_context(cafile=certifi.where())
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)

        for i, r in enumerate(recipients, 1):
            html = build_html(subject, newsletter_copy, articles, recipient_name=r["name"])
            msg = MIMEMultipart("alternative")
            msg["From"]    = GMAIL_ADDRESS
            msg["To"]      = r["email"]
            msg["Subject"] = subject
            msg.attach(MIMEText(html, "html"))
            server.send_message(msg, from_addr=GMAIL_ADDRESS, to_addrs=[r["email"]])
            print(f"  [{i}/{len(recipients)}] Sent → {r['email']}")
            if i < len(recipients):
                time.sleep(0.5)

    print(f"\nDone. {len(recipients)} email(s) sent.")


if __name__ == "__main__":
    main()
