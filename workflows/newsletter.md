# Newsletter Generation Workflow

## Objective
Generate a research-backed, visually polished PDF newsletter on any given topic, complete with data charts and AI-generated illustrations.

## Inputs
| Input | Required | Default | Notes |
|---|---|---|---|
| `topic` | Yes | — | The newsletter subject (e.g. "AI agents in 2026") |
| `keywords` | No | — | Comma-separated focus terms to steer research |
| `tone` | No | professional | professional / casual / educational |
| `audience` | No | general audience | Shapes vocabulary and depth of copy |

## Tools
| Step | Script | Input | Output |
|---|---|---|---|
| Research | `tools/research.py` | topic, keywords | `.tmp/research.json` |
| Write copy | `tools/write_newsletter.py` | `.tmp/research.json` | updates `research.json` |
| Charts | `tools/create_charts.py` | `.tmp/research.json` | `.tmp/charts/*.png` |
| AI Images | `tools/create_ai_images.py` | `.tmp/research.json` | `.tmp/images/*.png` |
| Render PDF | `tools/render_pdf.py` | `.tmp/research.json` + assets | `.tmp/newsletter_[slug]_[date].pdf` |
| Send email | `tools/send_email.py` | `.tmp/research.json` + Google Sheet | emails sent via Gmail SMTP |

## Step-by-Step

### Step 1: Research
```bash
python tools/research.py --topic "YOUR TOPIC" --keywords "optional,keywords"
```
Calls the Perplexity API (`sonar` model) with a structured prompt that extracts:
- A 200–300 word summary
- 5–8 key statistics with sources
- 3–5 expert quotes
- 4 section themes (used later for image generation)
- 4–6 source URLs

Output saved to `.tmp/research.json`.

**If Perplexity fails:** Check `PERPLEXITY_API_KEY` is set in `.env`. If rate-limited, wait 60s and retry once.

---

### Step 2: Write Newsletter Copy
```bash
python tools/write_newsletter.py --tone professional --audience "tech founders"
```
Reads `research.json`, calls Claude API to produce:
- Title + subtitle
- 3-sentence executive summary
- 4 sections (150–200 words each) with pull quotes
- Closing paragraph
- Image captions for each visual

Updates `research.json` with `newsletter_copy` key.

---

### Step 3: Create Charts
```bash
python tools/create_charts.py
```
Reads stats from `research.json`. Extracts numerical values via regex. Generates 1–2 horizontal bar charts using matplotlib.

- Saved to `.tmp/charts/chart_01.png` and `chart_02.png`
- Style: clean white background, `#4F46E5` accent color
- Updates `research.json` with `chart_paths`

**If no numeric stats found:** The script prints a notice and skips gracefully. The PDF will render without a charts page.

---

### Step 4: Create AI Images
```bash
python tools/create_ai_images.py
```
Generates 5 images via DALL-E 3 (`1792x1024`, standard quality):
- 1 hero image for the cover
- 1 image per section (4 total), styled as editorial flat illustrations

**Cost notice:** ~$0.08/image × 5 = ~$0.40 per run. Script prints this before running. Check with user if budget is a concern.

Images downloaded immediately to `.tmp/images/` (DALL-E URLs expire in ~1 hour).

---

### Step 5: Render PDF
```bash
python tools/render_pdf.py
```
Loads `research.json`, injects all content into `tools/templates/newsletter.html` via Jinja2, renders to PDF using WeasyPrint.

Output: `.tmp/newsletter_[slug]_[date].pdf`

Open the PDF and review before sharing.

---

### Step 6: Review & Iterate
After opening the PDF:
- **Copy edits:** Update `research.json` → `newsletter_copy` → rerun `render_pdf.py`
- **Regenerate one image:** Delete the specific `.tmp/images/image_0X.png`, rerun `create_ai_images.py` with `--section 2` flag (regenerates only that section)
- **Regenerate charts:** Rerun `create_charts.py`
- **Full re-render:** Rerun only `render_pdf.py` after any asset change

---

### Step 7: Send Email
Once you're happy with the PDF:

```bash
# Preview first — saves .tmp/email_preview.html, no send
python tools/send_email.py --dry-run

# Send to all subscribers
python tools/send_email.py

# Override the subject line
python tools/send_email.py --subject "This week: AI agents are taking over"
```

The tool:
1. Fetches subscriber list (Name, Email) from your Google Sheet
2. Resizes all AI images to 600px wide JPEG for email
3. Renders the full newsletter as HTML email with inline embedded images
4. Sends individually to each subscriber via Gmail SMTP

**One-time setup required:**
- Create a Google Cloud service account, download the JSON key, save as `credentials.json`
- Share your subscriber Google Sheet with the service account email address
- Enable a Gmail App Password: myaccount.google.com → Security → 2-Step Verification → App passwords
- Fill in `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `SUBSCRIBERS_SHEET_ID` in `.env`

**Google Sheet format:**
| Row | Column A | Column B |
|---|---|---|
| 1 | Name *(header)* | Email *(header)* |
| 2 | Jane Smith | jane@example.com |

**Gmail limits:** Free Gmail: 500 emails/day. Google Workspace: 2,000/day. Script adds 0.5s delay between sends automatically.

---

## Full Pipeline (one-liner sequence)
```bash
python tools/research.py --topic "AI agents in 2026" --keywords "automation,LLMs" && \
python tools/write_newsletter.py --tone professional --audience "tech founders" && \
python tools/create_charts.py && \
python tools/create_ai_images.py && \
python tools/render_pdf.py
# → review .tmp/newsletter_*.pdf, then:
python tools/send_email.py --dry-run   # check preview
python tools/send_email.py             # send
```

## Expected Output
A polished PDF newsletter (~6–8 pages):
- Cover page — hero AI image, title, subtitle, date
- Executive summary page with standout pull quote
- 4 content pages — AI image + body copy + pull quote per section
- Charts page — 1–2 data visualizations with captions
- Sources page

## Required API Keys (in `.env`)
```
PERPLEXITY_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
```

## Error Reference
| Error | Action |
|---|---|
| Perplexity rate limit | Wait 60s, retry once |
| No numeric stats in research | Skip chart step, note in output |
| DALL-E content policy block | Rephrase image prompt (remove flagged terms), retry |
| WeasyPrint rendering failure | Check all image paths in `.tmp/` exist; run `brew install pango` if missing system deps |
| Claude JSON parse error | Rerun `write_newsletter.py` — LLM output occasionally has trailing commas |
| Gmail auth error | Confirm App Password is set (not regular password); check 2FA is enabled on Google account |
| Google Sheet permission denied | Share the sheet with the service account email from `credentials.json` |
| No recipients found | Check sheet has a header row + data in column A (Name) and column B (Email) |

## System Requirements
```bash
pip install -r tools/requirements.txt
brew install pango  # macOS — required by WeasyPrint
```

## Known Constraints
- Perplexity `sonar` is used for cost efficiency; swap to `sonar-pro` in `research.py` for higher citation quality
- DALL-E 3 images must be downloaded within ~1 hour of generation — `create_ai_images.py` does this automatically
- WeasyPrint requires `pango` system library — install once per machine
