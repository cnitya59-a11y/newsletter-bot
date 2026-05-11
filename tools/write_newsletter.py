import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

if not GROQ_API_KEY:
    print("ERROR: GROQ_API_KEY not set in .env", file=sys.stderr)
    sys.exit(1)

research_path = Path(".tmp/research.json")
if not research_path.exists():
    print("ERROR: .tmp/research.json not found. Run research.py first.", file=sys.stderr)
    sys.exit(1)

articles = json.loads(research_path.read_text())["articles"]

articles_text = "\n".join(
    f"- [{a['source']}] {a['title']}: {a['description'][:200]}"
    for a in articles[:30]
)

PROMPT = f"""You are a newsletter writer. Based on these recent AI and tech news articles, write an engaging bullet-point newsletter.

Articles:
{articles_text}

Format your response like this:
SUBJECT: <compelling email subject line, max 10 words>

<Full newsletter as markdown. Start with a 2-sentence intro, then bullet points grouped under bold headers like **AI**, **Tech**, **Business**. 300-400 words total.>"""

print("Generating newsletter via Groq...")
resp = requests.post(
    GROQ_URL,
    headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
    json={"model": MODEL, "messages": [{"role": "user", "content": PROMPT}], "temperature": 0.7},
    timeout=30,
)
resp.raise_for_status()

raw_text = resp.json()["choices"][0]["message"]["content"].strip()

# Extract subject from first line, treat rest as newsletter body
lines = raw_text.splitlines()
subject = ""
body_start = 0
for i, line in enumerate(lines):
    clean = line.strip().strip("*").strip()
    if clean.upper().startswith("SUBJECT:"):
        subject = clean.split(":", 1)[1].strip().strip("*").strip()
        body_start = i + 1
        break

newsletter_copy = "\n".join(lines[body_start:]).strip()
if not subject:
    subject = "Your Weekly AI & Tech Newsletter"

out = {
    "subject": subject,
    "newsletter_copy": newsletter_copy,
    "articles": articles,
    "generated_at": datetime.now().isoformat(),
}

Path(".tmp/newsletter_copy.json").write_text(json.dumps(out, indent=2))
print(f'Subject: {out["subject"]}')
print(f"Saved to .tmp/newsletter_copy.json  ({len(articles)} articles)")
