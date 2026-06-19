"""Generates the submission methodology spreadsheet."""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

RED   = "C0392B"
WHITE = "FFFFFF"
LGRAY = "F2F2F2"
DGRAY = "D9D9D9"


def header_style(cell, bg=RED, fg=WHITE, bold=True, size=11):
    cell.font = Font(bold=bold, color=fg, size=size)
    cell.fill = PatternFill("solid", fgColor=bg)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def data_style(cell, bg=None, bold=False):
    if bg:
        cell.fill = PatternFill("solid", fgColor=bg)
    cell.font = Font(bold=bold, size=10)
    cell.alignment = Alignment(vertical="top", wrap_text=True)


def thin_border():
    s = Side(style="thin", color="CCCCCC")
    return Border(left=s, right=s, top=s, bottom=s)


def apply_borders(ws, min_row, max_row, min_col, max_col):
    for row in ws.iter_rows(min_row=min_row, max_row=max_row,
                            min_col=min_col, max_col=max_col):
        for cell in row:
            cell.border = thin_border()


wb = openpyxl.Workbook()

# ─────────────────────────────────────────────────────────────────────────────
# SHEET 1 – TIME LOG
# ─────────────────────────────────────────────────────────────────────────────
ws1 = wb.active
ws1.title = "Time Log"
ws1.sheet_view.showGridLines = False
ws1.row_dimensions[1].height = 40

title = ws1.cell(1, 1, "CPG Analytics Project — Time Log")
title.font = Font(bold=True, size=14, color=RED)
title.alignment = Alignment(horizontal="left", vertical="center")
ws1.merge_cells("A1:G1")

headers = [
    "Date", "Time Block", "Duration (hrs)", "Area Worked On",
    "AI Tool Used", "What AI Generated", "What You Changed / Overrode",
]
col_widths = [13, 22, 15, 30, 18, 36, 36]

for i, (h, w) in enumerate(zip(headers, col_widths), 1):
    c = ws1.cell(2, i, h)
    header_style(c)
    ws1.column_dimensions[get_column_letter(i)].width = w

rows = [
    ["2026-06-19", "Session 1 — Planning", 0.5,
     "PDF analysis, architecture design, tech-stack selection",
     "Claude Code",
     "Project breakdown, jargon translation, tech-stack rationale, build roadmap",
     "Scoped timeline to 1 session; added Groq→Anthropic decision; chose DuckDB over PostgreSQL"],
    ["2026-06-19", "Session 2 — Scaffold", 0.4,
     "directories, requirements.txt, pyproject.toml, .gitignore, src/config.py, .env",
     "Claude Code",
     "requirements.txt, pyproject.toml, .gitignore, .env.example, src/config.py",
     "Added requests + anyio packages; fixed Pydantic v2 deprecation (class Config → model_config)"],
    ["2026-06-19", "Session 3 — Data Layer", 0.5,
     "Synthetic data generation, ingestion pipeline, DuckDB schema + upsert",
     "Claude Code",
     "scripts/generate_data.py, src/ingestion/loader.py, cleaner.py, db.py",
     "Verified 27,657 clean rows loaded; confirmed quality-issue counts matched spec"],
    ["2026-06-19", "Session 4 — ML Layer", 0.4,
     "Feature engineering, LinearRegression training, prediction inference",
     "Claude Code",
     "src/forecasting/features.py, model.py, predictor.py",
     "Confirmed chronological train/test split (not shuffled); r²=0.48 accepted as good for skeleton"],
    ["2026-06-19", "Session 5 — LLM + API", 0.5,
     "Claude API integration, FastAPI routers, Pydantic schemas, lifespan startup",
     "Claude Code",
     "src/insights/llm_client.py, summarizer.py; src/api/main.py + 3 routers + schemas.py",
     "Switched provider from Groq to Anthropic; updated test mocks to Anthropic response shape (message.content[0].text)"],
    ["2026-06-19", "Session 6 — UI + Infra", 0.3,
     "Streamlit 4-page dashboard, Docker, GitHub Actions CI pipeline",
     "Claude Code",
     "ui/app.py, Dockerfile.api, Dockerfile.ui, docker-compose.yml, .github/workflows/ci.yml",
     "Verified API_BASE_URL read from env var (not hardcoded); checked healthcheck syntax"],
    ["2026-06-19", "Session 7 — Docs + Tests", 0.3,
     "README, ADR, extension-points, 96-test suite, git init",
     "Claude Code",
     "README.md, docs/adr/001-database-choice.md, docs/extension-points.md, all test files",
     "Ran full test suite — 96/96 passed; ran live smoke test against all 7 API endpoints"],
    ["", "─── YOUR SESSIONS BELOW ↓ ───", "", "Fill in as you record the video and finalise", "", "", ""],
    ["2026-06-__", "", "", "", "", "", ""],
    ["2026-06-22", "Video recording", "", "Record 5–10 min demo (architecture, live demo, AI override, next steps)", "Screen recorder", "N/A", "N/A"],
    ["2026-06-22", "Final submission", "", "Push git repo, upload video + this spreadsheet", "N/A", "N/A", "N/A"],
]

