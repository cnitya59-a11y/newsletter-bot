#!/usr/bin/env python3
"""
setup_cron.py — Sets up a daily cron job to send the newsletter
Run once: python3 setup_cron.py
"""

import os
import subprocess
from pathlib import Path

# Get absolute path to project
PROJECT_DIR = Path(__file__).parent.resolve()
PYTHON = subprocess.check_output(["which", "python3"]).decode().strip()
SCRIPT = PROJECT_DIR / "run_pipeline.py"
LOG = PROJECT_DIR / ".tmp" / "newsletter.log"

# Daily at 8:00 AM
CRON_TIME = "0 8 * * *"
CRON_JOB = f'{CRON_TIME} cd {PROJECT_DIR} && {PYTHON} {SCRIPT} >> {LOG} 2>&1'

def main():
    # Read existing crontab
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ""

    if str(SCRIPT) in existing:
        print("✅ Cron job already exists!")
        print(f"   Runs daily at 8:00 AM")
        return

    # Add new job
    new_crontab = existing.rstrip() + f"\n{CRON_JOB}\n"
    proc = subprocess.run(["crontab", "-"], input=new_crontab, text=True)

    if proc.returncode == 0:
        print("✅ Cron job set up successfully!")
        print(f"   Schedule: Every day at 8:00 AM")
        print(f"   Project:  {PROJECT_DIR}")
        print(f"   Log file: {LOG}")
        print(f"\n   To remove it later: crontab -e")
    else:
        print("❌ Failed to set up cron job")


if __name__ == "__main__":
    main()
