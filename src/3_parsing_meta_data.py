import pandas as pd
import re
import json
from datetime import datetime
import os
import openai
from typing import List, Dict, Tuple, Optional, Any
import dotenv
from bs4 import BeautifulSoup

dotenv.load_dotenv()

GPT_MODEL = os.getenv('GPT_MODEL')
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
PAR_DIR = os.path.dirname(CUR_DIR)

def create_directories() -> None:
    """
    필요한 디렉토리들을 생성합니다.
    
    Creates necessary directories for metadata parsing and backup storage.
    
    Input: None
    
    Output: None (creates directories)
        - backup/3_parsing_meta_data: Backup directory for parsing results
    
    Example:
        >>> create_directories()
        디렉토리 생성 완료
    """
    os.makedirs("backup/3_parsing_meta_data", exist_ok=True)
    print("디렉토리 생성 완료")


def clean_html_for_gpt(html_content: str) -> str:
    """
    GPT에 입력하기 전에 HTML을 정리합니다.
    
    Cleans HTML content for GPT processing by removing unnecessary attributes and tags.
    
    Input:
        - html_content: str - Raw HTML content from ltx_authors section
            - Ex: '<span class="ltx_text" style="font-size:144%;">John Doe</span><img src="image.png" alt="photo"/>'
    
    Output:
        - cleaned_html: str - Cleaned HTML with only essential tags and content
            - Ex: '<span class="ltx_text">John Doe</span>'
    
    Processing steps:
        1. 메인 태그 요소만 남기고 style 등 부수적 요소 삭제
        2. 마지막 종료 태그 삭제
        3. 불필요한 태그들 완전 제거
        4. 연속된 공백과 줄바꿈 정리
    
    Example:
        >>> html = '<span style="color: blue;">University</span><img src="logo.png"/>'
        >>> clean_html_for_gpt(html)
        '<span>University</span>'
    """
    if html_content in ['NO_HTML', 'NO_ltx_authors']:
        return html_content
    
    try:
        # 1. Style 속성과 기타 부수적 속성 제거, class만 유지
        # style="font-size:144%;" 같은 패턴 제거
        cleaned = re.sub(r'\s+style="[^"]*"', '', html_content)
        cleaned = re.sub(r'\s+href="[^"]*"', '', cleaned)
        cleaned = re.sub(r'\s+title="[^"]*"', '', cleaned)
        cleaned = re.sub(r'\s+id="[^"]*"', '', cleaned)
        cleaned = re.sub(r'\s+height="[^"]*"', '', cleaned)
        cleaned = re.sub(r'\s+width="[^"]*"', '', cleaned)
        cleaned = re.sub(r'\s+src="[^"]*"', '', cleaned)
        cleaned = re.sub(r'\s+alt="[^"]*"', '', cleaned)
        
        # 2. 불필요한 태그들 완전 제거
        cleaned = re.sub(r'<img[^>]*/?>', '', cleaned)
        cleaned = re.sub(r'<br\s*class="[^"]*"\s*/?>', ' ', cleaned)
        
        # 3. 마지막 종료 태그들 제거 (맨 뒤의 </span>, </div> 등)
        lines = cleaned.strip().split('\n')
        filtered_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not re.match(r'^</[^>]+>$', line):  # 종료 태그만 있는 라인 제거
                filtered_lines.append(line)
        
        # 4. 연속된 공백과 줄바꿈 정리
        result = '\n'.join(filtered_lines)
        result = re.sub(r'\n\s*\n', '\n', result)  # 빈 줄 제거
        result = re.sub(r'  +', ' ', result)  # 연속 공백 제거
        
        return result.strip()
        
    except Exception as e:
        print(f"Error cleaning HTML: {str(e)}")
        return html_content

