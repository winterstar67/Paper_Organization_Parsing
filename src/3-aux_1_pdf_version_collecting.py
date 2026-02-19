"""Extract first-page text from arXiv PDFs in memory and write to a result CSV."""

import os
from typing import Optional, Set
from datetime import datetime

import pandas as pd
import requests
from pipeline_config import results_dir, backup_dir

try:
    import fitz
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyMuPDF(fitz) is required: pip install pymupdf") from exc


PHASE1_CSV_PATH = os.path.join(results_dir("Phase_1"), "1_URL_of_paper_abstractions.csv")
FAILED_PAPERS_CSV_PATH = os.path.join(results_dir("Phase_2"), "2_2_failed_papers.csv")
RESULT_CSV_PATH = os.path.join(results_dir("Phase_3-aux_1"), "3-aux_1_pdf_version_result.csv")
PROCESSING_CSV_PATH = os.path.join(results_dir("Phase_3-aux_1"), "3-aux_1_pdf_version_result_processing.csv")
BACKUP_DIR = backup_dir("Phase_3-aux_1")


def fetch_pdf_bytes(url: str, timeout: int = 30) -> Optional[bytes]:
    if not url or not isinstance(url, str):
        return None
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.content
    except requests.RequestException:
        return None


def extract_first_page_text(pdf_bytes: bytes) -> str:
    if not pdf_bytes:
        return ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        if doc.page_count == 0:
            return ""
        page = doc.load_page(0)
        return page.get_text("text").strip()


def load_failed_paper_titles(path: str) -> Set[str]:
    """Return a set of titles from failed papers that need PDF processing."""
    if not os.path.exists(path):
        print(f"INFO 실패 논문 파일이 없어 모든 논문을 처리합니다: {path}")
        return set()

    try:
        failed_df = pd.read_csv(path, encoding="utf-8-sig")
    except Exception as exc:  # pragma: no cover
        print(f"WARNING 실패 논문 파일을 읽는 중 오류가 발생했습니다: {exc}")
        return set()

    if "Title" not in failed_df.columns:
        print("WARNING 실패 논문 파일에 'Title' 컬럼이 없어 모든 논문을 처리합니다.")
        return set()

    titles = (
        failed_df["Title"].dropna().astype(str).str.strip()
    )
    return {title for title in titles if title}


def save_intermediate_results(df: pd.DataFrame, processed_count: int) -> None:
    """Save intermediate processing results every 10 papers for recovery purposes."""
    try:
        # Main result file
        df.to_csv(RESULT_CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"OK 중간 저장 완료 ({processed_count}개 논문 처리됨): {RESULT_CSV_PATH}")
        
        # Processing file for backup access
        df.to_csv(PROCESSING_CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"OK 처리 중 파일 저장 완료: {PROCESSING_CSV_PATH}")
        
    except Exception as e:
        print(f"ERROR 중간 저장 실패: {str(e)}")
        # Try to save processing file even if main file fails
        try:
            df.to_csv(PROCESSING_CSV_PATH, index=False, encoding="utf-8-sig")
            print(f"OK 처리 중 파일은 저장 성공: {PROCESSING_CSV_PATH}")
        except Exception as e2:
            print(f"ERROR 처리 중 파일 저장도 실패: {str(e2)}")


