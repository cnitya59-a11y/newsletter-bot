"""
PDF rendering tool: assembles newsletter copy + images into a polished PDF.
Input: .tmp/research.json (must contain newsletter_copy, image_paths, chart_paths)
Output: .tmp/newsletter_[slug]_[date].pdf
Usage: python tools/render_pdf.py
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

TEMPLATE_DIR = Path(__file__).parent / "templates"


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50]


def resolve_images(paths: list[str]) -> list[str]:
    return [Path(p).resolve().as_uri() for p in paths if Path(p).exists()]


def main():
    research_path = Path(".tmp/research.json")
    if not research_path.exists():
        print("ERROR: .tmp/research.json not found.")
        sys.exit(1)

    data = json.loads(research_path.read_text())
    copy = data.get("newsletter_copy")

    if not copy:
        print("ERROR: newsletter_copy missing. Run write_newsletter.py first.")
        sys.exit(1)

    image_uris = resolve_images(data.get("image_paths", []))
    chart_uris = resolve_images(data.get("chart_paths", []))

    missing = (5 - len(image_uris))
    if missing > 0:
        print(f"Warning: {missing} image(s) missing from .tmp/images/ — placeholders will be used")

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("newsletter.html")

    html_content = template.render(
        topic=data["topic"],
        date=datetime.now().strftime("%B %d, %Y"),
        copy=copy,
        image_uris=image_uris,
        chart_uris=chart_uris,
        sources=data.get("sources", []),
        has_charts=bool(chart_uris),
    )

    slug = slugify(data["topic"])
    date_str = datetime.now().strftime("%Y%m%d")
    out_path = Path(f".tmp/newsletter_{slug}_{date_str}.pdf")

    print("Rendering PDF...")
    HTML(string=html_content).write_pdf(str(out_path))
    print(f"PDF saved: {out_path}")


if __name__ == "__main__":
    main()