def extract_organizations_with_gpt(cleaned_html: str, paper_id: int) -> Tuple[List[str], Dict[str, int]]:
    """
    정리된 HTML을 ChatGPT에게 전달하여 기관 정보를 추출합니다.
    
    Uses ChatGPT API to extract organization names from cleaned HTML content.
    
    Input:
        - cleaned_html: str - Cleaned HTML content from ltx_authors section
            - Ex: '<span class="ltx_text">John Doe</span><span class="ltx_text">Stanford University</span>'
        - paper_id: int - Paper identifier for logging
            - Ex: 5
    
    Output:
        - organizations_list: List[str] - List of extracted organization names
            - Ex: ['Stanford University', 'Google Research']
        - token_usage_dict: Dict[str, int] - API token usage statistics
            - Ex: {'input_tokens': 150, 'output_tokens': 25}
    
    Example:
        >>> html = '<span>John Doe</span><span>MIT</span><span>jane.smith@stanford.edu</span>'
        >>> orgs, tokens = extract_organizations_with_gpt(html, 1)
        Paper 1 - Token usage: 120 input, 15 output
        Paper 1 - GPT response: ["MIT", "Stanford University"]
        >>> print(orgs)
        ['MIT', 'Stanford University']
        >>> print(tokens)
        {'input_tokens': 120, 'output_tokens': 15}
    """
    global GPT_MODEL

    if cleaned_html in ['NO_HTML', 'NO_ltx_authors']:
        return [], {'input_tokens': 0, 'output_tokens': 0}
    
    try:
        # OpenAI API 클라이언트 설정 (환경변수에서 API 키 읽기)
        client = openai.OpenAI()
        
        prompt = f"""Extract all organizations, institutions, universities, research institutes, and companies from the following HTML content from an academic paper's author section.

HTML Content:
{cleaned_html}

Requirements:
1. Extract ONLY the names of organizations/institutions/universities/companies
2. Do NOT include author names, email addresses, cities, or countries
3. Remove any duplicates
4. Return as a simple list format: ["Organization1", "Organization2", ...]
5. If no organizations are found, return an empty list: []
6. Focus on extracting: Universities, Colleges, Research Institutes, Companies, Laboratories, Centers

Examples of what TO extract:
- "Carnegie Mellon University"
- "Google"
- "MIT"
- "Microsoft Research"
- "Stanford University"

Examples of what NOT to extract:
- Author names like "John Smith"
- Email addresses
- City names like "Pittsburgh"
- Country names like "USA"

Return only the JSON list, no additional text."""

        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert at extracting organization names from academic paper author sections. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # 토큰 사용량 추출
        token_usage = {
            'input_tokens': response.usage.prompt_tokens,
            'output_tokens': response.usage.completion_tokens
        }
        print(f"Paper {paper_id} - Token usage: {token_usage['input_tokens']} input, {token_usage['output_tokens']} output")
        
        # 응답에서 조직 리스트 추출
        content = response.choices[0].message.content.strip()
        print(f"Paper {paper_id} - GPT response: {content}")
        
        try:
            # JSON 파싱 시도
            organizations = json.loads(content)
            if isinstance(organizations, list):
                # 중복 제거 및 정리
                unique_orgs = []
                for org in organizations:
                    if isinstance(org, str) and org.strip() and org not in unique_orgs:
                        unique_orgs.append(org.strip())
                return unique_orgs, token_usage
            else:
                print(f"Paper {paper_id} - GPT response is not a list")
                return [], token_usage
        except json.JSONDecodeError:
            print(f"Paper {paper_id} - Failed to parse GPT response as JSON")
            return [], token_usage
            
    except Exception as e:
        print(f"Paper {paper_id} - Error with GPT API: {str(e)}")
        return [], {'input_tokens': 0, 'output_tokens': 0}

def save_existing_data_to_backup(start_date_str: str, end_date_str: str) -> bool:
    """
    기존 데이터를 백업으로 저장한 후 삭제합니다.
    
    Backs up existing parsing metadata results before processing new data.
    
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
        기존 데이터 백업 저장: backup/3_parsing_meta_data/3_parsing_meta_data_StartDate250508_EndDate250509.csv
        >>> print(backup_created)
        True
    """
    output_file = f"{PAR_DIR}/results/3_parsing_meta_data.csv"
    if os.path.exists(output_file):
        existing_df = pd.read_csv(output_file)
        backup_path = f"{PAR_DIR}/backup/3_parsing_meta_data/3_parsing_meta_data_StartDate{start_date_str}_EndDate{end_date_str}.csv"
        existing_df.to_csv(backup_path, index=False, encoding='utf-8-sig')
        print(f"기존 데이터 백업 저장: {backup_path}")
        return True
    return False

