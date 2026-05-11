"""
AI image generation tool: creates section images via DALL-E 3.
Input: .tmp/research.json (uses sections[].theme)
Output: .tmp/images/hero.png, image_01.png through image_04.png
Usage: python tools/create_ai_images.py [--section N  # regenerate only section N, 0=hero]
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

IMAGE_STYLE = (
    "editorial illustration, flat design, professional, modern, clean minimal color palette "
    "featuring indigo and purple tones, no text, no readable words, no human faces, wide landscape format"
)

COST_PER_IMAGE = 0.08


def build_prompt(theme: str, topic: str) -> str:
    return f"{theme}, in the context of {topic}. Style: {IMAGE_STYLE}"


def generate_and_save(prompt: str, out_path: Path) -> bool:
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1792x1024",
        quality="standard",
        n=1,
    )
    image_url = response.data[0].url
    img_data = requests.get(image_url, timeout=30).content
    out_path.write_bytes(img_data)
    print(f"  Saved: {out_path}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Generate newsletter images via DALL-E 3")
    parser.add_argument("--section", type=int, default=None,
                        help="Regenerate only this section index (0=hero, 1-4=sections). Omit for all.")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    research_path = Path(".tmp/research.json")
    if not research_path.exists():
        print("ERROR: .tmp/research.json not found. Run research.py first.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(research_path.read_text())
    topic = data.get("topic", "")
    sections = data.get("sections", [])

    images_dir = Path(".tmp/images")
    images_dir.mkdir(parents=True, exist_ok=True)

    # Build job list: (index, prompt, output_path)
    all_jobs = [
        (0, f"Abstract, inspiring visual representation of: {topic}", images_dir / "hero.png"),
    ] + [
        (i + 1, build_prompt(s.get("theme", s.get("title", topic)), topic), images_dir / f"image_{i + 1:02d}.png")
        for i, s in enumerate(sections[:4])
    ]

    jobs = [j for j in all_jobs if args.section is None or j[0] == args.section]

    if not jobs:
        print(f"ERROR: section {args.section} not found (valid: 0–{len(sections)})")
        sys.exit(1)

    total_cost = len(jobs) * COST_PER_IMAGE
    print(f"Generating {len(jobs)} image(s) via DALL-E 3  (~${total_cost:.2f})")

    image_paths = list(data.get("image_paths", [None] * 5))
    if len(image_paths) < 5:
        image_paths += [None] * (5 - len(image_paths))

    for idx, prompt, out_path in jobs:
        print(f"  [{idx}] {prompt[:80]}...")
        generate_and_save(prompt, out_path)
        image_paths[idx] = str(out_path)
        if idx < len(jobs) - 1:
            time.sleep(1)  # gentle rate limiting

    data["image_paths"] = [p for p in image_paths if p is not None]
    research_path.write_text(json.dumps(data, indent=2))
    print(f"Updated research.json with {len(data['image_paths'])} image path(s)")


if __name__ == "__main__":
    main()