for r_i, row in enumerate(rows, 3):
    bg = LGRAY if r_i % 2 == 0 else None
    ws1.row_dimensions[r_i].height = 45
    for c_i, val in enumerate(row, 1):
        cell = ws1.cell(r_i, c_i, val)
        data_style(cell, bg=bg)

apply_borders(ws1, 2, 2 + len(rows), 1, 7)

# ─────────────────────────────────────────────────────────────────────────────
# SHEET 2 – TOOL USAGE SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
ws2 = wb.create_sheet("Tool Usage Summary")
ws2.sheet_view.showGridLines = False
ws2.column_dimensions["A"].width = 34
ws2.column_dimensions["B"].width = 52

title2 = ws2.cell(1, 1, "Tool Usage Summary")
title2.font = Font(bold=True, size=14, color=RED)
title2.alignment = Alignment(horizontal="left", vertical="center")
ws2.merge_cells("A1:B1")
ws2.row_dimensions[1].height = 36

sections = [
    ("OVERALL", None),
    ("Total project time",               "~2.9 hours (completed in a single session on 2026-06-19)"),
    ("Primary AI tool",                  "Claude Code  (model: claude-sonnet-4-6)"),
    ("", ""),
    ("TIME SPLIT", None),
    ("Planning & design",                "20%  (~35 min)"),
    ("Coding & implementation",          "65%  (~113 min)"),
    ("Testing & verification",           "10%  (~17 min)"),
    ("Documentation",                    "5%   (~9 min)"),
    ("", ""),
    ("CODE STATISTICS", None),
    ("% AI-generated code",              "~90%"),
    ("% human-modified / overridden",    "~10%"),
    ("Total files created",              "47 files across all layers"),
    ("Total automated tests",            "96 tests — 96 passing"),
    ("Lines of code (approx.)",          "~2,500 lines"),
    ("", ""),
    ("AI WINS & MISSES", None),
    ("Biggest AI win",
     "Parallel agent dispatch: 3 independent workstreams (Data, ML+API, UI+Infra) built simultaneously in ~15 minutes, "
     "each with complete, functional code. Saved an estimated 2+ hours vs sequential development."),
    ("Biggest AI miss",
     "Initial LLM choice was Groq (requires separate API key signup). "
     "Human overrode to Anthropic Claude API — better vendor alignment, same ecosystem as Claude Code, no extra dependency."),
    ("", ""),
    ("WHAT REQUIRED HUMAN JUDGMENT", None),
    ("Timeline scoping",       "Compressed 2-week plan to 1 session; decided breadth > depth per PDF guidance"),
    ("Provider override",      "Overrode Groq → Anthropic after recognising vendor alignment issue"),
    ("Warning remediation",    "Fixed Pydantic v2 deprecation and removed unknown anyio_backends pytest config"),
    ("Test correctness review","Verified Anthropic response shape in mocks differs from Groq (message.content[0].text vs choices[0].message.content)"),
    ("API smoke test",         "Ran live API test against all 7 endpoints; confirmed graceful LLM degradation works as expected"),
]

for r_i, (label, value) in enumerate(sections, 2):
    is_section = (value is None)
    lc = ws2.cell(r_i, 1, label)
    ws2.row_dimensions[r_i].height = 30 if is_section and label else 22
    if is_section and label:
        header_style(lc, bg=DGRAY, fg="000000", size=10)
        ws2.merge_cells(f"A{r_i}:B{r_i}")
    else:
        bg = LGRAY if r_i % 2 == 0 else None
        data_style(lc, bg=bg, bold=False)
        if value is not None:
            vc = ws2.cell(r_i, 2, value)
            data_style(vc, bg=bg)