def save_backup_file(df: pd.DataFrame, start_date_str: str, end_date_str: str) -> None:
    """
    현재 결과를 백업으로 저장합니다.
    
    Saves current metadata parsing results as backup file with date range in filename.
    
    Input:
        - df: pd.DataFrame - DataFrame containing parsed metadata with organization information
            - Ex: DataFrame with columns ['ID', 'Title', 'organization', 'input_tokens', 'output_tokens']
        - start_date_str: str - Start date in YYMMDD format
            - Ex: '250508'
        - end_date_str: str - End date in YYMMDD format
            - Ex: '250509'
    
    Output: None (saves backup file)
        - backup/3_parsing_meta_data/3_parsing_meta_data_StartDateYYMMDD_EndDateYYMMDD.csv
    
    Example:
        >>> df = pd.DataFrame({'ID': ['250508_1'], 'Title': ['Test Paper'], 'organization': ['["MIT"]']})
        >>> save_backup_file(df, '250508', '250509')
        백업 파일 저장 완료: backup/3_parsing_meta_data/3_parsing_meta_data_StartDate250508_EndDate250509.csv
    """
    backup_path = f"{PAR_DIR}/backup/3_parsing_meta_data/3_parsing_meta_data_StartDate{start_date_str}_EndDate{end_date_str}.csv"
    df.to_csv(backup_path, index=False, encoding='utf-8-sig')
    print(f"백업 파일 저장 완료: {backup_path}")

def save_intermediate_results(df: pd.DataFrame, output_file: str, processed_count: int) -> None:
    """
    중간 결과를 저장합니다.
    
    Saves intermediate metadata parsing results every 10 papers for recovery purposes.
    
    Input:
        - df: pd.DataFrame - Current state of DataFrame with processed metadata
            - Ex: DataFrame with partially processed organization data
        - output_file: str - Path to main output file
            - Ex: 'results/3_parsing_meta_data.csv'
        - processed_count: int - Number of papers processed so far
            - Ex: 20
    
    Output: None (saves files)
        - Main output file (overwritten with cleaned data)
        - Processing file for backup access
    
    Example:
        >>> df = pd.DataFrame({'ID': ['250508_1'], 'organization': ['["MIT"]'], 'input_tokens': [120]})
        >>> save_intermediate_results(df, 'results/3_parsing_meta_data.csv', 10)
        OK 중간 저장 완료 (10개 논문 처리됨): results/3_parsing_meta_data.csv
        OK 처리 중 파일 저장 완료: results/3_parsing_meta_data_processing.csv
    """
    try:
        # 불필요한 컬럼들 제거한 복사본 생성
        df_clean = clean_dataframe_for_save(df)
        
        # 메인 결과 파일 저장
        df_clean.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"OK 중간 저장 완료 ({processed_count}개 논문 처리됨): {output_file}")
        
        # 처리 중 파일도 추가로 저장 (파일이 열려있어도 접근 가능하도록)
        processing_file = f"{PAR_DIR}/results/3_parsing_meta_data_processing.csv"
        df_clean.to_csv(processing_file, index=False, encoding='utf-8-sig')
        print(f"OK 처리 중 파일 저장 완료: {processing_file}")
        
    except Exception as e:
        print(f"ERROR 중간 저장 실패: {str(e)}")
        # 메인 파일 저장이 실패해도 processing 파일 저장 시도
        try:
            df_clean = clean_dataframe_for_save(df)
            processing_file = f"{PAR_DIR}/results/3_parsing_meta_data_processing.csv"
            df_clean.to_csv(processing_file, index=False, encoding='utf-8-sig')
            print(f"OK 처리 중 파일은 저장 성공: {processing_file}")
        except Exception as e2:
            print(f"ERROR 처리 중 파일 저장도 실패: {str(e2)}")

