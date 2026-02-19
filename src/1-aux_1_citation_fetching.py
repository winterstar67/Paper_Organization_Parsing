"""Fetch citation counts after Phase 1 using OpenAlex, fallback to Semantic Scholar."""

import os
import re
import time
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import requests
from pipeline_config import results_dir, backup_dir

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
PAR_DIR = os.path.dirname(CUR_DIR)

PHASE1_CSV_PATH = os.path.join(results_dir("Phase_1"), "1_URL_of_paper_abstractions.csv")
RESULT_CSV_PATH = os.path.join(results_dir("Phase_1-aux_1"), "1-aux_1_citation_results.csv")
BACKUP_DIR = backup_dir("Phase_1-aux_1")
PHASE1_BACKUP_DIR = backup_dir("Phase_1")

OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY", "").strip()
OPENALEX_MAILTO = os.getenv("OPENALEX_MAILTO", "").strip()
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "").strip()

REQUEST_TIMEOUT = 20
SLEEP_BETWEEN_REQUESTS = float(os.getenv("CITATION_SLEEP_SEC", "0.1"))
TITLE_MATCH_THRESHOLD = float(os.getenv("CITATION_TITLE_MATCH_THRESHOLD", "0.90"))


def normalize_title(title: str) -> str:
    title = title or ""
    title = title.lower()
    title = re.sub(r"[^a-z0-9\s]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def best_title_match(target_title: str, candidates: list[dict]) -> Optional[dict]:
    target_norm = normalize_title(target_title)
    if not target_norm:
        return None

    best_item = None
    best_score = 0.0
    for item in candidates:
        candidate_title = item.get("display_name") or item.get("title") or ""
        candidate_norm = normalize_title(candidate_title)
        if not candidate_norm:
            continue
        score = SequenceMatcher(None, target_norm, candidate_norm).ratio()
        if score > best_score:
            best_score = score
            best_item = item

    if best_score >= TITLE_MATCH_THRESHOLD:
        return best_item
    return None


def request_json(url: str, params: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code == 429:
                time.sleep(2 + attempt)
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            time.sleep(1 + attempt)
    return None


def fetch_openalex_citations(title: str) -> Optional[int]:
    if not title:
        return None

    params: Dict[str, Any] = {
        "filter": f"title.search:{title}",
        "per-page": 5,
        "select": "display_name,cited_by_count",
    }
    if OPENALEX_API_KEY:
        params["api_key"] = OPENALEX_API_KEY
    if OPENALEX_MAILTO:
        params["mailto"] = OPENALEX_MAILTO

    data = request_json("https://api.openalex.org/works", params=params)
    if not data or "results" not in data:
        return None

    match = best_title_match(title, data.get("results", []))
    if not match:
        return None
    cited_by_count = match.get("cited_by_count")
    return int(cited_by_count) if cited_by_count is not None else None


def fetch_semantic_scholar_citations(title: str) -> Optional[int]:
    if not title:
        return None

    params: Dict[str, Any] = {
        "query": title,
        "limit": 1,
        "fields": "title,citationCount",
    }
    headers: Dict[str, str] = {}
    if SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY

    data = request_json("https://api.semanticscholar.org/graph/v1/paper/search/bulk", params=params, headers=headers)
    if not data or "data" not in data:
        return None

    match = best_title_match(title, data.get("data", []))
    if not match:
        return None
    citation_count = match.get("citationCount")
    return int(citation_count) if citation_count is not None else None


def get_date_range_from_data(df: pd.DataFrame) -> Tuple[str, str]:
    if "Submitted" in df.columns and len(df) > 0:
        submitted_dates = pd.to_datetime(df["Submitted"], errors="coerce")
        start_date = submitted_dates.min().strftime("%y%m%d")
        end_date = submitted_dates.max().strftime("%y%m%d")
    else:
        current_date = datetime.now().strftime("%y%m%d")
        start_date = current_date
        end_date = current_date
    return start_date, end_date


def main() -> None:
    print("=" * 60)
    print("Phase 1-aux_1: 인용 수(OpenAlex → Semantic Scholar) 추가")
    print("=" * 60)

    if not os.path.exists(PHASE1_CSV_PATH):
        raise SystemExit(f"CSV not found: {PHASE1_CSV_PATH}")

    os.makedirs(BACKUP_DIR, exist_ok=True)
    os.makedirs(PHASE1_BACKUP_DIR, exist_ok=True)

    df = pd.read_csv(PHASE1_CSV_PATH, encoding="utf-8-sig")
    if "Title" not in df.columns:
        raise SystemExit("입력 CSV에 'Title' 컬럼이 없습니다.")

    df = df.copy()
    df["citation_count"] = ""
    df["citation_source"] = ""

    start_date_str, end_date_str = get_date_range_from_data(df)

    total = len(df)
    for idx, row in df.iterrows():
        title = str(row.get("Title", "")).strip()
        if not title:
            continue

        citation = fetch_openalex_citations(title)
        source = "OpenAlex" if citation is not None else ""

        if citation is None:
            citation = fetch_semantic_scholar_citations(title)
            if citation is not None:
                source = "SemanticScholar"

        if citation is not None:
            df.at[idx, "citation_count"] = citation
            df.at[idx, "citation_source"] = source

        print(f"[{idx+1:3d}/{total}] {source or 'NOT FOUND'} | {title[:80]}")

        if SLEEP_BETWEEN_REQUESTS > 0:
            time.sleep(SLEEP_BETWEEN_REQUESTS)

    # Backup original Phase 1 output before overwrite
    original_df = pd.read_csv(PHASE1_CSV_PATH, encoding="utf-8-sig")
    original_backup_path = os.path.join(
        PHASE1_BACKUP_DIR,
        f"1_URL_of_paper_abstractions_original_StartDate{start_date_str}_EndDate{end_date_str}.csv",
    )
    original_df.to_csv(original_backup_path, index=False, encoding="utf-8-sig")
    print(f"Phase 1 원본 백업 완료: {original_backup_path}")

    # Overwrite Phase 1 output with citation columns
    df.to_csv(PHASE1_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"Phase 1 결과 업데이트 완료: {PHASE1_CSV_PATH}")

    # Also save a separate Phase 1-aux_1 copy for traceability
    df.to_csv(RESULT_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"별도 결과 저장 완료: {RESULT_CSV_PATH}")

    backup_path = os.path.join(
        BACKUP_DIR,
        f"1-aux_1_citation_results_StartDate{start_date_str}_EndDate{end_date_str}.csv",
    )
    df.to_csv(backup_path, index=False, encoding="utf-8-sig")
    print(f"백업 저장 완료: {backup_path}")

    phase1_backup_path = os.path.join(
        PHASE1_BACKUP_DIR,
        f"1_URL_of_paper_abstractions_with_citations_StartDate{start_date_str}_EndDate{end_date_str}.csv",
    )
    df.to_csv(phase1_backup_path, index=False, encoding="utf-8-sig")
    print(f"Phase 1 백업 저장 완료: {phase1_backup_path}")


if __name__ == "__main__":
    main()
