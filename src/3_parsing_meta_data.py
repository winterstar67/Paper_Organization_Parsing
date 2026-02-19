import pandas as pd
import re
import json
from datetime import datetime
import os
from typing import List, Tuple, Optional
import dotenv
from bs4 import BeautifulSoup
from pipeline_config import results_dir

dotenv.load_dotenv()

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

def load_llm_model_blacklist() -> List[str]:
    """환경변수에서 제외할 LLM 모델 이름 목록을 불러옵니다."""
    try:
        llm_models_raw = os.getenv('LLM_MODEL_BLACKLIST', '[]')
        llm_models = json.loads(llm_models_raw)
        if isinstance(llm_models, list):
            return [model.strip().lower() for model in llm_models if isinstance(model, str) and model.strip()]
        return []
    except json.JSONDecodeError:
        print("경고: LLM_MODEL_BLACKLIST 환경변수의 JSON 형식이 올바르지 않습니다.")
        return []


def load_email_patterns() -> dict:
    """환경변수에서 EMAIL_PATTERNS를 불러옵니다."""
    try:
        patterns_str = os.getenv('EMAIL_PATTERNS', '{}')
        patterns = json.loads(patterns_str)
        return patterns if isinstance(patterns, dict) else {}
    except json.JSONDecodeError:
        print("경고: EMAIL_PATTERNS 환경변수의 JSON 형식이 올바르지 않습니다.")
        return {}


def match_email_pattern(text: str, pattern) -> bool:
    """
    단일 이메일 패턴을 텍스트에서 검색합니다 (Pattern 1: tight matching).

    - 문자열 패턴 (예: "@ethz.ch"): 단순 substring 검색
    - 리스트 패턴 (예: ["@", "eth", " "]): @\\S*keyword\\S* 정규식 사용
      → "@"와 keyword가 공백 없이 같은 토큰(이메일 도메인) 내에 있을 때만 매칭
      → "Netherlands" 같이 "@" 없이 나타나는 단어나,
         "Elizabeth" 같이 "@" 이후 별도 단어로 나타나는 기관명에는 매칭되지 않음
    """
    if isinstance(pattern, str):
        return pattern.lower() in text.lower()
    elif isinstance(pattern, list) and len(pattern) >= 2:
        anchor = re.escape(pattern[0])   # "@"
        keyword = re.escape(pattern[1])  # "eth", "mit" 등
        regex = anchor + r'\S*' + keyword + r'\S*'
        return bool(re.search(regex, text, re.IGNORECASE))
    return False


def find_organizations_by_email_patterns(
    text: str,
    email_patterns: dict,
    org_display_names: dict
) -> List[str]:
    """
    Step 1: EMAIL_PATTERNS를 사용하여 이메일 도메인 기반으로 기관을 찾습니다.

    각 기관의 패턴 중 하나라도 매칭되면 해당 기관을 결과에 추가합니다.
    이메일 주소가 있는 논문에서 정확하게 기관을 식별합니다.
    """
    if not text or not email_patterns:
        return []

    found_orgs = []
    for org_key, patterns in email_patterns.items():
        for pattern in patterns:
            if match_email_pattern(text, pattern):
                display_name = org_display_names.get(org_key, org_key)
                if display_name not in found_orgs:
                    found_orgs.append(display_name)
                break

    return found_orgs


def find_organizations_by_exact_name(
    text: str,
    email_patterns: dict,
    org_display_names: dict
) -> List[str]:
    """
    Step 2 (fallback): 기관명을 단어 경계(word boundary) 기준으로 정확히 매칭합니다.

    이메일 주소 없이 기관명만 기재된 논문을 위한 보조 탐색입니다.
    EMAIL_PATTERNS의 key 목록을 사용하여 텍스트를 소문자로 변환 후
    \\b(word boundary)로 정확한 단어 단위 매칭만 허용합니다.
    예: "eth"는 매칭되지만 "Netherlands", "Elizabeth"는 매칭되지 않음.
    """
    if not text or not email_patterns:
        return []

    text_lower = text.lower()
    found_orgs = []

    for org_key in email_patterns.keys():
        pattern = r'\b' + re.escape(org_key.lower()) + r'\b'
        if re.search(pattern, text_lower):
            display_name = org_display_names.get(org_key, org_key)
            if display_name not in found_orgs:
                found_orgs.append(display_name)

    return found_orgs

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