def clean_dataframe_for_save(df: pd.DataFrame, use_ai_mode: Optional[bool] = None) -> pd.DataFrame:
    """
    DataFrame에서 불필요한 컬럼들을 제거하여 저장용 DataFrame을 생성합니다.
    
    Removes unnecessary columns (HTML, tokens) from DataFrame based on AI mode for clean CSV output.
    
    Input:
        - df: pd.DataFrame - Original DataFrame with all processing columns
            - Ex: DataFrame with columns ['ID', 'Title', 'html_raw_text', 'html_raw_text_with_tags', 'organization', 'input_tokens', 'output_tokens']
        - use_ai_mode: Optional[bool] - AI mode flag (None for auto-detection)
            - Ex: True (keep token columns), False (remove token columns), None (auto-detect)
    
    Output:
        - clean_df: pd.DataFrame - Cleaned DataFrame for saving
            - Ex: DataFrame with HTML columns removed, token columns based on mode
    
    Example:
        >>> df = pd.DataFrame({'ID': ['1'], 'html_raw_text': ['<div>'], 'organization': ['["MIT"]'], 'input_tokens': [120]})
        >>> clean_df = clean_dataframe_for_save(df, use_ai_mode=True)
        저장용 DataFrame에서 제거된 컬럼: ['html_raw_text', 'html_raw_text_with_tags', 'html_raw_text_with_tags_filtered']
        >>> 'html_raw_text' in clean_df.columns
        False
    """
    df_clean = df.copy()
    
    # 항상 제거할 HTML 관련 컬럼들
    columns_to_remove = [
        'html_raw_text',
        'html_raw_text_with_tags', 
        'html_raw_text_with_tags_filtered'
    ]
    
    # AI 모드가 아닌 경우 토큰 컬럼도 추가로 제거
    if use_ai_mode is None:
        # input_tokens 컬럼의 값으로 AI 모드 자동 감지
        if 'input_tokens' in df_clean.columns:
            first_token_value = df_clean['input_tokens'].iloc[0] if len(df_clean) > 0 else None
            if first_token_value == "Not AI Mode":
                use_ai_mode = False
            else:
                use_ai_mode = True
        else:
            use_ai_mode = True
    
    if not use_ai_mode:
        columns_to_remove.extend(['input_tokens', 'output_tokens'])
    
    # 존재하는 컬럼만 제거
    columns_to_remove = [col for col in columns_to_remove if col in df_clean.columns]
    if columns_to_remove:
        df_clean = df_clean.drop(columns=columns_to_remove)
        print(f"저장용 DataFrame에서 제거된 컬럼: {columns_to_remove}")
    
    return df_clean

def load_known_organizations():
    """환경변수에서 사전 설정된 기관 목록을 불러옵니다."""
    try:
        known_orgs_str = os.getenv('KNOWN_ORGANIZATIONS', '[]')
        known_orgs = json.loads(known_orgs_str)
        return [org.lower() for org in known_orgs] if isinstance(known_orgs, list) else []
    except json.JSONDecodeError:
        print("경고: KNOWN_ORGANIZATIONS 환경변수의 JSON 형식이 올바르지 않습니다.")
        return []

def remove_author_names_from_html(html_content: str, authors_text: str) -> str:
    """
    HTML 컨텐츠에서 저자 이름들을 제거합니다.
    
    Args:
        html_content: 원본 HTML 텍스트
        authors_text: Authors 컬럼의 텍스트 (세미콜론으로 구분된 저자들)
    
    Returns:
        저자 이름이 제거된 HTML 텍스트
    """
    if not html_content or not authors_text or html_content in ['NO_HTML', 'NO_ltx_authors']:
        return html_content
    
    try:
        # Authors 텍스트를 개별 저자로 분리
        authors = [author.strip() for author in authors_text.split(';')]
        
        # HTML과 저자 텍스트를 소문자로 변환 (비교용)
        html_lower = html_content.lower()
        result_html = html_content  # 원본 유지
        
        # 각 저자에 대해 처리
        for author in authors:
            if not author:
                continue
                
            author_lower = author.lower()
            
            # 저자 이름을 공백으로 나누어 개별 단어 처리
            author_words = author_lower.split()
            
            for word in author_words:
                if len(word) < 2:  # 너무 짧은 단어는 건너뛰기
                    continue
                    
                # 소문자 비교로 위치를 찾고, 원본에서 해당 위치의 텍스트 제거
                word_positions = []
                start = 0
                while True:
                    pos = html_lower.find(word, start)
                    if pos == -1:
                        break
                    # 단어 경계 확인 (앞뒤로 문자가 아닌 것)
                    if ((pos == 0 or not html_lower[pos-1].isalpha()) and 
                        (pos + len(word) >= len(html_lower) or not html_lower[pos + len(word)].isalpha())):
                        word_positions.append((pos, pos + len(word)))
                    start = pos + 1
                
                # 뒤에서부터 제거 (인덱스가 변하지 않도록)
                for start_pos, end_pos in reversed(word_positions):
                    # 원본 HTML에서 해당 위치의 실제 텍스트 제거
                    result_html = result_html[:start_pos] + ' ' * (end_pos - start_pos) + result_html[end_pos:]
                    html_lower = html_lower[:start_pos] + ' ' * (end_pos - start_pos) + html_lower[end_pos:]
        
        # 연속된 공백 정리
        result_html = re.sub(r'\s+', ' ', result_html)
        return result_html.strip()
        
    except Exception as e:
        print(f"저자 이름 제거 중 오류 발생: {str(e)}")
        return html_content

