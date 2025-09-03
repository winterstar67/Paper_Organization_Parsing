import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import time
import pickle
import xml.dom.minidom
import re
from typing import Tuple, Optional, Any

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
PAR_DIR = os.path.dirname(CUR_DIR)

def remove_outer_tags_and_check_rule(html_with_tags: str) -> Tuple[str, Optional[str]]:
    """
    HTML에서 외부 div와 span 태그를 제거하고 규칙 위배 여부를 확인합니다.
    
    Removes outer HTML tags and validates structure according to specific rules for ltx_authors content.
    
    Input:
        - html_with_tags: str - HTML string with ltx_authors structure
            - Ex: '<div class="ltx_authors">\n<span class="ltx_creator ltx_role_author">\nContent\n</span>\n</div>'
    
    Output:
        - filtered_html: str - HTML with outer tags removed and indentation adjusted
            - Ex: 'Content'
        - rule_violation_message: Optional[str] - Error message if rule violated, None if valid
            - Ex: None (valid) or "First tag mismatch: expected '<div class="ltx_authors">', got '<div>'"
    
    규칙:
    1. 첫 번째 태그: <div class="ltx_authors">
    2. 두 번째 태그: <span class="ltx_creator ltx_role_author">
    3. 마지막에서 두 번째 태그: </span>
    4. 마지막 태그: </div>
    
    Example:
        >>> html = '<div class="ltx_authors">\n<span class="ltx_creator ltx_role_author">\nJohn Doe\n</span>\n</div>'
        >>> filtered, error = remove_outer_tags_and_check_rule(html)
        >>> print(filtered)
        'John Doe'
        >>> print(error)
        None
    """
    if html_with_tags in ["NO_HTML", "NO_ltx_authors"]:
        return html_with_tags, None
    
    try:
        lines = html_with_tags.strip().split('\n')
        lines = [line for line in lines if line.strip()]  # 빈 줄 제거
        
        if len(lines) < 4:
            return html_with_tags, "Too few lines to apply rule"
        
        # 규칙 검사
        first_line = lines[0].strip()
        second_line = lines[1].strip()
        second_last_line = lines[-2].strip()
        last_line = lines[-1].strip()
        
        # 하드코딩된 규칙 체크
        expected_first = '<div class="ltx_authors">'
        expected_second = '<span class="ltx_creator ltx_role_author">'
        expected_second_last = '</span>'
        expected_last = '</div>'
        
        rule_violation = []
        
        if first_line != expected_first:
            rule_violation.append(f"First tag mismatch: expected '{expected_first}', got '{first_line}'")
        
        if second_line != expected_second:
            rule_violation.append(f"Second tag mismatch: expected '{expected_second}', got '{second_line}'")
        
        if second_last_line != expected_second_last:
            rule_violation.append(f"Second last tag mismatch: expected '{expected_second_last}', got '{second_last_line}'")
        
        if last_line != expected_last:
            rule_violation.append(f"Last tag mismatch: expected '{expected_last}', got '{last_line}'")
        
        # 규칙 위배가 있으면 메시지 반환
        if rule_violation:
            violation_message = "; ".join(rule_violation)
            return html_with_tags, violation_message
        
        # 규칙이 정상이면 외부 4개 태그 제거
        inner_lines = lines[2:-2]  # 첫 2줄과 마지막 2줄 제거
        
        # 들여쓰기 조정 (4칸씩 줄임)
        adjusted_lines = []
        for line in inner_lines:
            if line.startswith('    '):  # 4칸 이상 들여쓰기된 경우
                adjusted_lines.append(line[4:])  # 4칸 제거
            else:
                adjusted_lines.append(line)
        
        filtered_html = '\n'.join(adjusted_lines)
        return filtered_html, None
        
    except Exception as e:
        return html_with_tags, f"Error processing HTML: {str(e)}"

