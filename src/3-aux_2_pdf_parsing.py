"""Filter PDF abstracts using configured email patterns."""

import json
import os
import re
from typing import Dict, Iterable, List, Tuple, Union
import pandas as pd
import dotenv
from pipeline_config import results_dir


dotenv.load_dotenv()

INPUT_CSV_PATH = os.path.join(results_dir("Phase_3-aux_1"), "3-aux_1_pdf_version_result.csv")
OUTPUT_CSV_PATH = os.path.join(results_dir("Phase_3-aux_2"), "3-aux_2_pdf_parsing.csv")

PatternValue = Union[str, List[str]]


def _load_email_patterns() -> Dict[str, List[PatternValue]]:
    """Return email patterns defined in the EMAIL_PATTERNS environment variable."""
    patterns_raw = os.getenv("EMAIL_PATTERNS", "{}")
    try:
        parsed = json.loads(patterns_raw)
    except json.JSONDecodeError:
        print("WARNING EMAIL_PATTERNS 환경변수가 올바른 JSON 형식이 아닙니다. 필터링 없이 종료합니다.")
        return {}

    if not isinstance(parsed, dict):
        print("WARNING EMAIL_PATTERNS 가 dict 형식이 아닙니다. 필터링 없이 종료합니다.")
        return {}

    valid_patterns: Dict[str, List[PatternValue]] = {}
    for org, pattern_list in parsed.items():
        collected: List[PatternValue] = []

        if isinstance(pattern_list, str):
            collected.append(pattern_list)
        elif isinstance(pattern_list, Iterable):
            for pattern in pattern_list:
                if isinstance(pattern, str):
                    collected.append(pattern)
                elif isinstance(pattern, list):
                    collected.append([str(item) for item in pattern])
        if collected:
            valid_patterns[str(org)] = collected
    return valid_patterns


def _match_literal(text: str, literal: str) -> bool:
    literal = literal.strip().lower()
    if not literal:
        return False
    return literal in text


def _match_pattern_tokens(text: str, org: str, tokens: List[str]) -> bool:
    if len(tokens) != 3:
        return False

    start, mid, end = (token.lower() for token in tokens)

    if mid == "기관명":
        mid = org.lower()

    email_segment = r"[A-Za-z\.]{0,20}"
    regex = re.escape(start) + email_segment + re.escape(mid) + email_segment + re.escape(end)
    return re.search(regex, text, flags=re.IGNORECASE | re.DOTALL) is not None


def _match_and_collect(text: str, patterns: Dict[str, List[PatternValue]]) -> List[str]:
    matched_orgs: List[str] = []
    for org, pattern_list in patterns.items():
        for pattern in pattern_list:
            if isinstance(pattern, str):
                if _match_literal(text, pattern):
                    matched_orgs.append(org)
                    break
            elif isinstance(pattern, list) and _match_pattern_tokens(text, org, pattern):
                matched_orgs.append(org)
                break
    return matched_orgs


def filter_pdf_abstracts() -> pd.DataFrame:
    if not os.path.exists(INPUT_CSV_PATH):
        raise SystemExit(f"입력 CSV 파일을 찾을 수 없습니다: {INPUT_CSV_PATH}")

    df = pd.read_csv(INPUT_CSV_PATH, encoding="utf-8-sig")

    if "pdf_abstract_text" not in df.columns:
        print("WARNING 입력 CSV에 'pdf_abstract_text' 컬럼이 없어 필터링을 수행할 수 없습니다.")
        df["pdf_abstract_text"] = ""

    df["pdf_abstract_text"] = df["pdf_abstract_text"].fillna("").astype(str).str.lower()

    patterns = _load_email_patterns()
    if not patterns:
        print("WARNING EMAIL_PATTERNS가 비어 있어 결과가 생성되지 않습니다.")
        return pd.DataFrame(columns=df.columns)

    matched_data: List[Tuple[List[str], bool]] = []
    for text in df["pdf_abstract_text"]:
        orgs = _match_and_collect(text, patterns)
        matched_data.append((orgs, bool(orgs)))

    mask = [flag for _, flag in matched_data]
    matched_indices = [i for i, flag in enumerate(mask) if flag]
    filtered_df = df.iloc[matched_indices].reset_index(drop=True)

    pdf_orgs = [matched_data[idx][0] for idx in matched_indices]
    filtered_df["pdf_based_organization"] = pdf_orgs

    print(f"INFO 총 {len(df)}건 중 {len(filtered_df)}건이 이메일 패턴과 일치했습니다.")
    return filtered_df



def main() -> None:
    print("=" * 60)
    print("Phase 3-aux_2: 이메일 패턴 기반 PDF 필터링")
    print("=" * 60)

    filtered_df = filter_pdf_abstracts()
    if "pdf_abstract_text" in filtered_df.columns:
        filtered_df = filtered_df.drop(columns=["pdf_abstract_text"])

    filtered_df.to_csv(OUTPUT_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"최종 PDF 파싱 결과 저장 완료: {OUTPUT_CSV_PATH}")


if __name__ == "__main__":
    main()
