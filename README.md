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

Phase 1 expects a paper pool file. Supported formats:

- `.csv`
- `.tsv`
- `.xlsx`
- `.json`

Default path:

- `input/paper_pool.csv`

Override with:

- `.env`: `PAPER_POOL_PATH=...`
- or CLI input option in `1_input_pool_prepare.py`

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

## Notes

- Results are written under `results/`.
- Current pipeline uses local input normalization as Phase 1.