def extract_ltx_authors(html_url: str) -> Tuple[str, str]:
    """
    주어진 HTML URL에서 <div class="ltx_authors"> 태그의 텍스트와 HTML을 추출합니다.
    
    Fetches HTML content from arXiv URL and extracts ltx_authors section in both text and HTML formats.
    
    Input:
        - html_url: str - URL of arXiv HTML page
            - Ex: 'https://arxiv.org/html/2405.12345'
    
    Output:
        - text_only: str - Plain text content from ltx_authors section
            - Ex: 'John Doe\nUniversity of Example\nDepartment of Computer Science'
        - html_with_tags: str - HTML content with proper indentation
            - Ex: '<div class="ltx_authors">\n    <span class="ltx_creator ltx_role_author">\n        John Doe\n        <br class="ltx_break"/>\n        University of Example\n    </span>\n</div>'
        
    Special return values:
        - ("NO_HTML", "NO_HTML"): When HTML is not available or request fails
        - ("NO_ltx_authors", "NO_ltx_authors"): When ltx_authors tag is not found
    
    Example:
        >>> text, html = extract_ltx_authors('https://arxiv.org/html/2405.12345')
        >>> print(text[:50])
        'John Doe\nUniversity of Example\nDepartment of...'
        >>> print('ltx_authors' in html)
        True
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(html_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # HTML이 없다는 메시지 체크
        if ("No HTML for" in response.text or 
            "HTML is not available for the source" in response.text):
            return ("NO_HTML", "NO_HTML")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ltx_authors 태그 찾기
        ltx_authors_div = soup.find('div', class_='ltx_authors')
        
        if ltx_authors_div:
            # 텍스트만 추출
            text_only = ltx_authors_div.get_text()
            # HTML 태그 포함하여 hierarchical indentation으로 추출
            try:
                # BeautifulSoup의 prettify()는 기본 2칸 들여쓰기 사용
                pretty_html = ltx_authors_div.prettify()
                # 2칸을 4칸으로 변경
                lines = pretty_html.split('\n')
                formatted_lines = []
                for line in lines:
                    # 앞의 공백 개수 세기
                    leading_spaces = len(line) - len(line.lstrip())
                    if leading_spaces > 0:
                        # 2칸 단위를 4칸 단위로 변경
                        new_indent = ' ' * (leading_spaces * 2)
                        formatted_lines.append(new_indent + line.lstrip())
                    else:
                        formatted_lines.append(line)
                html_with_tags = '\n'.join(formatted_lines)
            except:
                # prettify 실패시 원본 HTML 사용
                html_with_tags = str(ltx_authors_div)
            return (text_only, html_with_tags)
        else:
            return ("NO_ltx_authors", "NO_ltx_authors")
            
    except Exception as e:
        print(f"Error processing {html_url}: {str(e)}")
        return ("NO_HTML", "NO_HTML")

def create_directories() -> None:
    """
    필요한 디렉토리들을 생성합니다.
    
    Creates necessary directories for HTML raw text processing and backup storage.
    
    Input: None
    
    Output: None (creates directories)
        - backup/2_html_raw_text: Backup directory for HTML processing results
    
    Example:
        >>> create_directories()
        디렉토리 생성 완료
    """
    os.makedirs(f"{PAR_DIR}/backup/2_html_raw_text", exist_ok=True)
    print("디렉토리 생성 완료")

def save_existing_data_to_backup(start_date_str: str, end_date_str: str) -> bool:
    """
    기존 데이터를 백업으로 저장한 후 삭제합니다.
    
    Backs up existing HTML raw text results before processing new data.
    
    Input:
        - start_date_str: str - Start date in YYMMDD format
            - Ex: '250508'
        - end_date_str: str - End date in YYMMDD format
            - Ex: '250509'
    
    Output:
        - backup_created: bool - True if backup was created, False if no existing file
            - Ex: True
    
    Example:
        >>> backup_created = save_existing_data_to_backup('250508', '250509')
        기존 데이터 백업 저장: backup/2_html_raw_text/2_html_raw_text_StartDate250508_EndDate250509.csv
        >>> print(backup_created)
        True
    """
    output_file = f"{PAR_DIR}/results/2_html_raw_text.csv"
    if os.path.exists(output_file):
        existing_df = pd.read_csv(output_file)
        backup_path = f"{PAR_DIR}/backup/2_html_raw_text/2_html_raw_text_StartDate{start_date_str}_EndDate{end_date_str}.csv"
        existing_df.to_csv(backup_path, index=False, encoding='utf-8-sig')
        print(f"기존 데이터 백업 저장: {backup_path}")
        return True
    return False

def save_backup_file(df: pd.DataFrame, start_date_str: str, end_date_str: str) -> None:
    """
    현재 결과를 백업으로 저장합니다.
    
    Saves current processing results as backup file with date range in filename.
    
    Input:
        - df: pd.DataFrame - DataFrame containing processed HTML data
            - Ex: DataFrame with columns ['ID', 'Title', 'html_raw_text', 'html_raw_text_with_tags', ...]
        - start_date_str: str - Start date in YYMMDD format
            - Ex: '250508'
        - end_date_str: str - End date in YYMMDD format
            - Ex: '250509'
    
    Output: None (saves backup file)
        - backup/2_html_raw_text/2_html_raw_text_StartDateYYMMDD_EndDateYYMMDD.csv
    
    Example:
        >>> df = pd.DataFrame({'ID': ['250508_1'], 'Title': ['Test Paper'], 'html_raw_text': ['Content']})
        >>> save_backup_file(df, '250508', '250509')
        백업 파일 저장 완료: backup/2_html_raw_text/2_html_raw_text_StartDate250508_EndDate250509.csv
    """
    backup_path = f"{PAR_DIR}/backup/2_html_raw_text/2_html_raw_text_StartDate{start_date_str}_EndDate{end_date_str}.csv"
    df.to_csv(backup_path, index=False, encoding='utf-8-sig')
    print(f"백업 파일 저장 완료: {backup_path}")

def save_additional_formats(df: pd.DataFrame, start_date_str: str, end_date_str: str) -> None:
    """
    추가 형식으로 데이터를 저장하고 백업도 생성합니다.
    
    Saves HTML raw text data in multiple formats (pickle, txt) along with backups.
    
    Input:
        - df: pd.DataFrame - DataFrame containing HTML data
            - Ex: DataFrame with columns ['html_raw_text', 'html_raw_text_with_tags', 'html_raw_text_with_tags_filtered']
        - start_date_str: str - Start date in YYMMDD format
            - Ex: '250508'
        - end_date_str: str - End date in YYMMDD format
            - Ex: '250509'
    
    Output: None (saves files)
        - results/html_raw_text.p: Pickle format of text data
        - results/html_raw_text.txt: Text format with separators
        - backup versions of all formats
    
    Example:
        >>> df = pd.DataFrame({'html_raw_text': ['Text 1', 'Text 2'], 'html_raw_text_with_tags': ['<p>Text 1</p>', '<p>Text 2</p>']})
        >>> save_additional_formats(df, '250508', '250509')
        Pickle 파일 저장: results/html_raw_text.p (백업: backup/2_html_raw_text/html_raw_text_StartDate250508_EndDate250509.p)
        TXT 파일 저장: results/html_raw_text.txt (백업: backup/2_html_raw_text/html_raw_text_StartDate250508_EndDate250509.txt)
    """
    
    try:
        # html_raw_text pickle 저장
        html_raw_text_data = df['html_raw_text'].tolist()
        pickle_path = f"{PAR_DIR}/results/html_raw_text.p"
        backup_pickle_path = f"{PAR_DIR}/backup/2_html_raw_text/html_raw_text_StartDate{start_date_str}_EndDate{end_date_str}.p"
        
        with open(pickle_path, 'wb') as f:
            pickle.dump(html_raw_text_data, f)
        with open(backup_pickle_path, 'wb') as f:
            pickle.dump(html_raw_text_data, f)
        print(f"Pickle 파일 저장: {pickle_path} (백업: {backup_pickle_path})")
        
        # html_raw_text txt 저장
        txt_path = f"{PAR_DIR}/results/html_raw_text.txt"
        backup_txt_path = f"{PAR_DIR}/backup/2_html_raw_text/html_raw_text_StartDate{start_date_str}_EndDate{end_date_str}.txt"
        
        for path in [txt_path, backup_txt_path]:
            with open(path, 'w', encoding='utf-8') as f:
                for idx, text in enumerate(df['html_raw_text']):
                    f.write(f"=== Paper {idx + 1} ===\n")
                    f.write(str(text))
                    f.write("\n" + "="*50 + "\n\n")
        print(f"TXT 파일 저장: {txt_path} (백업: {backup_txt_path})")
        
        # html_raw_text_with_tags 저장
        save_with_tags_formats(df, start_date_str, end_date_str)
        save_filtered_formats(df, start_date_str, end_date_str)
        
    except Exception as e:
        print(f"추가 형식 저장 중 오류 발생: {str(e)}")

def save_with_tags_formats(df: pd.DataFrame, start_date_str: str, end_date_str: str) -> None:
    """
    html_raw_text_with_tags 데이터를 여러 형식으로 저장합니다.
    
    Saves HTML data with tags in pickle and text formats with backups.
    
    Input:
        - df: pd.DataFrame - DataFrame containing HTML data with tags
            - Ex: DataFrame with 'html_raw_text_with_tags' column
        - start_date_str: str - Start date in YYMMDD format
            - Ex: '250508'
        - end_date_str: str - End date in YYMMDD format
            - Ex: '250509'
    
    Output: None (saves files)
        - results/html_raw_text_with_tags.p: Pickle format
        - results/html_raw_text_with_tags.txt: Text format
        - Corresponding backup files
    
    Example:
        >>> df = pd.DataFrame({'html_raw_text_with_tags': ['<div>Content 1</div>', '<div>Content 2</div>']})
        >>> save_with_tags_formats(df, '250508', '250509')
        태그 포함 Pickle 저장: results/html_raw_text_with_tags.p (백업: backup/2_html_raw_text/html_raw_text_with_tags_StartDate250508_EndDate250509.p)
    """
    try:
        # Pickle format
        html_raw_text_with_tags_data = df['html_raw_text_with_tags'].tolist()
        pickle_path = f"{PAR_DIR}/results/html_raw_text_with_tags.p"
        backup_pickle_path = f"{PAR_DIR}/backup/2_html_raw_text/html_raw_text_with_tags_StartDate{start_date_str}_EndDate{end_date_str}.p"
        
        for path in [pickle_path, backup_pickle_path]:
            with open(path, 'wb') as f:
                pickle.dump(html_raw_text_with_tags_data, f)
        print(f"태그 포함 Pickle 저장: {pickle_path} (백업: {backup_pickle_path})")
        
        # TXT format
        txt_path = f"{PAR_DIR}/results/html_raw_text_with_tags.txt"
        backup_txt_path = f"{PAR_DIR}/backup/2_html_raw_text/html_raw_text_with_tags_StartDate{start_date_str}_EndDate{end_date_str}.txt"
        
        for path in [txt_path, backup_txt_path]:
            with open(path, 'w', encoding='utf-8') as f:
                for idx, text in enumerate(df['html_raw_text_with_tags']):
                    f.write(f"=== Paper {idx + 1} ===\n")
                    f.write(str(text))
                    f.write("\n" + "="*50 + "\n\n")
        print(f"태그 포함 TXT 저장: {txt_path} (백업: {backup_txt_path})")
        
    except Exception as e:
        print(f"태그 포함 형식 저장 중 오류 발생: {str(e)}")

def save_filtered_formats(df: pd.DataFrame, start_date_str: str, end_date_str: str) -> None:
    """
    html_raw_text_with_tags_filtered 데이터를 여러 형식으로 저장합니다.
    
    Saves filtered HTML data (with outer tags removed) in pickle and text formats with backups.
    
    Input:
        - df: pd.DataFrame - DataFrame containing filtered HTML data
            - Ex: DataFrame with 'html_raw_text_with_tags_filtered' column
        - start_date_str: str - Start date in YYMMDD format
            - Ex: '250508'
        - end_date_str: str - End date in YYMMDD format
            - Ex: '250509'
    
    Output: None (saves files)
        - results/html_raw_text_with_tags_filtered.p: Pickle format
        - results/html_raw_text_with_tags_filtered.txt: Text format
        - Corresponding backup files
    
    Example:
        >>> df = pd.DataFrame({'html_raw_text_with_tags_filtered': ['Content 1', 'Content 2']})
        >>> save_filtered_formats(df, '250508', '250509')
        필터링된 태그 Pickle 저장: results/html_raw_text_with_tags_filtered.p (백업: backup/2_html_raw_text/html_raw_text_with_tags_filtered_StartDate250508_EndDate250509.p)
    """
    try:
        # Pickle format
        html_raw_text_filtered_data = df['html_raw_text_with_tags_filtered'].tolist()
        pickle_path = f"{PAR_DIR}/results/html_raw_text_with_tags_filtered.p"
        backup_pickle_path = f"{PAR_DIR}/backup/2_html_raw_text/html_raw_text_with_tags_filtered_StartDate{start_date_str}_EndDate{end_date_str}.p"
        
        for path in [pickle_path, backup_pickle_path]:
            with open(path, 'wb') as f:
                pickle.dump(html_raw_text_filtered_data, f)
        print(f"필터링된 태그 Pickle 저장: {pickle_path} (백업: {backup_pickle_path})")
        
        # TXT format
        txt_path = f"{PAR_DIR}/results/html_raw_text_with_tags_filtered.txt"
        backup_txt_path = f"{PAR_DIR}/backup/2_html_raw_text/html_raw_text_with_tags_filtered_StartDate{start_date_str}_EndDate{end_date_str}.txt"
        
        for path in [txt_path, backup_txt_path]:
            with open(path, 'w', encoding='utf-8') as f:
                for idx, text in enumerate(df['html_raw_text_with_tags_filtered']):
                    f.write(f"=== Paper {idx + 1} ===\n")
                    f.write(str(text))
                    f.write("\n" + "="*50 + "\n\n")
        print(f"필터링된 태그 TXT 저장: {txt_path} (백업: {backup_txt_path})")
        
    except Exception as e:
        print(f"필터링된 태그 형식 저장 중 오류 발생: {str(e)}")

def save_intermediate_results(df: pd.DataFrame, output_file: str, processed_count: int) -> None:
    """
    중간 결과를 저장합니다.
    
    Saves intermediate processing results every 10 papers for recovery purposes.
    
    Input:
        - df: pd.DataFrame - Current state of DataFrame with processed papers
            - Ex: DataFrame with partially processed HTML data
        - output_file: str - Path to main output file
            - Ex: 'results/2_html_raw_text.csv'
        - processed_count: int - Number of papers processed so far
            - Ex: 20
    
    Output: None (saves files)
        - Main output file (overwritten)
        - Processing file for backup access
    
    Example:
        >>> df = pd.DataFrame({'ID': ['250508_1'], 'html_raw_text': ['Content']})
        >>> save_intermediate_results(df, 'results/2_html_raw_text.csv', 10)
        OK 중간 저장 완료 (10개 논문 처리됨): results/2_html_raw_text.csv
        OK 처리 중 파일 저장 완료: results/2_html_raw_text_processing.csv
    """
    try:
        # 메인 결과 파일 저장
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"OK 중간 저장 완료 ({processed_count}개 논문 처리됨): {output_file}")
        
        # 처리 중 파일도 추가로 저장 (파일이 열려있어도 접근 가능하도록)
        processing_file = f"{PAR_DIR}/results/2_html_raw_text_processing.csv"
        df.to_csv(processing_file, index=False, encoding='utf-8-sig')
        print(f"OK 처리 중 파일 저장 완료: {processing_file}")
        
    except Exception as e:
        print(f"ERROR 중간 저장 실패: {str(e)}")
        # 메인 파일 저장이 실패해도 processing 파일 저장 시도
        try:
            processing_file = f"{PAR_DIR}/results/2_html_raw_text_processing.csv"
            df.to_csv(processing_file, index=False, encoding='utf-8-sig')
            print(f"OK 처리 중 파일은 저장 성공: {processing_file}")
        except Exception as e2:
            print(f"ERROR 처리 중 파일 저장도 실패: {str(e2)}")

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    DataFrame에서 None, NaN, 빈칸이 있는 row를 제거합니다.
    
    Removes rows with missing, null, or empty values from DataFrame and reports cleaning statistics.
    
    Input:
        - df: pd.DataFrame - DataFrame to clean
            - Ex: DataFrame with potential None, NaN, or empty string values
    
    Output:
        - clean_df: pd.DataFrame - Cleaned DataFrame with invalid rows removed
            - Ex: DataFrame with only complete, valid rows
    
    Example:
        >>> df = pd.DataFrame({'ID': ['1', '2', ''], 'Title': ['Paper A', None, 'Paper C']})
        >>> clean_df = clean_dataframe(df)
        WARNING 잘못된 형식의 row 2개 발견:
          - Row 1: 빈 컬럼 ['Title']
          - Row 2: 빈 컬럼 ['ID']
        OK 2개의 잘못된 row를 제거했습니다.
        >>> len(clean_df)
        1
    """
    try:
        original_count = len(df)
        
        # 모든 컬럼에서 None, NaN, 빈 문자열 확인
        # fillna로 NaN을 빈 문자열로 변환 후 빈 문자열 체크
        df_temp = df.fillna('')
        
        # 각 row에서 빈 값이 있는지 확인
        mask = (df_temp == '').any(axis=1) | df.isnull().any(axis=1)
        invalid_rows = df[mask]
        
        if len(invalid_rows) > 0:
            print(f"WARNING 잘못된 형식의 row {len(invalid_rows)}개 발견:")
            for idx in invalid_rows.index:
                empty_cols = []
                for col in df.columns:
                    if pd.isna(df.at[idx, col]) or df.at[idx, col] == '':
                        empty_cols.append(col)
                print(f"  - Row {idx}: 빈 컬럼 {empty_cols}")
            
            # 유효한 row만 남기기
            df_clean = df[~mask].copy()
            removed_count = original_count - len(df_clean)
            print(f"OK {removed_count}개의 잘못된 row를 제거했습니다.")
            print(f"유효한 데이터: {len(df_clean)}개 (원본: {original_count}개)")
            return df_clean
        else:
            print("OK 모든 데이터가 유효합니다.")
            return df.copy()
            
    except Exception as e:
        print(f"ERROR 데이터 정리 중 오류 발생: {str(e)}")
        return df

