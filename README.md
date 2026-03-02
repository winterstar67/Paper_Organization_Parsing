# Paper Organization Parsing

Local pipeline for extracting author organizations from arXiv paper metadata/HTML/PDF and sending filtered results by Gmail API.

## Overview

This project processes a user-provided paper pool (no direct crawling phase in the current flow), then:

1. Normalizes input paper data
2. Extracts author/organization raw text from HTML
3. Parses organizations with filtering rules
4. Integrates HTML/PDF organization results
5. Generates abstract summaries
6. Sends filtered report email via Gmail API

Main runner: `src/integrated.py`

## Project Structure

- `src/`: pipeline scripts
- `input/`: input paper pool and source files
- `results/`: phase outputs
- `env_example.txt`: environment variable template

## Requirements

- Python 3.x
- Dependencies in `requirements.txt`

Install:

```bash
pip install -r requirements.txt
```

## Environment Setup

Create `.env` from `env_example.txt` and set values:

- `OPENAI_API_KEY`
- `RECIPIENT_EMAIL`
- `TARGET_ORGANIZATIONS`
- `KNOWN_ORGANIZATIONS`
- `EMAIL_PATTERNS`
- `LLM_MODEL_BLACKLIST`
- Optional: `PAPER_POOL_PATH`, `BROWSER_PATH`

## Input Data

This repository uses **CSV only** as input paper pool format.

Required input file:

- `input/paper_pool.csv` (or a custom CSV path via `PAPER_POOL_PATH`)

Important requirement:

- For each paper row, the designated local path for HTML or PDF must point to a file that actually exists.
- Relative paths are resolved from project root.
- If neither valid local HTML nor valid local PDF exists for a row, that row cannot be processed.

Recommended CSV columns:

- `Title` (required)
- `Authors`
- `Abstract`
- `Submitted`
- `html_path` (local HTML file path)
- `pdf_path` (local PDF file path)

Alias columns can be normalized by Phase 1, but keeping the standard names above is recommended.

### CSV Example

```csv
Title,Authors,Abstract,Submitted,html_path,pdf_path
"Sample Paper A","Alice; Bob","...",2026-03-01,input/sources/Yes_organ_1.html,input/sources/Yes_organ_3.pdf
"Sample Paper B","Charlie","...",2026-03-01,input/sources/No_organ_1.html,input/sources/No_organ_2.pdf
```

### Path Rules

- `html_path` and `pdf_path` can be absolute or relative.
- Relative example: `input/sources/Yes_organ_1.html`
- Absolute example: `/mnt/c/.../input/sources/Yes_organ_1.html`
- Remote URLs are not used as source files in this local pipeline mode.

## Gmail API Setup

1. Enable **Gmail API** in Google Cloud Console.
2. Create OAuth 2.0 Client ID as **Desktop App**.
3. Download credentials JSON and place it at `src/credentials.json`.
4. First run will create `src/token.json` after OAuth consent.

## Run

```bash
cd src
python integrated.py
```

Optional (Phase 1 only):

```bash
cd src
python 1_input_pool_prepare.py --input ../input/paper_pool.csv
```

## Notes

- Results are written under `results/`.
- Current pipeline uses local input normalization as Phase 1.
