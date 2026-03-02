#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 2 (Local): parse HTML from local files/content without crawling."""

import os
import pickle
import re
from datetime import datetime
from typing import Optional, Tuple

import pandas as pd
from bs4 import BeautifulSoup

from pipeline_config import PROJECT_DIR, backup_dir, results_dir


def remove_outer_tags_and_check_rule(html_with_tags: str) -> Tuple[str, Optional[str]]:
    if html_with_tags in ["NO_HTML", "NO_ltx_authors"]:
        return html_with_tags, None

    try:
        lines = [line for line in html_with_tags.strip().split("\n") if line.strip()]
        if len(lines) < 4:
            return html_with_tags, "Too few lines to apply rule"

        first_line = lines[0].strip()
        second_line = lines[1].strip()
        second_last_line = lines[-2].strip()
        last_line = lines[-1].strip()

        expected_first = '<div class="ltx_authors">'
        expected_second = '<span class="ltx_creator ltx_role_author">'
        expected_second_last = "</span>"
        expected_last = "</div>"

        violations = []
        if first_line != expected_first:
            violations.append(f"First tag mismatch: {first_line}")
        if second_line != expected_second:
            violations.append(f"Second tag mismatch: {second_line}")
        if second_last_line != expected_second_last:
            violations.append(f"Second last tag mismatch: {second_last_line}")
        if last_line != expected_last:
            violations.append(f"Last tag mismatch: {last_line}")
        if violations:
            return html_with_tags, "; ".join(violations)

        inner_lines = lines[2:-2]
        adjusted_lines = [line[4:] if line.startswith("    ") else line for line in inner_lines]
        return "\n".join(adjusted_lines), None
    except Exception as exc:
        return html_with_tags, f"Error processing HTML: {exc}"


def _prettify_4_space(tag) -> str:
    pretty_html = tag.prettify()
    lines = pretty_html.split("\n")
    formatted = []
    for line in lines:
        leading_spaces = len(line) - len(line.lstrip())
        if leading_spaces > 0:
            formatted.append((" " * (leading_spaces * 2)) + line.lstrip())
        else:
            formatted.append(line)
    return "\n".join(formatted)


def extract_ltx_authors_from_html_content(html_content: str) -> Tuple[str, str]:
    if not html_content:
        return ("NO_HTML", "NO_HTML")

    soup = BeautifulSoup(html_content, "html.parser")

    ltx_authors_div = soup.find("div", class_="ltx_authors")
    if ltx_authors_div:
        text_only = ltx_authors_div.get_text(separator=" ", strip=True)
        try:
            html_with_tags = _prettify_4_space(ltx_authors_div)
        except Exception:
            html_with_tags = str(ltx_authors_div)
        return (text_only, html_with_tags)

    # Fallback for non-arXiv or different HTML structures, including table-based layouts.
    candidate_selectors = [
        "div.authors",
        "section.authors",
        "p.authors",
        "[class*='author']",
        "[id*='author']",
        "table",
    ]
    selected_parts = []
    for selector in candidate_selectors:
        for node in soup.select(selector):
            text = node.get_text(" ", strip=True)
            if len(text) >= 8:
                selected_parts.append(node)
            if len(selected_parts) >= 8:
                break
        if len(selected_parts) >= 8:
            break

    if selected_parts:
        text_only = " ".join(node.get_text(" ", strip=True) for node in selected_parts)
        html_with_tags = "\n".join(str(node) for node in selected_parts)
        return (re.sub(r"\s+", " ", text_only).strip(), html_with_tags)

    body = soup.body or soup
    body_text = re.sub(r"\s+", " ", body.get_text(" ", strip=True)).strip()
    if body_text:
        return (body_text, str(body))

    return ("NO_ltx_authors", "NO_ltx_authors")


def _resolve_local_path(path_text: str) -> str:
    if not path_text:
        return ""
    path = str(path_text).strip()
    if os.path.isabs(path) and os.path.exists(path):
        return path
    candidate = os.path.join(PROJECT_DIR, path)
    if os.path.exists(candidate):
        return candidate
    return ""