def save_failed_papers(df: pd.DataFrame, start_date_str: str, end_date_str: str) -> None:
    """
    HTML 수집에 실패한 논문들을 별도 파일로 저장합니다.
    
    Identifies and saves papers where HTML extraction failed to separate files for analysis.
    
    Input:
        - df: pd.DataFrame - DataFrame containing all processed papers
            - Ex: DataFrame with 'html_raw_text' column containing 'NO_HTML' or 'NO_ltx_authors' for failed papers
        - start_date_str: str - Start date in YYMMDD format
            - Ex: '250508'
        - end_date_str: str - End date in YYMMDD format
            - Ex: '250509'
    
    Output: None (saves files)
        - results/2_2_failed_papers.csv: Failed papers main file
        - backup/2_html_raw_text/2_2_failed_papers_StartDateYYMMDD_EndDateYYMMDD.csv: Backup file
        - Console statistics about failure reasons
    
    Example:
        >>> df = pd.DataFrame({'html_raw_text': ['Content', 'NO_HTML', 'NO_ltx_authors'], 'Title': ['A', 'B', 'C']})
        >>> save_failed_papers(df, '250508', '250509')
        실패한 논문 2개를 별도 파일로 저장: results/2_2_failed_papers.csv
          - HTML 접근 불가: 1개
          - ltx_authors 태그 없음: 1개
    """
    try:
        # 실패한 논문들 필터링 (NO_HTML 또는 NO_ltx_authors)
        failed_df = df[(df['html_raw_text'] == 'NO_HTML') | (df['html_raw_text'] == 'NO_ltx_authors')].copy()
        
        if len(failed_df) > 0:
            # 실패한 논문들을 메인 결과 파일과 동일한 형태로 저장
            failed_output_file = f"{PAR_DIR}/results/2_2_failed_papers.csv"
            failed_df.to_csv(failed_output_file, index=False, encoding='utf-8-sig')
            print(f"실패한 논문 {len(failed_df)}개를 별도 파일로 저장: {failed_output_file}")
            
            # 백업도 생성
            backup_failed_path = f"{PAR_DIR}/backup/2_html_raw_text/2_2_failed_papers_StartDate{start_date_str}_EndDate{end_date_str}.csv"
            failed_df.to_csv(backup_failed_path, index=False, encoding='utf-8-sig')
            print(f"실패한 논문 백업 저장: {backup_failed_path}")
            
            # 실패 사유별 통계
            no_html_count = len(failed_df[failed_df['html_raw_text'] == 'NO_HTML'])
            no_ltx_authors_count = len(failed_df[failed_df['html_raw_text'] == 'NO_ltx_authors'])
            print(f"  - HTML 접근 불가: {no_html_count}개")
            print(f"  - ltx_authors 태그 없음: {no_ltx_authors_count}개")
        else:
            print("실패한 논문이 없습니다.")
    except Exception as e:
        print(f"실패한 논문 저장 중 오류 발생: {str(e)}")