def main() -> None:
    """
    메인 실행 함수
    
    Main execution function for Phase 3: Paper metadata parsing and organization extraction.
    현재는 사전 정의된 기관 목록만 사용하여 결과를 생성합니다.
    
    Input: None
    
    Output: None (processes and saves data)
        - Saves 3_parsing_meta_data.csv (filtered results)
    
    Processing flow:
        1. Load HTML data from Phase 2 results
        2. Clean HTML and remove author names
        3. Extract organizations by matching predefined names
        4. Save results with backups and statistics
    
    Example:
        >>> main()
        ============================================================
        Phase 3: 논문 메타데이터 파싱 및 기관 추출
        ============================================================
        ...
        Phase 3 완료!
    """
    print("=" * 60)
    print("Phase 3: 논문 메타데이터 파싱 및 기관 추출")
    print("=" * 60)
    
    input_file = os.path.join(results_dir('Phase_2'), '2_html_raw_text.csv')
    output_file = os.path.join(results_dir('Phase_3'), '3_parsing_meta_data.csv')
    
    print(f"\n{'='*60}")
    print("선택된 모드: 사전 기관 전용 모드")
    print(f"{'='*60}")
    
    try:
        df = pd.read_csv(input_file)
        print(f"총 {len(df)}개의 논문 데이터를 로드했습니다.")
        
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

        # EMAIL_PATTERNS 로드 (Step 1 탐색용)
        email_patterns = load_email_patterns()
        org_display_names = {org.lower(): org for org in original_known_orgs}
        print(f"EMAIL_PATTERNS {len(email_patterns)}개 로드 완료")

        llm_model_blacklist = load_llm_model_blacklist()
        if llm_model_blacklist:
            print(f"LLM 모델 제외 목록 {len(llm_model_blacklist)}개 로드 완료")
        else:
            print("LLM 모델 제외 목록이 비어있습니다.")

        # 새로운 컬럼들 추가 (기존 컬럼들은 유지)
        df['organization'] = ""
        df['input_tokens'] = "Not AI Mode"
        df['output_tokens'] = "Not AI Mode"
        
        print(f"\n{'='*60}")
        print(f"논문 메타데이터 파싱 시작")
        print(f"총 {len(df)}개 논문 처리 예정")
        print(f"10개 논문마다 중간 저장 실행")
        print(f"사전 설정 기관: {len(original_known_orgs)}개")
        print("처리 모드: 사전 기관만")
        print(f"{'='*60}")
        
        start_time = datetime.now()
        processed_count = 0
        llm_filtered_indices: List[int] = []

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
            text_only_lower = text_only.lower() if text_only else ""

            final_organizations = []  # 변수 초기화

            try:
                # Step 1: 이메일 도메인 기반 탐색 (EMAIL_PATTERNS, Pattern 1)
                final_organizations = find_organizations_by_email_patterns(
                    text_only, email_patterns, org_display_names
                )
                if final_organizations:
                    print(f"[Step 1] 이메일 패턴으로 기관 발견 ({len(final_organizations)}개): {final_organizations}")
                else:
                    # Step 2: 이메일 없이 기관명만 있는 경우 - 단어 경계 정확 매칭
                    final_organizations = find_organizations_by_exact_name(
                        text_only, email_patterns, org_display_names
                    )
                    if final_organizations:
                        print(f"[Step 2] 정확한 기관명 매칭으로 발견 ({len(final_organizations)}개): {final_organizations}")
                    else:
                        print("[Step 1 & 2] 기관 발견 없음")

                # LLM 모델 이름 필터링
                llm_org_matches = []
                llm_name_hits = set()
                if final_organizations and llm_model_blacklist:
                    for org in final_organizations:
                        org_lower = org.lower()
                        for llm_name in llm_model_blacklist:
                            if llm_name in org_lower:
                                llm_org_matches.append(org)
                                llm_name_hits.add(llm_name)

                llm_text_hits = set()
                if text_only_lower and llm_model_blacklist:
                    for llm_name in llm_model_blacklist:
                        if llm_name in text_only_lower:
                            llm_text_hits.add(llm_name)

                if llm_org_matches or llm_text_hits:
                    detected_llm_names = sorted(llm_name_hits.union(llm_text_hits))
                    print(
                        f"LLM 모델 이름 감지로 논문 제외: {detected_llm_names}"
                        f" | 기관 문자열 일치: {llm_org_matches}"
                    )
                    llm_filtered_indices.append(idx)
                    final_organizations = []
                    df.at[idx, 'organization'] = "[]"
                else:
                    # 결과를 JSON 형태로 저장
                    df.at[idx, 'organization'] = json.dumps(final_organizations, ensure_ascii=False)

            except Exception as e:
                print(f"Paper {paper_id} - 기관 추출 실패: {str(e)}")
                final_organizations = []
                df.at[idx, 'organization'] = "[]"
            
            processed_count += 1
            
            print(f"최종 기관 ({len(final_organizations)}개): {final_organizations}")
            
        
        # 처리 완료 시간
        total_elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n총 처리 시간: {total_elapsed/60:.1f}분")

        if llm_filtered_indices:
            df = df.drop(index=llm_filtered_indices).reset_index(drop=True)
            print(f"LLM 모델 이름으로 제외된 논문: {len(llm_filtered_indices)}개")

        # 결과 저장 로직
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
            empty_df = pd.DataFrame(columns=df.columns)
            empty_df_clean = clean_dataframe_for_save(empty_df, use_ai_mode=False)

            empty_df_clean.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"사전 기관과 일치하는 논문이 없음: {output_file} (빈 파일이지만 컬럼 헤더는 포함)")
        
        # 결과 통계
        total_orgs = 0
        papers_with_orgs = 0
        
        print(f"\n=== 기관 추출 결과 통계 ===")
        for idx, row in df.iterrows():
            organizations = json.loads(row['organization']) if row['organization'] else []
            
            if organizations:
                papers_with_orgs += 1
                total_orgs += len(organizations)
                print(f"Paper {idx+1}: {len(organizations)}개 기관 - {organizations}")
            else:
                print(f"Paper {idx+1}: 기관 정보 없음")
        
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