def extract_text_from_html(html_content: str) -> str:
    """
    HTML에서 태그를 제거하고 텍스트만 추출합니다.
    
    Extracts plain text content from HTML by removing all tags and preserving only text.
    
    Input:
        - html_content: str - Raw HTML content with tags
            - Ex: '<span class="ltx_text">John Doe</span><div>Stanford University</div>'
    
    Output:
        - text_only: str - Plain text with HTML tags removed
            - Ex: 'John Doe Stanford University'
    
    Example:
        >>> html = '<span>MIT</span><div>Computer Science</div><a href="link">Google</a>'
        >>> extract_text_from_html(html)
        'MIT Computer Science Google'
    """
    if html_content in ['NO_HTML', 'NO_ltx_authors'] or not html_content:
        return html_content if html_content else ""
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        text_only = soup.get_text(separator=' ', strip=True)
        # 연속된 공백 정리
        text_only = re.sub(r'\s+', ' ', text_only)
        return text_only.strip()
    except Exception as e:
        print(f"HTML 텍스트 추출 중 오류: {str(e)}")
        # 실패 시 기본적인 태그 제거로 fallback
        text_only = re.sub(r'<[^>]+>', ' ', html_content)
        text_only = re.sub(r'\s+', ' ', text_only)
        return text_only.strip()

def find_known_organizations_in_text(text: str, known_orgs_lower: List[str], original_known_orgs: List[str]) -> List[str]:
    """
    텍스트에서 사전 설정된 기관을 찾습니다.
    
    Args:
        text: 검색할 텍스트 (HTML 태그가 제거된 순수 텍스트)
        known_orgs_lower: 소문자로 변환된 사전 설정 기관 목록
        original_known_orgs: 원본 사전 설정 기관 목록
    
    Returns:
        찾아낸 기관들의 원본 이름 리스트
    """
    if not text:
        return []
    
    text_lower = text.lower()
    found_orgs = []
    
    for i, org_lower in enumerate(known_orgs_lower):
        if org_lower in text_lower:
            original_org = original_known_orgs[i]
            if original_org not in found_orgs:
                found_orgs.append(original_org)
    
    return found_orgs