def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # Initialize new columns
    df = df.copy()
    df["pdf_url"] = ""
    df["pdf_abstract_text"] = ""
    
    total = len(df)
    processed_count = 0
    
    print(f"\n{'='*60}")
    print(f"PDF 데이터 수집 시작")
    print(f"총 {total}개 논문 처리 예정")
    print(f"10개 논문마다 중간 저장 실행")
    print(f"{'='*60}")
    
    start_time = datetime.now()

    for idx, row in df.iterrows():
        paper_id = idx + 1
        
        # Progress calculation
        progress = (paper_id / total) * 100
        elapsed_time = (datetime.now() - start_time).total_seconds()
        estimated_total_time = elapsed_time * total / paper_id if paper_id > 0 else 0
        remaining_time = estimated_total_time - elapsed_time
        
        pdf_url = row.get("pdf_url", "")
        if not pdf_url and isinstance(row.get("abs_url"), str):
            abs_url = row.get("abs_url", "")
            pdf_url = abs_url.replace("/abs/", "/pdf/") if "/abs/" in abs_url else ""

        df.at[idx, "pdf_url"] = pdf_url

        pdf_bytes = fetch_pdf_bytes(pdf_url)
        text = extract_first_page_text(pdf_bytes)
        df.at[idx, "pdf_abstract_text"] = text

        status = "OK" if text else "EMPTY"
        print(f"\n[{paper_id:3d}/{total}] ({progress:.1f}%) PDF 추출 {status} - URL: {pdf_url}")
        print(f"경과시간: {elapsed_time/60:.1f}분 | 예상 남은시간: {remaining_time/60:.1f}분")
        
        processed_count += 1
        
        # Save intermediate results every 10 papers
        if processed_count % 10 == 0:
            save_intermediate_results(df, processed_count)
    
    # Final statistics
    total_elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n총 처리 시간: {total_elapsed/60:.1f}분")
    
    empty_count = sum(1 for text in df["pdf_abstract_text"] if not text)
    if empty_count:
        print(f"WARNING PDF 1페이지 텍스트를 추출하지 못한 논문: {empty_count}건")
    else:
        print("INFO 모든 논문의 PDF 1페이지 텍스트를 성공적으로 추출했습니다.")

    return df


def create_backup_directory() -> None:
    """Create backup directory for PDF version results."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    print(f"백업 디렉토리 생성 완료: {BACKUP_DIR}")


def get_date_range_from_data(df: pd.DataFrame) -> tuple[str, str]:
    """Extract date range from DataFrame for backup filename."""
    if 'Submitted' in df.columns and len(df) > 0:
        # Parse submission dates and get min/max
        submitted_dates = pd.to_datetime(df['Submitted'], errors='coerce')
        start_date = submitted_dates.min().strftime('%y%m%d')
        end_date = submitted_dates.max().strftime('%y%m%d')
    else:
        # Fallback to current date
        current_date = datetime.now().strftime('%y%m%d')
        start_date = current_date
        end_date = current_date
    return start_date, end_date


def main() -> None:
    print("=" * 60)
    print("Phase 3-aux_1: PDF 1페이지 텍스트 추출")
    print("=" * 60)
    
    if not os.path.exists(PHASE1_CSV_PATH):
        raise SystemExit(f"CSV not found: {PHASE1_CSV_PATH}")

    df = pd.read_csv(PHASE1_CSV_PATH, encoding="utf-8-sig")

    # Create backup directory
    create_backup_directory()
    start_date_str, end_date_str = get_date_range_from_data(df)

    if "Title" not in df.columns:
        print("WARNING 입력 CSV에 'Title' 컬럼이 없어 필터링을 수행할 수 없습니다.")
    else:
        failed_titles = load_failed_paper_titles(FAILED_PAPERS_CSV_PATH)
        if failed_titles:
            input_titles = df["Title"].fillna("").astype(str).str.strip()
            mask = input_titles.isin(failed_titles)
            selected_count = int(mask.sum())
            if selected_count:
                df = df.loc[mask].reset_index(drop=True)
                print(f"INFO HTML 처리 실패 논문 {selected_count}건만 PDF 처리합니다.")
            else:
                print("WARNING 실패 논문 목록과 일치하는 논문이 없습니다. 모든 논문을 처리합니다.")
        else:
            print("INFO 실패 논문 목록이 비어있어 모든 논문을 처리합니다.")

    if "pdf_url" not in df.columns:
        print("WARNING: 'pdf_url' column not found. Run Phase 1 after adding pdf_url support.")
        df["pdf_url"] = ""

    updated_df = process_dataframe(df)
    
    # Final save
    updated_df.to_csv(RESULT_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"최종 PDF 추출 결과 저장 완료: {RESULT_CSV_PATH}")
    
    # Save final backup
    final_backup_path = os.path.join(BACKUP_DIR, f"3-aux_1_pdf_version_result_StartDate{start_date_str}_EndDate{end_date_str}.csv")
    updated_df.to_csv(final_backup_path, index=False, encoding="utf-8-sig")
    print(f"최종 백업 파일 저장 완료: {final_backup_path}")


if __name__ == "__main__":
    main()