def main() -> None:
    """
    메인 실행 함수
    
    Main execution function for Phase 2: HTML data collection and parsing.
    Orchestrates the complete workflow of extracting HTML content from arXiv papers.
    
    Input: None
    
    Output: None (processes and saves data)
        - Loads paper URLs from Phase 1 results
        - Extracts ltx_authors HTML content from each paper
        - Saves results in multiple formats (CSV, pickle, txt)
        - Creates backups and handles failed extractions
        - Provides processing statistics and progress tracking
    
    Processing flow:
        1. Load paper URLs from 1_URL_of_paper_abstractions.csv
        2. Extract HTML content from each arXiv HTML URL
        3. Process ltx_authors sections in 3 formats: text-only, with-tags, filtered
        4. Save intermediate results every 10 papers
        5. Clean data and save final results with backups
    
    Example:
        >>> main()
        ============================================================
        Phase 2: HTML 데이터 수집 및 파싱
        ============================================================
        총 25개의 논문 데이터를 로드했습니다.
        ...
        성공적으로 추출된 논문: 23개
        HTML 접근 불가능한 논문: 1개
        ltx_authors 태그가 없는 논문: 1개
        Phase 2 완료!
    """
    print("=" * 60)
    print("Phase 2: HTML 데이터 수집 및 파싱")
    print("=" * 60)
    
    # 디렉토리 생성
    create_directories()
    
    # CSV 파일 읽기
    input_file = f"{PAR_DIR}/results/1_URL_of_paper_abstractions.csv"
    output_file = f"{PAR_DIR}/results/2_html_raw_text.csv"
    
    try:
        df = pd.read_csv(input_file)
        print(f"총 {len(df)}개의 논문 데이터를 로드했습니다.")
        
        # Extract date range from the data
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
            
        print(f"논문 날짜 범위: {start_date} ~ {end_date}")
        
        # 기존 데이터 백업
        save_existing_data_to_backup(start_date, end_date)
        
        # 필요한 컬럼들 초기화
        df['html_raw_text'] = ""
        df['html_raw_text_with_tags'] = ""
        df['html_raw_text_with_tags_filtered'] = ""
        
        print(f"\n{'='*60}")
        print(f"HTML 데이터 수집 시작")
        print(f"총 {len(df)}개 논문 처리 예정")
        print(f"API 요청 간격: 5.2초")
        print(f"10개 논문마다 중간 저장 실행")
        print(f"{'='*60}")
        
        start_time = datetime.now()
        processed_count = 0
        
        # 각 HTML URL에서 ltx_authors 태그 내용 추출
        for idx, row in df.iterrows():
            html_url = row['html_url']
            paper_id = idx + 1
            
            # 진행률 계산
            progress = (paper_id / len(df)) * 100
            elapsed_time = (datetime.now() - start_time).total_seconds()
            estimated_total_time = elapsed_time * len(df) / paper_id if paper_id > 0 else 0
            remaining_time = estimated_total_time - elapsed_time
            
            print(f"\n[{paper_id:3d}/{len(df)}] ({progress:.1f}%) 처리 중: {html_url}")
            print(f"경과시간: {elapsed_time/60:.1f}분 | 예상 남은시간: {remaining_time/60:.1f}분")
            
            # HTML에서 ltx_authors 태그 추출 (텍스트와 HTML 태그 포함 버전)
            try:
                text_only, html_with_tags = extract_ltx_authors(html_url)
                df.at[idx, 'html_raw_text'] = text_only
                df.at[idx, 'html_raw_text_with_tags'] = html_with_tags
                
                # 외부 태그 제거 및 규칙 검사
                filtered_html, rule_violation = remove_outer_tags_and_check_rule(html_with_tags)
                df.at[idx, 'html_raw_text_with_tags_filtered'] = filtered_html
            except Exception as e:
                print(f"Paper {paper_id} - HTML 추출 실패: {str(e)}")
                df.at[idx, 'html_raw_text'] = "ERROR"
                df.at[idx, 'html_raw_text_with_tags'] = "ERROR"
                df.at[idx, 'html_raw_text_with_tags_filtered'] = "ERROR"
            
            processed_count += 1
            
            # 10개마다 중간 저장
            if processed_count % 10 == 0:
                save_intermediate_results(df, output_file, processed_count)
            
            # API 요청 간격 조절 (5.2초 대기)
            if paper_id < len(df):  # 마지막 요청이 아닌 경우만
                print(f"API 요청 간격 대기 중... (5.2초)")
                time.sleep(5.2)
        
        # 처리 완료 시간
        total_elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n총 처리 시간: {total_elapsed/60:.1f}분")
        
        # 데이터 정리: None, NaN, 빈칸이 있는 row 제거
        print(f"\n{'='*60}")
        print("데이터 품질 검사 및 정리")
        print(f"{'='*60}")
        df = clean_dataframe(df)
        
        # 메인 결과 파일 저장 (덮어쓰기)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"메인 결과 파일 저장 완료: {output_file}")
        
        # 백업 파일 저장
        save_backup_file(df, start_date, end_date)
        
        # 추가 형식으로 저장 (pickle, txt 등 - 모두 백업 포함)
        save_additional_formats(df, start_date, end_date)
        
        # 실패한 논문들을 별도 파일로 저장
        save_failed_papers(df, start_date, end_date)
        
        # 결과 통계
        no_html_count = len(df[df['html_raw_text'] == 'NO_HTML'])
        no_ltx_authors_count = len(df[df['html_raw_text'] == 'NO_ltx_authors'])
        success_count = len(df[(df['html_raw_text'] != 'NO_HTML') & (df['html_raw_text'] != 'NO_ltx_authors')])
        
        print(f"\n=== 처리 결과 ===")
        print(f"성공적으로 추출된 논문: {success_count}개")
        print(f"HTML 접근 불가능한 논문: {no_html_count}개")
        print(f"ltx_authors 태그가 없는 논문: {no_ltx_authors_count}개")
        print(f"전체 논문 수: {len(df)}개")
        print("Phase 2 완료!")
        
    except FileNotFoundError:
        print(f"입력 파일을 찾을 수 없습니다: {input_file}")
        print("먼저 Phase 1을 실행하여 1_URL_of_paper_abstractions.csv를 생성해주세요.")
    except Exception as e:
        print(f"오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    main()