def main() -> None:
    """
    메인 실행 함수
    
    Main execution function for Phase 3: Paper metadata parsing and organization extraction.
    Provides user choice between AI mode (GPT + known orgs) and known-only mode.
    
    Input: None (interactive user input for mode selection)
    
    Output: None (processes and saves data)
        - Mode 1 (AI): Uses GPT API + predefined organizations
            - Saves 3_parsing_meta_data_ai_full.csv (all results)
            - Saves 3_parsing_meta_data_ai_filtered.csv (known orgs only)
            - Saves 3_parsing_meta_data.csv (main file)
        - Mode 2 (Known-only): Uses only predefined organizations
            - Saves 3_parsing_meta_data.csv (filtered results)
    
    Processing flow:
        1. User selects processing mode (AI or known-only)
        2. Load HTML data from Phase 2 results
        3. Clean HTML and remove author names
        4. Extract organizations using selected method
        5. Save results with backups and statistics
    
    Example:
        >>> main()
        ============================================================
        Phase 3: 논문 메타데이터 파싱 및 기관 추출
        ============================================================
        처리 모드를 선택하세요:
        1. AI 모드 (GPT + 사전 기관): ChatGPT API와 사전 설정 기관 모두 사용
        2. 사전 기관 전용 모드: 사전 설정 기관 목록만 사용 (API 비용 없음)
        모드를 선택하세요 (1 또는 2): 1
        ...
        Phase 3 완료!
    """
    print("=" * 60)
    print("Phase 3: 논문 메타데이터 파싱 및 기관 추출")
    print("=" * 60)
    
    # 사용자 모드 선택
    print("처리 모드를 선택하세요:")
    print("1. AI 모드 (GPT + 사전 기관): ChatGPT API와 사전 설정 기관 모두 사용")
    print("2. 사전 기관 전용 모드: 사전 설정 기관 목록만 사용 (API 비용 없음)")
    
    while True:
        try:
            mode_choice = input("모드를 선택하세요 (1 또는 2): ").strip()
            if mode_choice in ['1', '2']:
                break
            else:
                print("올바른 선택지를 입력하세요 (1 또는 2)")
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            return
    
    use_ai_mode = (mode_choice == '1')
    
    input_file = f"{PAR_DIR}/results/2_html_raw_text.csv"
    output_file = f"{PAR_DIR}/results/3_parsing_meta_data.csv"
    
    # AI 모드일 때만 OpenAI API 키 확인
    if use_ai_mode and not os.getenv('OPENAI_API_KEY'):
        print("WARNING: AI 모드 선택 시 OPENAI_API_KEY 환경변수가 필요합니다.")
        print("환경변수를 설정하거나 .env 파일에 API 키를 추가해주세요.")
        print("또는 사전 기관 전용 모드(2)를 선택해주세요.")
        return
    
    print(f"\n{'='*60}")
    print(f"선택된 모드: {'AI 모드 (GPT + 사전 기관)' if use_ai_mode else '사전 기관 전용 모드'}")
    print(f"{'='*60}")
    
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
        
        # 디렉토리 생성 및 기존 데이터 백업
        save_existing_data_to_backup(start_date, end_date)
        
        # 사전 설정 기관 목록 불러오기
        known_orgs_str = os.getenv('KNOWN_ORGANIZATIONS', '[]')
        try:
            original_known_orgs = json.loads(known_orgs_str)
            known_orgs_lower = [org.lower() for org in original_known_orgs]
            print(f"사전 설정 기관 {len(original_known_orgs)}개 로드 완료")
        except json.JSONDecodeError:
            print("WARNING: KNOWN_ORGANIZATIONS 환경변수의 JSON 형식이 올바르지 않습니다.")
            original_known_orgs = []
            known_orgs_lower = []
        
        # 새로운 컬럼들 추가 (기존 컬럼들은 유지)
        df['organization'] = ""
        # 토큰 컬럼은 모드에 관계없이 항상 생성
        if use_ai_mode:
            df['input_tokens'] = 0
            df['output_tokens'] = 0
        else:
            df['input_tokens'] = "Not AI Mode"
            df['output_tokens'] = "Not AI Mode"
        
        print(f"\n{'='*60}")
        print(f"논문 메타데이터 파싱 시작")
        print(f"총 {len(df)}개 논문 처리 예정")
        print(f"10개 논문마다 중간 저장 실행")
        print(f"사전 설정 기관: {len(original_known_orgs)}개")
        print(f"처리 모드: {'AI + 사전 기관' if use_ai_mode else '사전 기관만'}")
        print(f"{'='*60}")
        
        start_time = datetime.now()
        processed_count = 0
        
        # 각 논문의 HTML을 처리하여 기관 정보 추출
        for idx, row in df.iterrows():
            html_filtered = row['html_raw_text_with_tags_filtered']
            authors_text = row.get('Authors', '')
            paper_id = idx + 1
            
            # 진행률 계산
            progress = (paper_id / len(df)) * 100
            elapsed_time = (datetime.now() - start_time).total_seconds()
            estimated_total_time = elapsed_time * len(df) / paper_id if paper_id > 0 else 0
            remaining_time = estimated_total_time - elapsed_time
            
            print(f"\n[{paper_id:3d}/{len(df)}] ({progress:.1f}%) Paper {paper_id}")
            print(f"경과시간: {elapsed_time/60:.1f}분 | 예상 남은시간: {remaining_time/60:.1f}분")
            
            # 1단계: HTML 정리 (Rule-based preprocessing)
            cleaned_html = clean_html_for_gpt(html_filtered)
            print(f"Cleaned HTML length: {len(cleaned_html)} characters")
            
            # 2단계: 저자 이름 제거
            html_without_authors = remove_author_names_from_html(cleaned_html, authors_text)
            print(f"HTML after author removal: {len(html_without_authors)} characters")
            
            # 3단계: HTML에서 텍스트만 추출 (태그 제거)
            text_only = extract_text_from_html(html_without_authors)
            print(f"Text-only content: {len(text_only)} characters")
            
            final_organizations = []  # 변수 초기화
            
            try:
                if use_ai_mode:
                    # 4단계: GPT를 통한 기관 정보 추출
                    gpt_organizations, token_usage = extract_organizations_with_gpt(cleaned_html, paper_id)
                    print(f"GPT 추출 기관 ({len(gpt_organizations)}개): {gpt_organizations}")
                    
                    # 토큰 사용량 저장
                    df.at[idx, 'input_tokens'] = token_usage['input_tokens']
                    df.at[idx, 'output_tokens'] = token_usage['output_tokens']
                    
                    # 5단계: 사전 설정 기관 매칭 (텍스트만에서)
                    known_found_orgs = find_known_organizations_in_text(
                        text_only, known_orgs_lower, original_known_orgs
                    )
                    print(f"사전 설정 기관 발견 ({len(known_found_orgs)}개): {known_found_orgs}")
                    
                    # 6단계: GPT 결과와 사전 설정 기관 통합
                    final_organizations = list(gpt_organizations)  # GPT 결과 복사
                    
                    # GPT가 누락한 사전 설정 기관 추가
                    for org in known_found_orgs:
                        if org not in final_organizations:
                            final_organizations.append(org)
                            print(f"INFO GPT가 누락한 기관 추가: {org}")
                else:
                    # 사전 기관 전용 모드: 사전 설정 기관만 검색 (텍스트만에서)
                    final_organizations = find_known_organizations_in_text(
                        text_only, known_orgs_lower, original_known_orgs
                    )
                    print(f"사전 설정 기관 발견 ({len(final_organizations)}개): {final_organizations}")
                
                # 결과를 JSON 형태로 저장
                df.at[idx, 'organization'] = json.dumps(final_organizations, ensure_ascii=False)
                
            except Exception as e:
                print(f"Paper {paper_id} - 기관 추출 실패: {str(e)}")
                # 기본값으로 설정
                final_organizations = []
                df.at[idx, 'organization'] = "[]"
                if use_ai_mode:
                    df.at[idx, 'input_tokens'] = 0
                    df.at[idx, 'output_tokens'] = 0
                # 사전 기관 전용 모드에서는 토큰 컬럼이 이미 "Not AI Mode"로 설정되어 있으므로 건드리지 않음
            
            processed_count += 1
            
            print(f"최종 기관 ({len(final_organizations)}개): {final_organizations}")
            
            # 10개마다 중간 저장
            if processed_count % 10 == 0:
                save_intermediate_results(df, output_file, processed_count)
            
        
        # 처리 완료 시간
        total_elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n총 처리 시간: {total_elapsed/60:.1f}분")
        
        # 결과 저장 로직
        if use_ai_mode:
            # AI 모드: GPT 추출 결과와 사전 기관 필터링 결과 모두 저장
            
            # 1) GPT 추출 결과 저장 (전체) - HTML 컬럼 제거
            df_clean_ai = clean_dataframe_for_save(df, use_ai_mode=True)
            ai_output_file = f"{PAR_DIR}/results/3_parsing_meta_data_ai_full.csv"
            df_clean_ai.to_csv(ai_output_file, index=False, encoding='utf-8-sig')
            print(f"AI 모드 전체 결과 저장: {ai_output_file}")
            
            # 2) 사전 기관 필터링된 결과 저장
            if original_known_orgs:
                df_filtered = df.copy()
                filtered_indices = []
                
                for idx, row in df_filtered.iterrows():
                    organizations = json.loads(row['organization']) if row['organization'] else []
                    # 사전 설정 기관과 매칭되는 논문만 필터링
                    if any(org for org in organizations if org.lower() in known_orgs_lower):
                        filtered_indices.append(idx)
                
                if filtered_indices:
                    df_filtered = df_filtered.iloc[filtered_indices]
                    df_filtered_clean = clean_dataframe_for_save(df_filtered, use_ai_mode=True)
                    filtered_output_file = f"{PAR_DIR}/results/3_parsing_meta_data_ai_filtered.csv"
                    df_filtered_clean.to_csv(filtered_output_file, index=False, encoding='utf-8-sig')
                    print(f"사전 기관 필터링된 결과 저장: {filtered_output_file} ({len(df_filtered)}개 논문)")
                else:
                    print("사전 기관과 일치하는 논문이 없어 필터링 파일을 생성하지 않습니다.")
            
            # 3) 메인 파일은 전체 결과로 설정 - HTML 컬럼 제거
            df_clean_main = clean_dataframe_for_save(df, use_ai_mode=True)
            df_clean_main.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"메인 결과 파일 저장 완료: {output_file}")
            
        else:
            # 사전 기관 전용 모드: 바로 필터링된 결과만 저장
            df_filtered = df.copy()
            filtered_indices = []
            
            for idx, row in df_filtered.iterrows():
                organizations = json.loads(row['organization']) if row['organization'] else []
                if organizations:  # 사전 기관이 발견된 논문만
                    filtered_indices.append(idx)
            
            if filtered_indices:
                df_filtered = df_filtered.iloc[filtered_indices]
                df_filtered_clean = clean_dataframe_for_save(df_filtered, use_ai_mode=False)
                df_filtered_clean.to_csv(output_file, index=False, encoding='utf-8-sig')
                print(f"사전 기관 필터링된 결과 저장: {output_file} ({len(df_filtered)}개 논문)")
            else:
                # 빈 결과도 저장
                pd.DataFrame().to_csv(output_file, index=False, encoding='utf-8-sig')
                print(f"사전 기관과 일치하는 논문이 없음: {output_file} (빈 파일 생성)")
        
        # 백업 파일 저장
        save_backup_file(df, start_date, end_date)
        
        # 결과 통계
        total_orgs = 0
        papers_with_orgs = 0
        total_input_tokens = 0
        total_output_tokens = 0
        
        print(f"\n=== 기관 추출 결과 통계 ===")
        for idx, row in df.iterrows():
            organizations = json.loads(row['organization']) if row['organization'] else []
            
            if use_ai_mode:
                input_tokens = row.get('input_tokens', 0)
                output_tokens = row.get('output_tokens', 0)
                # 숫자인 경우만 합계에 포함 (문자열 "Not AI Mode"는 제외)
                if isinstance(input_tokens, (int, float)) and isinstance(output_tokens, (int, float)):
                    total_input_tokens += input_tokens
                    total_output_tokens += output_tokens
                
                if organizations:
                    papers_with_orgs += 1
                    total_orgs += len(organizations)
                    print(f"Paper {idx+1}: {len(organizations)}개 기관 - {organizations} (토큰: {input_tokens}+{output_tokens})")
                else:
                    print(f"Paper {idx+1}: 기관 정보 없음 (토큰: {input_tokens}+{output_tokens})")
            else:
                if organizations:
                    papers_with_orgs += 1
                    total_orgs += len(organizations)
                    print(f"Paper {idx+1}: {len(organizations)}개 기관 - {organizations} (토큰: Not AI Mode)")
                else:
                    print(f"Paper {idx+1}: 기관 정보 없음 (토큰: Not AI Mode)")
        
        print(f"\n전체 추출된 기관 수: {total_orgs}개")
        print(f"기관 정보가 있는 논문: {papers_with_orgs}개")
        print(f"전체 논문 수: {len(df)}개")
        
        # 사전 기관과 매칭되는 논문 수 계산
        if original_known_orgs:
            papers_with_known_orgs = 0
            for idx, row in df.iterrows():
                organizations = json.loads(row['organization']) if row['organization'] else []
                if any(org for org in organizations if org.lower() in known_orgs_lower):
                    papers_with_known_orgs += 1
            print(f"사전 설정 기관과 일치하는 논문: {papers_with_known_orgs}개")
        
        if use_ai_mode:
            print(f"총 토큰 사용량: {total_input_tokens} input + {total_output_tokens} output = {total_input_tokens + total_output_tokens} total")
        else:
            print("사전 기관 전용 모드 - API 비용 없음")
        
        # 모든 기관 리스트 (중복 제거)
        all_organizations = set()
        for idx, row in df.iterrows():
            organizations = json.loads(row['organization']) if row['organization'] else []
            all_organizations.update(organizations)
        
        print(f"\n=== 전체 고유 기관 목록 ({len(all_organizations)}개) ===")
        for org in sorted(all_organizations):
            print(f"- {org}")
        
        print("Phase 3 완료!")
        
    except FileNotFoundError:
        print(f"WARNING: 입력 파일을 찾을 수 없습니다: {input_file}")
        print("먼저 Phase 2를 실행하여 2_html_raw_text.csv를 생성해주세요.")
    except Exception as e:
        print(f"WARNING: 오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    main()