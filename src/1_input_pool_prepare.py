#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 1 (Local): normalize user-provided paper pool table into pipeline input CSV."""

import argparse
import json
import os
from datetime import datetime
from typing import Dict, List

import pandas as pd
from zoneinfo import ZoneInfo

from pipeline_config import PROJECT_DIR, results_dir


OUTPUT_CSV_PATH = os.path.join(results_dir("Phase_1"), "1_URL_of_paper_abstractions.csv")
VALIDATION_JSON_PATH = os.path.join(results_dir("Phase_1"), "collection_validation.json")


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    aliases: Dict[str, List[str]] = {
        "Title": ["title", "paper_title", "논문제목", "제목"],
        "Authors": ["authors", "author", "저자", "저자명"],
        "Abstract": ["abstract", "summary", "요약"],
        "Subjects": ["subjects", "subject", "category", "분야"],
        "Comments": ["comments", "comment", "비고"],
        "Submitted": ["submitted", "date", "submitted_date", "게시일", "날짜"],
        "abs_url": ["abs_url", "abstract_url", "arxiv_abs_url"],
        "html_url": ["html_url", "source_url", "paper_url"],
        "pdf_url": ["pdf_url", "paper_pdf_url"],
        "html_path": ["html_path", "html_file", "html_local_path", "html_filepath"],
        "pdf_path": ["pdf_path", "pdf_file", "pdf_local_path", "pdf_filepath"],
        "html_content": ["html_content", "raw_html", "html_text"],
    }

    lower_to_original = {col.lower().strip(): col for col in df.columns}
    normalized = pd.DataFrame(index=df.index)

    for target, candidates in aliases.items():
        source_col = None
        if target in df.columns:
            source_col = target
        else:
            for candidate in candidates:
                if candidate.lower() in lower_to_original:
                    source_col = lower_to_original[candidate.lower()]
                    break
        normalized[target] = df[source_col] if source_col else ""

    return normalized


def _load_pool_table(input_path: str) -> pd.DataFrame:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_path}")

    _, ext = os.path.splitext(input_path.lower())
    if ext == ".csv":
        return pd.read_csv(input_path, encoding="utf-8-sig")
    if ext in {".tsv", ".txt"}:
        return pd.read_csv(input_path, sep="\t", encoding="utf-8-sig")
    if ext in {".xlsx", ".xls"}:
        return pd.read_excel(input_path)
    if ext == ".json":
        return pd.read_json(input_path)
    raise ValueError("지원하지 않는 입력 형식입니다. csv/tsv/xlsx/json만 지원합니다.")


def _sanitize_row_values(df: pd.DataFrame) -> pd.DataFrame:
    df = df.fillna("").copy()
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    return df


def _resolve_local_path(value: str) -> str:
    if not value:
        return ""
    path = value.strip()
    if os.path.isabs(path) and os.path.exists(path):
        return path
    candidate = os.path.join(PROJECT_DIR, path)
    return candidate if os.path.exists(candidate) else path


def _build_output_df(df: pd.DataFrame) -> pd.DataFrame:
    now_kst = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
    run_date = datetime.now().strftime("%Y%m%d")

    out = df.copy()
    out = _sanitize_row_values(out)

    out["html_path"] = out["html_path"].apply(_resolve_local_path)
    out["pdf_path"] = out["pdf_path"].apply(_resolve_local_path)

    # If URL columns are actually local files, move them to *_path.
    html_url_is_file = out["html_url"].apply(lambda v: bool(v) and os.path.exists(_resolve_local_path(v)))
    pdf_url_is_file = out["pdf_url"].apply(lambda v: bool(v) and os.path.exists(_resolve_local_path(v)))

    out.loc[html_url_is_file & (out["html_path"] == ""), "html_path"] = out.loc[html_url_is_file, "html_url"].apply(
        _resolve_local_path
    )
    out.loc[pdf_url_is_file & (out["pdf_path"] == ""), "pdf_path"] = out.loc[pdf_url_is_file, "pdf_url"].apply(
        _resolve_local_path
    )

    out["ID"] = [f"{run_date}_{idx + 1}" for idx in range(len(out))]
    out["collected_at_kst"] = now_kst

    if "Submitted" in out.columns:
        parsed = pd.to_datetime(out["Submitted"], errors="coerce")
        out.loc[parsed.isna(), "Submitted"] = datetime.now().strftime("%Y-%m-%d")
    else:
        out["Submitted"] = datetime.now().strftime("%Y-%m-%d")

    required_title = out["Title"].astype(str).str.strip() != ""
    has_any_source = (
        (out["html_path"].astype(str).str.strip() != "")
        | (out["html_content"].astype(str).str.strip() != "")
        | (out["pdf_path"].astype(str).str.strip() != "")
    )
    valid_mask = required_title & has_any_source
    return out.loc[valid_mask].reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="로컬 논문 풀 테이블을 Phase 1 입력 형식으로 정규화")
    parser.add_argument(
        "--input",
        type=str,
        default=os.getenv("PAPER_POOL_PATH", os.path.join(PROJECT_DIR, "input", "paper_pool.csv")),
        help="입력 파일 경로 (csv/tsv/xlsx/json)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Phase 1 (Local): 입력 논문 풀 정규화")
    print("=" * 60)
    print(f"입력 파일: {args.input}")

    raw_df = _load_pool_table(args.input)
    print(f"원본 행 수: {len(raw_df)}")

    normalized = _normalize_columns(raw_df)
    output_df = _build_output_df(normalized)
    print(f"유효 행 수: {len(output_df)}")

    if output_df.empty:
        raise SystemExit("유효한 행이 없습니다. Title + (html_path/html_content/pdf_path) 조합이 필요합니다.")

    output_df.to_csv(OUTPUT_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {OUTPUT_CSV_PATH}")

    validation = {
        "source": "local_pool",
        "input_path": args.input,
        "webpage_total": int(len(raw_df)),
        "collected_count": int(len(output_df)),
        "validation_status": "PASS" if len(output_df) > 0 else "FAIL",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(VALIDATION_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(validation, f, ensure_ascii=False, indent=2)
    print(f"검증 리포트 저장 완료: {VALIDATION_JSON_PATH}")


if __name__ == "__main__":
    main()
