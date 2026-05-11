"""
Chart generation tool: creates matplotlib charts from research stats.
Input: .tmp/research.json
Output: .tmp/charts/chart_01.png, chart_02.png
Usage: python tools/create_charts.py
"""

import json
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt

BRAND_COLORS = ["#4F46E5", "#7C3AED", "#2563EB", "#0891B2", "#059669", "#D97706"]
BG_COLOR = "#FFFFFF"
TEXT_COLOR = "#1F2937"
SUBTITLE_COLOR = "#6B7280"


def extract_numeric_stats(stats: list[dict]) -> list[dict]:
    numeric = []
    for s in stats:
        text = s.get("stat", "")
        matches = re.findall(r"(\d+(?:\.\d+)?)\s*(%|billion|million|trillion|x\b|\bfold\b)?", text)
        if matches:
            value = float(matches[0][0])
            unit = matches[0][1] or ""
            label = text[:55] + ("…" if len(text) > 55 else "")
            numeric.append({
                "label": label,
                "value": value,
                "unit": unit,
                "source": s.get("source", ""),
            })
    return numeric[:6]


def make_bar_chart(stats: list[dict], title: str, out_path: Path):
    fig, ax = plt.subplots(figsize=(11, 5))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    labels = [s["label"] for s in stats]
    values = [s["value"] for s in stats]
    colors = BRAND_COLORS[:len(stats)]

    bars = ax.barh(labels, values, color=colors, height=0.55)

    max_val = max(values) if values else 1
    for bar, stat in zip(bars, stats):
        ax.text(
            bar.get_width() + max_val * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{stat['value']:g}{stat['unit']}",
            va="center",
            color=TEXT_COLOR,
            fontsize=10,
            fontweight="bold",
        )

    ax.set_title(title, fontsize=13, fontweight="bold", color=TEXT_COLOR, pad=12, loc="left")
    ax.tick_params(colors=TEXT_COLOR, labelsize=9)
    ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
    ax.xaxis.set_visible(False)
    ax.set_xlim(0, max_val * 1.25)

    plt.tight_layout(pad=1.5)
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG_COLOR)
    plt.close()
    print(f"Saved: {out_path}")


def main():
    research_path = Path(".tmp/research.json")
    if not research_path.exists():
        print("ERROR: .tmp/research.json not found. Run research.py first.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(research_path.read_text())
    stats = extract_numeric_stats(data.get("key_stats", []))

    if not stats:
        print("No numeric stats found — skipping chart generation.")
        return

    charts_dir = Path(".tmp/charts")
    charts_dir.mkdir(parents=True, exist_ok=True)

    topic = data.get("topic", "")
    chart_paths = []

    if len(stats) >= 2:
        path = charts_dir / "chart_01.png"
        make_bar_chart(stats[:4], f"Key Numbers: {topic}", path)
        chart_paths.append(str(path))

    if len(stats) >= 5:
        path = charts_dir / "chart_02.png"
        make_bar_chart(stats[3:], f"More Data: {topic}", path)
        chart_paths.append(str(path))

    data["chart_paths"] = chart_paths
    research_path.write_text(json.dumps(data, indent=2))
    print(f"Updated research.json with {len(chart_paths)} chart(s)")


if __name__ == "__main__":
    main()
