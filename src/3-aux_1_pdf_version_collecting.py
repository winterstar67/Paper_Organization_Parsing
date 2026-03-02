#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 3-aux_1 (Local): extract first-page text from local PDF files only."""

import os
from datetime import datetime
from typing import Set

import pandas as pd

from pipeline_config import PROJECT_DIR, backup_dir, results_dir

try:
    import fitz
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyMuPDF(fitz) is required: pip install pymupdf") from exc


PHASE1_CSV_PATH = os.path.join(results_dir("Phase_1"), "1_URL_of_paper_abstractions.csv")
FAILED_PAPERS_CSV_PATH = os.path.join(results_dir("Phase_2"), "2_2_failed_papers.csv")
RESULT_CSV_PATH = os.path.join(results_dir("Phase_3-aux_1"), "3-aux_1_pdf_version_result.csv")
BACKUP_DIR = backup_dir("Phase_3-aux_1")


def load_failed_paper_titles(path: str) -> Set[str]:
    if not os.path.exists(path):
        return set()
    failed_df = pd.read_csv(path, encoding="utf-8-sig")
    if "Title" not in failed_df.columns:
        return set()
    titles = failed_df["Title"].dropna().astype(str).str.strip()
    return {title for title in titles if title}


def _resolve_local_pdf_path(path_text: str) -> str:
    if not path_text:
        return ""
    path = path_text.strip()
    if os.path.isabs(path) and os.path.exists(path):
        return path
    candidate = os.path.join(PROJECT_DIR, path)
    if os.path.exists(candidate):
        return candidate
    return ""


def resolve_pdf_path(row: pd.Series) -> str:
    for key in ("pdf_path", "pdf_file", "pdf_local_path", "pdf_url"):
        value = str(row.get(key, "") or "").strip()
        if not value:
            continue
        if value.startswith("http://") or value.startswith("https://"):
            continue
        resolved = _resolve_local_pdf_path(value)
        if resolved and os.path.isfile(resolved):
            return resolved
    return ""


def extract_first_page_text_from_path(pdf_path: str) -> str:
    if not pdf_path:
        return ""
    with fitz.open(pdf_path) as doc:
        if doc.page_count == 0:
            return ""
        page = doc.load_page(0)
        return page.get_text("text").strip()


def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "pdf_path" not in df.columns:
        df["pdf_path"] = ""
    df["pdf_abstract_text"] = ""

    total = len(df)
    for idx, row in df.iterrows():
        paper_id = idx + 1
        path = resolve_pdf_path(row)
        df.at[idx, "pdf_path"] = path

        text = ""
        if path:
            try:
                text = extract_first_page_text_from_path(path)
            except Exception as exc:
                print(f"[{paper_id:3d}/{total}] PDF 파싱 실패: {path} ({exc})")
        else:
            print(f"[{paper_id:3d}/{total}] 로컬 PDF 경로 없음")

        df.at[idx, "pdf_abstract_text"] = text
        print(f"[{paper_id:3d}/{total}] {'OK' if text else 'EMPTY'}")
    return df


def get_date_range_from_data(df: pd.DataFrame) -> tuple[str, str]:
    if "Submitted" in df.columns and len(df) > 0:
        submitted_dates = pd.to_datetime(df["Submitted"], errors="coerce")
        return submitted_dates.min().strftime("%y%m%d"), submitted_dates.max().strftime("%y%m%d")
    current_date = datetime.now().strftime("%y%m%d")
    return current_date, current_date


def main() -> None:
    print("=" * 60)
    print("Phase 3-aux_1 (Local): PDF 1페이지 텍스트 추출")
    print("=" * 60)

    if not os.path.exists(PHASE1_CSV_PATH):
        raise SystemExit(f"CSV not found: {PHASE1_CSV_PATH}")

    df = pd.read_csv(PHASE1_CSV_PATH, encoding="utf-8-sig")
    if "Title" in df.columns:
        failed_titles = load_failed_paper_titles(FAILED_PAPERS_CSV_PATH)
        if failed_titles:
            input_titles = df["Title"].fillna("").astype(str).str.strip()
            mask = input_titles.isin(failed_titles)
            if int(mask.sum()) > 0:
                df = df.loc[mask].reset_index(drop=True)
                print(f"INFO HTML 실패 논문 {len(df)}건을 PDF로 보완 처리합니다.")

    updated_df = process_dataframe(df)
    updated_df.to_csv(RESULT_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {RESULT_CSV_PATH}")

    start_date_str, end_date_str = get_date_range_from_data(updated_df)
    final_backup_path = os.path.join(
        BACKUP_DIR, f"3-aux_1_pdf_version_result_StartDate{start_date_str}_EndDate{end_date_str}.csv"
    )
    updated_df.to_csv(final_backup_path, index=False, encoding="utf-8-sig")
    print(f"백업 저장 완료: {final_backup_path}")


if __name__ == "__main__":
    main()