def _clean_cell(value) -> str:
    text = str(value or "").strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def load_html_content_from_row(row: pd.Series) -> Tuple[str, str]:
    html_content = _clean_cell(row.get("html_content", ""))
    if html_content:
        return html_content, "html_content"

    path_candidates = [
        row.get("html_path", ""),
        row.get("html_file", ""),
        row.get("html_local_path", ""),
        row.get("html_url", ""),
    ]

    for candidate in path_candidates:
        resolved = _resolve_local_path(_clean_cell(candidate))
        if resolved and os.path.isfile(resolved):
            with open(resolved, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(), resolved

    url_value = _clean_cell(row.get("html_url", ""))
    if url_value.startswith("http://") or url_value.startswith("https://"):
        return "", "NETWORK_DISABLED"

    return "", "NO_LOCAL_HTML"


def save_additional_formats(df: pd.DataFrame, start_date_str: str, end_date_str: str) -> None:
    html_raw_text_data = df["html_raw_text"].tolist()
    pickle_path = os.path.join(results_dir("Phase_2"), "html_raw_text.p")
    backup_pickle_path = os.path.join(
        backup_dir("Phase_2"), f"html_raw_text_StartDate{start_date_str}_EndDate{end_date_str}.p"
    )
    with open(pickle_path, "wb") as f:
        pickle.dump(html_raw_text_data, f)
    with open(backup_pickle_path, "wb") as f:
        pickle.dump(html_raw_text_data, f)

    txt_path = os.path.join(results_dir("Phase_2"), "html_raw_text.txt")
    backup_txt_path = os.path.join(
        backup_dir("Phase_2"), f"html_raw_text_StartDate{start_date_str}_EndDate{end_date_str}.txt"
    )
    for path in [txt_path, backup_txt_path]:
        with open(path, "w", encoding="utf-8") as f:
            for idx, text in enumerate(df["html_raw_text"]):
                f.write(f"=== Paper {idx + 1} ===\n{text}\n{'='*50}\n\n")


def save_failed_papers(df: pd.DataFrame, start_date_str: str, end_date_str: str) -> None:
    failed_df = df[(df["html_raw_text"] == "NO_HTML") | (df["html_raw_text"] == "NO_ltx_authors")].copy()
    failed_output_file = os.path.join(results_dir("Phase_2"), "2_2_failed_papers.csv")
    failed_df.to_csv(failed_output_file, index=False, encoding="utf-8-sig")

    backup_failed_path = os.path.join(
        backup_dir("Phase_2"), f"2_2_failed_papers_StartDate{start_date_str}_EndDate{end_date_str}.csv"
    )
    failed_df.to_csv(backup_failed_path, index=False, encoding="utf-8-sig")


def main() -> None:
    print("=" * 60)
    print("Phase 2 (Local): HTML 데이터 파싱")
    print("=" * 60)

    input_file = os.path.join(results_dir("Phase_1"), "1_URL_of_paper_abstractions.csv")
    output_file = os.path.join(results_dir("Phase_2"), "2_html_raw_text.csv")

    if not os.path.exists(input_file):
        raise SystemExit(f"입력 파일을 찾을 수 없습니다: {input_file}")

    df = pd.read_csv(input_file, encoding="utf-8-sig")
    print(f"총 {len(df)}개의 논문 데이터를 로드했습니다.")

    if "Submitted" in df.columns and len(df) > 0:
        submitted_dates = pd.to_datetime(df["Submitted"], errors="coerce")
        start_date = submitted_dates.min().strftime("%y%m%d")
        end_date = submitted_dates.max().strftime("%y%m%d")
    else:
        current_date = datetime.now().strftime("%y%m%d")
        start_date = current_date
        end_date = current_date

    df["html_raw_text"] = ""
    df["html_raw_text_with_tags"] = ""
    df["html_raw_text_with_tags_filtered"] = ""

    for idx, row in df.iterrows():
        html_content, source = load_html_content_from_row(row)
        paper_id = idx + 1
        print(f"[{paper_id:3d}/{len(df)}] HTML source: {source}")

        if not html_content:
            df.at[idx, "html_raw_text"] = "NO_HTML"
            df.at[idx, "html_raw_text_with_tags"] = "NO_HTML"
            df.at[idx, "html_raw_text_with_tags_filtered"] = "NO_HTML"
            continue

        text_only, html_with_tags = extract_ltx_authors_from_html_content(html_content)
        filtered_html, _ = remove_outer_tags_and_check_rule(html_with_tags)
        df.at[idx, "html_raw_text"] = text_only
        df.at[idx, "html_raw_text_with_tags"] = html_with_tags
        df.at[idx, "html_raw_text_with_tags_filtered"] = filtered_html

    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    backup_path = os.path.join(backup_dir("Phase_2"), f"2_html_raw_text_StartDate{start_date}_EndDate{end_date}.csv")
    df.to_csv(backup_path, index=False, encoding="utf-8-sig")

    save_additional_formats(df, start_date, end_date)
    save_failed_papers(df, start_date, end_date)

    success_count = len(df[(df["html_raw_text"] != "NO_HTML") & (df["html_raw_text"] != "NO_ltx_authors")])
    print(f"성공적으로 파싱된 논문: {success_count} / {len(df)}")
    print(f"저장 완료: {output_file}")


if __name__ == "__main__":
    main()
