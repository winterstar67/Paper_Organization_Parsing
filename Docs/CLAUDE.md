# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **arXiv Paper Metadata Collector** that automatically collects and processes AI/ML research papers from arXiv. The system operates as a 5-phase pipeline that can be run individually or through the integrated pipeline script.

**Code Quality**: All functions across the project include comprehensive type annotations and detailed documentation with input/output examples (updated 2025-08-30).

## Project Structure

```
3_Paper_collect_and_extract_organization_of_paper/
├── src/                              # Main source code directory
│   ├── 1_URLs of Paper Abstract Page.py  # Phase 1: arXiv search & metadata collection  
│   ├── 2_html_raw_text.py                # Phase 2: HTML author info extraction
│   ├── 3_parsing_meta_data.py            # Phase 3: AI-based organization parsing
│   ├── 4_organ_integrate.py              # Phase 4: Organization data integration
│   ├── 5_gmail_sending.py               # Phase 5: Email notifications
│   ├── integrated.py                     # Main pipeline orchestrator
│   ├── credentials.json                  # Gmail API credentials
│   └── token.json                        # Gmail API token
├── results/                          # Processing results and data files
│   ├── 1_URL_of_paper_abstractions.csv  # Main paper metadata
│   ├── 2_html_raw_text.csv              # HTML author information
│   ├── 2_2_failed_papers.csv            # Failed HTML extractions
│   ├── 3_parsing_meta_data.csv          # AI-extracted organizations
│   ├── 3_parsing_meta_data_processing.csv # Processing intermediate file
│   ├── 4_organ_integrate.csv            # Final integrated data
│   └── html_raw_text.* (p/txt)          # Multiple format exports
├── backup/                           # Automated date-range based backups
│   ├── 1_URL_of_paper_abstractions/     # Phase 1 backups (StartDate_EndDate format)
│   ├── 2_html_raw_text/                 # Phase 2 backups (StartDate_EndDate format)
│   ├── 3_parsing_meta_data/             # Phase 3 backups (StartDate_EndDate format)
│   └── 4_organ_integrate/               # Phase 4 backups (StartDate_EndDate format)
├── Example_files/                    # Sample HTML structure documentation
├── Docs/                             # Project documentation
│   ├── CLAUDE.md                        # This file
│   ├── Project_Overview.md              # Korean project overview
│   └── Work_state.md                    # Development progress log
└── .env                              # Environment variables (create manually)
```

## Running the System

### Full Integrated Pipeline (Recommended)
```bash
cd src/
python integrated.py
```
This runs all phases sequentially with detailed logging, handles Windows encoding issues, and includes comprehensive error handling.

### Individual Phase Execution
```bash
cd src/

# Phase 1: Collect paper URLs and basic metadata
python "1_URLs of Paper Abstract Page.py"

# Phase 2: Extract HTML author information (~21 minutes for 243 papers)  
python "2_html_raw_text.py"

# Phase 3: Extract organizations using AI (requires OpenAI API key)
python "3_parsing_meta_data.py"

# Phase 4: Integrate and normalize organization data
python "4_organ_integrate.py"  

# Phase 5: Send email notifications
python "5_gmail_sending.py"
```

## Required Dependencies

Install Python packages:
```bash
pip install requests beautifulsoup4 pandas pytz openai python-dotenv
# For Gmail functionality:
pip install google-auth google-auth-oauthlib google-api-python-client
```

## Environment Configuration

Create `.env` file in the root directory:
```env
# Required for Phase 3 AI processing
OPENAI_API_KEY=your_openai_api_key
GPT_MODEL=gpt-3.5-turbo

# Organization filtering (JSON format)
KNOWN_ORGANIZATIONS=["Google", "Microsoft", "OpenAI", "Stanford University"]
TARGET_ORGANIZATIONS=["Google", "Microsoft"]

# Gmail configuration (optional)
GMAIL_USER=your_email@gmail.com
GMAIL_PASSWORD=your_app_password
```

## Data Flow Pipeline