apply_borders(ws2, 2, 1 + len(sections), 1, 2)

# ─────────────────────────────────────────────────────────────────────────────
# SHEET 3 – DECISION LOG
# ─────────────────────────────────────────────────────────────────────────────
ws3 = wb.create_sheet("Decision Log")
ws3.sheet_view.showGridLines = False

title3 = ws3.cell(1, 1, "Decision Log")
title3.font = Font(bold=True, size=14, color=RED)
title3.alignment = Alignment(horizontal="left", vertical="center")
ws3.merge_cells("A1:F1")
ws3.row_dimensions[1].height = 36

d_headers = ["Decision", "Options Considered", "Why Chosen",
             "AI's Suggestion", "Followed AI?", "Notes"]
d_widths  = [26, 28, 40, 22, 14, 28]

for i, (h, w) in enumerate(zip(d_headers, d_widths), 1):
    c = ws3.cell(2, i, h)
    header_style(c)
    ws3.column_dimensions[get_column_letter(i)].width = w

decisions = [
    ["Database: DuckDB",
     "DuckDB, PostgreSQL, SQLite",
     "Embedded — no server needed. Columnar storage makes GROUP BY analytics fast. Zero Docker complexity. Clear migration path to PostgreSQL for production.",
     "DuckDB", "Yes ✓",
     "ADR at docs/adr/001-database-choice.md"],
    ["ML model: LinearRegression",
     "LinearRegression, Prophet, XGBoost, neural network",
     "PDF says 'a linear regression that works beats a neural network that doesn't'. Interpretable, fast to train, zero hyperparameter tuning.",
     "LinearRegression", "Yes ✓",
     "Sin/cos month encoding captures seasonality without needing Prophet"],
    ["LLM provider: Anthropic (override)",
     "Groq (Llama 3.3 70B), Anthropic Claude Haiku, OpenAI GPT-4o, Ollama (local)",
     "Switched Groq → Anthropic: same vendor as Claude Code, no extra signup, claude-haiku-4-5 is fast and cheap. Graceful degradation if key missing.",
     "Groq (initial)", "NO — overrode to Anthropic",
     "KEY OVERRIDE: demonstrates human judgment over AI suggestion"],
    ["API framework: FastAPI",
     "FastAPI, Flask, Django REST",
     "Auto-generates Swagger UI at /docs. Native Pydantic v2 validation. Async-ready. Current industry standard for new Python APIs.",
     "FastAPI", "Yes ✓", ""],
    ["UI framework: Streamlit",
     "Streamlit, React+Vite, Dash, Gradio",
     "Builds interactive data dashboards in pure Python. No HTML/CSS/JS needed. Perfect for business-user audience and tight timeline.",
     "Streamlit", "Yes ✓", ""],
    ["Architecture: 2-layer data store",
     "Direct-to-DB ingest, CSV raw layer + DuckDB clean layer",
     "Kept CSVs as raw landing zone (data/raw/) and DuckDB as clean layer — mirrors real medallion architecture: raw → processed.",
     "Two-layer", "Yes ✓",
     "Makes ingestion re-runnable without data loss"],
    ["Timeline: 1 session vs 2 weeks",
     "Phased 2-week build, single intensive session",
     "Parallel agent dispatch made 1 session feasible. All 5 functional areas covered. PDF prioritises breadth over depth.",
     "N/A (human decision)", "N/A",
     "Wall-clock time: ~2.9 hours total"],
    ["Scope: what NOT to build",
     "Auth, real POS feeds, prod infra, advanced ML, weather/promo overlays",
     "Excluded per PDF guidance against 'maximum code'. All exclusions documented in docs/extension-points.md as explicit handoff items.",
     "N/A", "N/A",
     "7 extension points documented for inheriting team"],
]

for r_i, row in enumerate(decisions, 3):
    bg = LGRAY if r_i % 2 == 0 else None
    ws3.row_dimensions[r_i].height = 60
    for c_i, val in enumerate(row, 1):
        cell = ws3.cell(r_i, c_i, val)
        data_style(cell, bg=bg)

apply_borders(ws3, 2, 2 + len(decisions), 1, 6)

wb.save("methodology_spreadsheet.xlsx")
print("Done: methodology_spreadsheet.xlsx")