```
arXiv Search → Phase 1 → results/1_URL_of_paper_abstractions.csv
              ↓
Individual HTML Pages → Phase 2 → results/2_html_raw_text.csv
                       ↓  
AI Processing → Phase 3 → results/3_parsing_meta_data.csv
              ↓
Integration → Phase 4 → results/4_organ_integrate.csv
            ↓
Email Notifications → Phase 5
```

### Key Result Files
- `results/1_URL_of_paper_abstractions.csv`: Basic paper metadata (title, authors, dates, subjects)
- `results/2_html_raw_text.csv`: Raw HTML author sections with detailed information
- `results/3_parsing_meta_data.csv`: AI-extracted organization data with token usage tracking
- `results/4_organ_integrate.csv`: Final integrated data with normalized organizations
- `results/2_2_failed_papers.csv`: Papers that failed HTML extraction for retry

## Processing Configuration

### Data Collection Strategy
- **Target subjects**: cs.AI, cs.LG, cs.CL, cs.CV (AI/ML focus)
- **Date range**: Yesterday 00:00 to current time (US Eastern timezone)
- **Rate limiting**: 10-second delays every 20 requests (Phase 1), 5.2-second delays (Phase 2)

### Windows Encoding Compatibility
- All scripts handle CP949 encoding issues with ASCII alternatives
- UTF-8 with BOM (`utf-8-sig`) for CSV outputs
- Comprehensive Windows path handling

### Code Quality Standards
- **Type Annotations**: All functions include comprehensive type hints using `typing` module
- **Documentation**: Detailed docstrings with function descriptions, input/output examples, and usage examples
- **Consistent Format**: Standardized documentation format across all 5 phases
- **Error Handling**: Proper exception handling with informative error messages

### AI Processing (Phase 3)
- Uses OpenAI GPT-3.5-turbo API for organization extraction
- Processes in batches of 10 with intermediate saves
- Tracks input/output tokens for cost monitoring
- Automatic retry for failed extractions

## Important Processing Notes

### Automated Operation Features
- `integrated.py` automatically selects optimal processing modes
- Comprehensive logging with timestamps and execution times
- Automatic backup generation with date-range naming (StartDate[YYMMDD]_EndDate[YYMMDD])
- Progress tracking with intermediate save files

### Quality Assurance
- Verify result files are non-empty after each phase
- Check `backup/` directories for automatic backups
- Monitor processing logs for encoding errors or network failures
- Use processing CSV files for intermediate progress checking

### Performance Optimization
- Phase 1: 20 requests with 10-second delays every 20 requests
- Phase 2: 5.2-second delays between HTML requests (~21 minutes for 243 papers)
- Phase 3: Processes in batches of 10 with intermediate saves
- All phases include comprehensive progress reporting

## Special Features

### Research Career Tracking
The system is designed to track researchers who have moved between academia and industry, particularly identifying those with Big Tech experience (Google, Microsoft, Meta, Amazon, Apple) even if they've since moved to universities or startups.

### Multi-format Data Storage
Phase 2 saves data in multiple formats:
- CSV for structured analysis
- Pickle files for Python object preservation  
- TXT files for human-readable inspection
- Filtered variants for different processing needs

### Email Notification System
- Gmail API integration for comprehensive reporting with date-range based subjects
- Complete organization list display (all discovered organizations, alphabetically sorted)
- Paper publication date range information in email body
- Customizable organization targeting via environment variables

## Testing and Development

### Running Tests
Currently, the project uses manual testing by running each phase and verifying outputs. Check:
- Non-empty result files after each phase
- Backup file generation
- Processing log completeness
- Data consistency across different formats

### Error Handling
- Network request failures with automatic retry
- API rate limit handling
- File encoding error recovery
- Missing dependency detection
- Gmail authentication error handling

## Git Workflow

The project uses standard Git workflow with automatic commits generated by the integrated pipeline. Current working directory structure has been reorganized with all Python scripts moved to `src/` directory for better organization.

## Performance Monitoring

Track the following metrics:
- Papers processed per hour
- API token usage and costs (Phase 3)
- Success rates for each phase
- Network request failure rates
- Processing time for each phase