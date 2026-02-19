import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
import json
import pandas as pd
import time
import os
import pytz
from typing import List, Dict, Any, Optional, Tuple
from pipeline_config import results_dir, backup_dir, master_id_table_path, PROJECT_DIR

def create_directories() -> None:
    """
    Create necessary directories for results and backups

    Creates directory structure required for paper collection and backup storage.

    Input: None

    Output: None (creates directories)
        - results/{date}/Phase_1: 결과 저장 directory
        - backup/{date}/Phase_1: results와 동일하지만 backup용으로 저장하는 폴더 (날짜 정보까지 저장됨)

    Example:
        >>> create_directories()
        # Creates directories: results/{date}/Phase_1/, backup/{date}/Phase_1/
    """
    results_dir('Phase_1')
    backup_dir('Phase_1')

def parse_paper_data(paper_element: Any) -> Dict[str, str]:
    """
    Extract detailed paper information from HTML element
    
    Parses arXiv paper HTML element to extract metadata including URL, title, authors, dates, subjects, and abstract.
    
    Input:
        - paper_element: BeautifulSoup element (HTML element from arXiv search results)
            - Ex: <li class="arxiv-result">...</li> element containing paper information
    
    Output:
        - paper_data: Dict[str, str] - Dictionary containing paper metadata
            - Ex: {
                'abs_url': 'https://arxiv.org/abs/2401.12345',
                'html_url': 'https://arxiv.org/html/2401.12345',
                'pdf_url': 'https://arxiv.org/pdf/2401.12345',
                'Title': 'Advanced Machine Learning Techniques',
                'Authors': 'John Doe; Jane Smith',
                'Submitted': '8 Jan 2024',
                'Originally_announced': 'January 2024',
                'Subjects': 'Computer Science - Artificial Intelligence; Machine Learning',
                'Abstract': 'This paper presents novel approaches to machine learning...'
            }
    
    Example:
        >>> soup = BeautifulSoup(html_content, 'html.parser')
        >>> paper_elem = soup.find('li', class_='arxiv-result')
        >>> data = parse_paper_data(paper_elem)
        >>> print(data['Title'])
        'Advanced Machine Learning Techniques'
    """
    paper_data = {}
    
    # Extract arXiv URL
    url_element = paper_element.find('p', class_='list-title')
    if url_element:
        url_link = url_element.find('a', href=re.compile(r'https://arxiv\.org/abs'))
        abs_url = url_link.get('href') if url_link else ''
        paper_data['abs_url'] = abs_url
        # Generate HTML URL by replacing /abs/ with /html/
        paper_data['html_url'] = abs_url.replace('/abs/', '/html/') if abs_url else ''
        # Generate PDF URL by replacing /abs/ with /pdf/
        paper_data['pdf_url'] = abs_url.replace('/abs/', '/pdf/') if abs_url else ''
    else:
        paper_data['abs_url'] = ''
        paper_data['html_url'] = ''
        paper_data['pdf_url'] = ''
    
    # Extract title
    title_element = paper_element.find('p', class_='title')
    paper_data['Title'] = title_element.get_text(strip=True) if title_element else ''
    
    # Extract authors
    authors_element = paper_element.find('p', class_='authors')
    if authors_element:
        author_links = authors_element.find_all('a')
        authors = [link.get_text(strip=True) for link in author_links]
        paper_data['Authors'] = '; '.join(authors)
    else:
        paper_data['Authors'] = ''
    
    # Extract submission and announcement dates
    date_element = paper_element.find('p', class_='is-size-7')
    paper_data['Submitted'] = ''
    paper_data['Originally_announced'] = ''
    
    if date_element:
        date_text = date_element.get_text()
        # Parse submitted date
        submitted_match = re.search(r'Submitted\s+([^;]+)', date_text)
        if submitted_match:
            paper_data['Submitted'] = submitted_match.group(1).strip()
        
        # Parse announced date
        announced_match = re.search(r'originally announced\s+([^.]+)', date_text)
        if announced_match:
            paper_data['Originally_announced'] = announced_match.group(1).strip()
    
    # Extract subjects
    subjects_element = paper_element.find('div', class_='tags')
    if subjects_element:
        subject_tags = subjects_element.find_all('span', class_='tag')
        subjects = [tag.get_text(strip=True) for tag in subject_tags]
        paper_data['Subjects'] = '; '.join(subjects)
    else:
        paper_data['Subjects'] = ''
    
    # Extract abstract
    abstract_element = paper_element.find('span', class_='abstract-full has-text-grey-dark mathjax')
    if abstract_element:
        # Clean up excessive whitespace and line breaks
        abstract_text = abstract_element.get_text(strip=True)
        # Replace multiple whitespaces (including newlines) with single space
        abstract_text = re.sub(r'\s+', ' ', abstract_text)
        paper_data['Abstract'] = abstract_text
    else:
        paper_data['Abstract'] = ""
    
    # Extract comments
    comments_spans = paper_element.find_all('span', class_='has-text-black-bis has-text-weight-semibold')
    comments_found = False
    for span in comments_spans:
        span_text = span.get_text(strip=True)
        if span_text in ['Comments:', 'Comments:  ']:
            comments_text_element = span.find_next_sibling('span', class_='has-text-grey-dark mathjax')
            if comments_text_element:
                paper_data['Comments'] = comments_text_element.get_text(strip=True)
                comments_found = True
                break
    
    if not comments_found:
        paper_data['Comments'] = "Nothing"
    
    # Extract journal reference
    journal_found = False
    for span in comments_spans:  # Reuse the same spans
        span_text = span.get_text(strip=True)
        if span_text in ['Journal ref:', 'Journal ref: ']:
            # Check for sibling span first
            journal_text_element = span.find_next_sibling('span', class_='has-text-grey-dark mathjax')
            if journal_text_element:
                paper_data['Journal_ref'] = journal_text_element.get_text(strip=True)
                journal_found = True
                break
            else:
                # Get text directly from parent element after the "Journal ref:" span
                parent_element = span.parent
                if parent_element:
                    full_text = parent_element.get_text(strip=True)
                    journal_text = full_text.replace('Journal ref:', '').strip()
                    if journal_text:
                        paper_data['Journal_ref'] = journal_text
                        journal_found = True
                        break
    
    if not journal_found:
        paper_data['Journal_ref'] = "Nothing"
    
    return paper_data

def remove_internal_duplicates(papers_data: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Remove duplicates within the current collection based on Title
    
    Filters out duplicate papers by comparing titles, keeping only the first occurrence of each unique title.
    
    Input:
        - papers_data: List[Dict[str, str]] - List of paper dictionaries
            - Ex: [
                {'Title': 'Paper A', 'Authors': 'Author 1', ...},
                {'Title': 'Paper B', 'Authors': 'Author 2', ...},
                {'Title': 'Paper A', 'Authors': 'Author 3', ...}  # duplicate
            ]
    
    Output:
        - unique_papers: List[Dict[str, str]] - List without duplicate titles
            - Ex: [
                {'Title': 'Paper A', 'Authors': 'Author 1', ...},
                {'Title': 'Paper B', 'Authors': 'Author 2', ...}
            ]
    
    Example:
        >>> papers = [{'Title': 'AI Research', 'Authors': 'A'}, {'Title': 'AI Research', 'Authors': 'B'}]
        >>> unique = remove_internal_duplicates(papers)
        >>> len(unique)
        1
    """
    seen_titles = set()
    unique_papers = []
    
    for paper in papers_data:
        if paper['Title'] not in seen_titles:
            unique_papers.append(paper)
            seen_titles.add(paper['Title'])
    
    return unique_papers

def build_multi_subject_url(subjects: List[str], start_date: datetime, end_date: datetime, start: int = 0) -> str:
    """
    Build arXiv advanced search URL for multiple subjects

    Creates a single URL that searches for papers across multiple subject categories simultaneously.

    Input:
        - subjects: List[str] - List of arXiv subject categories
            - Ex: ['cs.AI', 'cs.LG', 'cs.CV', 'cs.CG']
        - start_date: datetime - Start date for paper search
            - Ex: datetime(2025, 5, 8)
        - end_date: datetime - End date for paper search
            - Ex: datetime(2025, 5, 9)
        - start: int - Result offset for pagination (0, 200, 400, ...)
            - Ex: 0 (first page), 200 (second page)

    Output:
        - url: str - Complete arXiv advanced search URL
            - Ex: 'https://arxiv.org/search/advanced?advanced=&terms-0-operator=AND&terms-0-term=cs.AI...'

    Example:
        >>> subjects = ['cs.AI', 'cs.LG', 'cs.CV']
        >>> start = datetime(2025, 5, 8)
        >>> end = datetime(2025, 5, 9)
        >>> url = build_multi_subject_url(subjects, start, end)
        >>> 'terms-0-term=cs.AI' in url and 'terms-1-term=cs.LG' in url
        True
    """
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    # Base URL with common parameters
    base_url = "https://arxiv.org/search/advanced?advanced="

    # Build terms parameters for each subject
    terms_params = []
    for i, subject in enumerate(subjects):
        if i == 0:
            # First subject uses AND operator
            terms_params.extend([
                f"terms-{i}-operator=AND",
                f"terms-{i}-term={subject}",
                f"terms-{i}-field=all"
            ])
        else:
            # Subsequent subjects use OR operator
            terms_params.extend([
                f"terms-{i}-operator=OR",
                f"terms-{i}-term={subject}",
                f"terms-{i}-field=all"
            ])

    # Common parameters
    common_params = [
        "classification-physics_archives=all",
        "classification-include_cross_list=include",
        f"date-filter_by=date_range",
        "date-year=",
        f"date-from_date={start_str}",
        f"date-to_date={end_str}",
        "date-date_type=submitted_date_first",
        "abstracts=show",
        "size=200",
        "order=-announced_date_first",
        f"start={start}"
    ]

    # Combine all parameters
    all_params = terms_params + common_params
    url = base_url + "&" + "&".join(all_params)

    return url

def _parse_total_results(soup: BeautifulSoup) -> Optional[int]:
    """
    Parse total result count from arXiv search results page.

    Extracts the total number from text like "Showing 1–200 of 217 results".

    Input:
        - soup: BeautifulSoup - Parsed HTML of an arXiv search results page

    Output:
        - total: Optional[int] - Total number of results, or None if not found
            - Ex: 217

    Example:
        >>> soup = BeautifulSoup('<h1 class="title is-clearfix">Showing 1–200 of 217 results</h1>', 'html.parser')
        >>> _parse_total_results(soup)
        217
    """
    title_el = soup.find('h1', class_='title')
    if title_el:
        match = re.search(r'of\s+([\d,]+)\s+results', title_el.get_text())
        if match:
            return int(match.group(1).replace(',', ''))
    return None

def fetch_arxiv_data(subjects: List[str], start_date: datetime, end_date: datetime) -> Optional[List[Dict[str, str]]]:
    """
    Fetch detailed arXiv paper data for given subjects and date range (all pages).

    Sends HTTP requests to arXiv advanced search API, automatically paginating
    through all result pages (200 results per page) to collect every paper.

    Input:
        - subjects: List[str] - List of arXiv subject categories
            - Ex: ['cs.AI', 'cs.LG', 'cs.CV', 'cs.CG']
        - start_date: datetime - Start date for paper search
            - Ex: datetime(2025, 5, 8)
        - end_date: datetime - End date for paper search
            - Ex: datetime(2025, 5, 9)

    Output:
        - papers_data: Optional[List[Dict[str, str]]] - List of paper dictionaries or None if request failed
            - Ex: [
                {
                    'abs_url': 'https://arxiv.org/abs/2405.12345',
                    'html_url': 'https://arxiv.org/html/2405.12345',
                    'Title': 'Novel AI Approach',
                    'Authors': 'John Doe; Jane Smith',
                    'Submitted': '8 May 2025',
                    'Originally_announced': 'May 2025',
                    'Subjects': 'Computer Science - Artificial Intelligence',
                    'Abstract': 'This paper presents...',
                    'Comments': 'Accepted to ICML 2025',
                    'Journal_ref': 'Nothing',
                    'collected_at_kst': '2025-05-08 14:30:25 KST',
                    'collected_at_est': '2025-05-08 01:30:25 EST/EDT'
                }
            ]

    Example:
        >>> papers = fetch_arxiv_data(['cs.AI', 'cs.LG'], datetime(2025, 5, 8), datetime(2025, 5, 9))
        >>> print(len(papers)) if papers else print('Request failed')
        15
    """
    PAGE_SIZE = 200
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    # Get collection time in both timezones
    korea_tz = pytz.timezone('Asia/Seoul')
    us_tz = pytz.timezone('US/Eastern')
    korea_time = datetime.now(korea_tz).strftime('%Y-%m-%d %H:%M:%S KST')
    us_time = datetime.now(us_tz).strftime('%Y-%m-%d %H:%M:%S EST/EDT')

    all_papers: List[Dict[str, str]] = []
    offset = 0
    total_results = None

    while True:
        url = build_multi_subject_url(subjects, start_date, end_date, start=offset)
        page_num = offset // PAGE_SIZE + 1
        print(f"요청 URL (page {page_num}): {url}")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed for {subjects} from {start_str} to {end_str} (page {page_num}): {str(e)}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # Parse total results on the first page
        if total_results is None:
            total_results = _parse_total_results(soup)
            if total_results is not None:
                total_pages = (total_results + PAGE_SIZE - 1) // PAGE_SIZE
                print(f"총 {total_results}개 논문 발견 ({total_pages} 페이지)")
            else:
                # Fallback: if we can't parse total, treat as single page
                total_results = PAGE_SIZE

        paper_elements = soup.find_all('li', class_='arxiv-result')

        if not paper_elements:
            if offset == 0:
                print(f"No papers found for {subjects} from {start_str} to {end_str}")
                return []
            break

        for paper_element in paper_elements:
            paper_data = parse_paper_data(paper_element)
            paper_data['collected_at_kst'] = korea_time
            paper_data['collected_at_est'] = us_time
            all_papers.append(paper_data)

        print(f"  페이지 {page_num}: {len(paper_elements)}개 논문 수집 (누적 {len(all_papers)}개)")

        # Move to next page if there are more results
        offset += PAGE_SIZE
        if offset >= total_results:
            break

        # Polite delay between pages
        time.sleep(3)

    # Validation: compare collected count against webpage total
    collected_count = len(all_papers)
    if total_results is not None:
        if collected_count == total_results:
            validation_status = "PASS"
            print(f"✅ 수집 검증 통과: 웹페이지 표시 {total_results}개 == 실제 수집 {collected_count}개")
        else:
            validation_status = "FAIL"
            print(f"⚠️ 수집 검증 실패: 웹페이지 표시 {total_results}개 != 실제 수집 {collected_count}개 (차이: {total_results - collected_count}개)")
    else:
        validation_status = "UNKNOWN"
        print(f"⚠️ 수집 검증 불가: 웹페이지에서 총 논문 수를 파싱하지 못했습니다. 실제 수집: {collected_count}개")

    # Save validation report for downstream phases (e.g., email notification)
    validation_report = {
        "webpage_total": total_results,
        "collected_count": collected_count,
        "validation_status": validation_status,
        "timestamp": datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')
    }
    validation_path = os.path.join(results_dir('Phase_1'), 'collection_validation.json')
    with open(validation_path, 'w', encoding='utf-8') as f:
        json.dump(validation_report, f, ensure_ascii=False, indent=2)
    print(f"검증 리포트 저장: {validation_path}")

    return all_papers

def load_or_create_id_table() -> pd.DataFrame:
    """
    Load existing ID_TABLE.csv or create new one if it doesn't exist

    Attempts to load ID table from CSV file, creates empty DataFrame if file doesn't exist.

    Input: None

    Output:
        - DataFrame: ID table with ID, Paper_Title, Submitted, and created_datetime_UTC9 columns
            - Ex: pandas.DataFrame with columns ['ID', 'Paper_Title', 'Submitted', 'created_datetime_UTC9']
                ID          | Paper_Title              | Submitted    | created_datetime_UTC9
                '250508_1'  | 'Advanced Machine Learning' | '8 May 2025' | '2025-05-08 14:30:25'
                '250508_2'  | 'Deep Neural Networks'      | '8 May 2025' | '2025-05-08 14:30:25'

    Example:
        >>> df = load_or_create_id_table()
        >>> print(df.columns.tolist())
        ['ID', 'Paper_Title', 'Submitted', 'created_datetime_UTC9']
    """
    id_table_path = master_id_table_path()

    if os.path.exists(id_table_path):
        return pd.read_csv(id_table_path, encoding='utf-8-sig')
    else:
        # Create empty ID table
        return pd.DataFrame(columns=['ID', 'Paper_Title', 'Submitted', 'created_datetime_UTC9'])

def generate_paper_id(date_str: str, sequence_num: int) -> str:
    """
    Generate paper ID in format: YYMMDD_sequence
    
    Creates unique paper identifier combining date and sequence number.
    
    Input:
        - date_str: str - Date in YYYY-MM-DD format
            - Ex: '2025-08-30'
        - sequence_num: int - Sequence number starting from 1
            - Ex: 1
    
    Output:
        - paper_id: str - Generated ID in YYMMDD_sequence format
            - Ex: '250830_1'
    
    Example:
        >>> generate_paper_id('2025-08-30', 1)
        '250830_1'
        >>> generate_paper_id('2025-12-25', 15)
        '251225_15'
    """
    # Convert YYYY-MM-DD to YYMMDD
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    date_short = date_obj.strftime('%y%m%d')
    return f"{date_short}_{sequence_num}"

def get_next_sequence_number(id_table_df: pd.DataFrame, date_str: str) -> int:
    """
    Get next sequence number for the given date
    
    Finds the highest sequence number used for a specific date and returns the next available number.
    
    Input:
        - id_table_df: pd.DataFrame - Current ID table containing existing IDs
            - Ex: DataFrame with columns ['ID', 'Paper_Title'] where IDs like '250830_1', '250830_2'
        - date_str: str - Date in YYYY-MM-DD format
            - Ex: '2025-08-30'
    
    Output:
        - next_sequence: int - Next available sequence number for the date
            - Ex: 3 (if '250830_1' and '250830_2' already exist)
    
    Example:
        >>> df = pd.DataFrame({'ID': ['250830_1', '250830_3'], 'Paper_Title': ['Paper A', 'Paper B']})
        >>> get_next_sequence_number(df, '2025-08-30')
        4
        >>> get_next_sequence_number(pd.DataFrame(columns=['ID', 'Paper_Title']), '2025-08-30')
        1
    """
    if id_table_df.empty:
        return 1
    
    # Convert date to YYMMDD format for comparison
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    date_prefix = date_obj.strftime('%y%m%d')
    
    # Find existing IDs for this date
    existing_ids = id_table_df[id_table_df['ID'].str.startswith(date_prefix + '_', na=False)]
    
    if existing_ids.empty:
        return 1
    
    # Extract sequence numbers and find the maximum
    sequence_nums = []
    for id_val in existing_ids['ID']:
        try:
            seq_num = int(id_val.split('_')[1])
            sequence_nums.append(seq_num)
        except (IndexError, ValueError):
            continue
    
    return max(sequence_nums) + 1 if sequence_nums else 1

def save_results(papers_data: List[Dict[str, str]], start_date: datetime, end_date: datetime) -> None:
    """
    Save results to CSV, overwriting existing file
    
    Processes paper data, generates IDs, filters duplicates, and saves to CSV files with backup.
    
    Input:
        - papers_data: List[Dict[str, str]] - List of paper dictionaries
            - Ex: [
                {
                    'Title': 'AI Research Paper',
                    'Authors': 'John Doe; Jane Smith',
                    'abs_url': 'https://arxiv.org/abs/2405.12345',
                    'Abstract': 'This paper presents...',
                    'collected_at_kst': '2025-05-08 14:30:25 KST',
                    'collected_at_est': '2025-05-08 01:30:25 EST/EDT'
                }
            ]
        - start_date: datetime - Start date of collection period
            - Ex: datetime(2025, 5, 8)
        - end_date: datetime - End date of collection period
            - Ex: datetime(2025, 5, 9)
    
    Output: None (saves files)
        - results/1_URL_of_paper_abstractions.csv: Main results file (overwritten)
        - results/ID_TABLE.csv: Updated ID table
        - backup/1_URL_of_paper_abstractions/1_URL_of_paper_abstractions_StartDateYYMMDD_EndDateYYMMDD.csv: Backup file
        - backup/ID_TABLE/ID_TABLE_YYMMDD.csv: ID table backup
    
    Example:
        >>> papers = [{'Title': 'Test Paper', 'Authors': 'Author', ...}]
        >>> save_results(papers, datetime(2025, 5, 8), datetime(2025, 5, 9))
        # Saves CSV files with generated IDs and backups
    """
    if not papers_data:
        print("No data to save")
        return
    
    csv_path = os.path.join(results_dir('Phase_1'), '1_URL_of_paper_abstractions.csv')
    
    # Create DataFrame with new data
    new_df = pd.DataFrame(papers_data)
    
    # Reorder columns to match the required format (including PDF URL and extended metadata)
    column_order = ['collected_at_kst', 'collected_at_est', 'abs_url', 'html_url', 'pdf_url', 'Title', 'Authors', 
                   'Submitted', 'Originally_announced', 'Subjects', 'Abstract', 'Comments', 'Journal_ref']
    new_df = new_df[column_order]
    
    # Load or create ID table
    id_table_df = load_or_create_id_table()
    
    # Filter out papers that already exist in ID table
    new_papers = []
    skipped_papers = []
    existing_titles = set(id_table_df['Paper_Title'].str.lower().str.strip()) if not id_table_df.empty else set()
    
    for paper in papers_data:
        paper_title_clean = paper['Title'].lower().strip()
        if paper_title_clean not in existing_titles:
            new_papers.append(paper)
        else:
            skipped_papers.append(paper)
    
    if not new_papers:
        print("모든 논문이 이미 ID 테이블에 존재합니다. 새로운 논문이 없습니다.")
        return
    
    print(f"새로운 논문: {len(new_papers)}개")
    print(f"중복으로 스킵된 논문: {len(skipped_papers)}개")
    
    # Create DataFrame with new papers only
    new_df = pd.DataFrame(new_papers)
    
    # Reorder columns to match the required format (including PDF URL and extended metadata)
    column_order = ['collected_at_kst', 'collected_at_est', 'abs_url', 'html_url', 'pdf_url', 'Title', 'Authors', 
                   'Submitted', 'Originally_announced', 'Subjects', 'Abstract', 'Comments', 'Journal_ref']
    new_df = new_df[column_order]
    
    # Generate IDs for new papers and update ID table
    paper_ids = []
    current_date = datetime.now().strftime('%Y-%m-%d')

    # Get current time in UTC+9 for created_datetime_UTC9
    utc9_tz = pytz.timezone('Asia/Seoul')
    created_datetime_utc9 = datetime.now(utc9_tz).strftime('%Y-%m-%d %H:%M:%S')

    # Get starting sequence number for current date
    start_sequence_num = get_next_sequence_number(id_table_df, current_date)

    for i, paper in enumerate(new_papers):
        # Generate sequential ID (start_sequence_num + i)
        sequence_num = start_sequence_num + i
        paper_id = generate_paper_id(current_date, sequence_num)
        paper_ids.append(paper_id)

        # Add to ID table (use original submitted date format)
        new_row = pd.DataFrame({
            'ID': [paper_id],
            'Paper_Title': [paper['Title']],
            'Submitted': [paper['Submitted']],
            'created_datetime_UTC9': [created_datetime_utc9]
        })
        id_table_df = pd.concat([id_table_df, new_row], ignore_index=True)
    
    # Add ID column to new_df
    new_df.insert(0, 'ID', paper_ids)
    
    # Save updated ID table (master + snapshot copy in Phase_1)
    id_table_path = master_id_table_path()
    id_table_df.to_csv(id_table_path, index=False, encoding='utf-8-sig')
    print(f"ID 테이블 업데이트 완료: {id_table_path} (총 {len(id_table_df)}개 논문)")

    id_table_snapshot_path = os.path.join(results_dir('Phase_1'), 'ID_TABLE.csv')
    id_table_df.to_csv(id_table_snapshot_path, index=False, encoding='utf-8-sig')
    print(f"ID 테이블 스냅샷 저장 완료: {id_table_snapshot_path}")

    # Backup ID table with current date
    current_date_short = datetime.now().strftime('%y%m%d')
    id_table_backup_path = os.path.join(backup_dir('Phase_1'), f'ID_TABLE_{current_date_short}.csv')
    id_table_df.to_csv(id_table_backup_path, index=False, encoding='utf-8-sig')
    print(f"ID 테이블 백업 완료: {id_table_backup_path}")

    # Overwrite results file with only new data (no accumulation)
    new_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"결과 파일 저장 완료 (덮어쓰기): {csv_path}")

    # Save backup of new data only with date range format
    start_date_str = start_date.strftime('%y%m%d')
    end_date_str = end_date.strftime('%y%m%d')
    backup_path = os.path.join(backup_dir('Phase_1'), f'1_URL_of_paper_abstractions_StartDate{start_date_str}_EndDate{end_date_str}.csv')
    new_df.to_csv(backup_path, index=False, encoding='utf-8-sig')
    print(f"백업 파일 저장 완료: {backup_path}")
    
    print(f"새로 수집된 논문 수: {len(new_df)}")

def save_failed_requests(failed_requests: List[Dict[str, str]], start_date: datetime, end_date: datetime) -> None:
    """
    Save failed request information to CSV files
    
    Records information about failed arXiv requests for later retry or analysis.
    
    Input:
        - failed_requests: List[Dict[str, str]] - List of failed request information
            - Ex: [
                {
                    'Subject': 'cs.AI',
                    'Start_date': '2025-05-08',
                    'End_date': '2025-05-09',
                    'Failed_time': '2025-05-08 14:30:25'
                }
            ]
        - start_date: datetime - Start date of collection period
            - Ex: datetime(2025, 5, 8)
        - end_date: datetime - End date of collection period  
            - Ex: datetime(2025, 5, 9)
    Output: None (saves files)
        - results/Failed_list.csv: Main failed requests file (overwritten)
        - backup/Failed/Failed_list_StartDateYYMMDD_EndDateYYMMDD.csv: Backup file
    
    Example:
        >>> failed = [{'Subject': 'cs.AI', 'Start_date': '2025-05-08', 'End_date': '2025-05-09', 'Failed_time': '2025-05-08 14:30:25'}]
        >>> save_failed_requests(failed, datetime(2025, 5, 8), datetime(2025, 5, 9))
        # Saves failed request information to CSV files
    """
    if not failed_requests:
        return  # No failed requests to save
    
    failed_df = pd.DataFrame(failed_requests)
    
    # Overwrite main failed list
    failed_csv_path = os.path.join(results_dir('Phase_1'), 'Failed_list.csv')
    failed_df.to_csv(failed_csv_path, index=False, encoding='utf-8-sig')
    print(f"실패한 요청 저장: {failed_csv_path}")

    # Save backup with date range format
    start_date_str = start_date.strftime('%y%m%d')
    end_date_str = end_date.strftime('%y%m%d')
    backup_path = os.path.join(backup_dir('Phase_1'), f'Failed_list_StartDate{start_date_str}_EndDate{end_date_str}.csv')
    failed_df.to_csv(backup_path, index=False, encoding='utf-8-sig')
    print(f"실패한 요청 백업 저장: {backup_path}")

def main() -> None:
    """
    Main function to execute arXiv paper collection workflow
    
    Orchestrates the complete paper collection process including directory setup, date range generation,
    paper fetching from multiple subjects, duplicate removal, and result saving.
    
    Input: None
    
    Output: None (saves collected data to files)
        - Collects papers from yesterday (US Eastern time) for subjects: cs.AI, cs.LG, cs.CL
        - Saves results to CSV files with generated IDs
        - Creates backups and handles failed requests
    
    Example:
        >>> main()
        ============================================================
        Phase 1: arXiv 논문 URL 및 메타데이터 수집
        ============================================================
        수집 기간: 2025-08-29 ~ 2025-08-30
        대상 주제: cs.AI, cs.LG, cs.CL
        ...
        Phase 1 완료!
    """
    print("=" * 60)
    print("Phase 1: arXiv 논문 URL 및 메타데이터 수집")
    print("=" * 60)
    
    create_directories()
    
    # Get current time in different timezones
    korea_tz = pytz.timezone('Asia/Seoul')
    us_tz = pytz.timezone('US/Eastern')
    
    korea_now = datetime.now(korea_tz)
    us_now = datetime.now(us_tz)
    
    print(f"프로그램 실행 시각 (한국 시간): {korea_now.strftime('%Y-%m-%d %H:%M:%S KST')}")
    print(f"프로그램 실행 시각 (미국 뉴욕 시간): {us_now.strftime('%Y-%m-%d %H:%M:%S EST/EDT')}")
    
    # Optional manual date range via env vars (YYYY-MM-DD)
    env_start = os.getenv("PAPER_START_DATE", "").strip()
    env_end = os.getenv("PAPER_END_DATE", "").strip()

    if env_start and env_end:
        try:
            start_target_date = datetime.strptime(env_start, "%Y-%m-%d").date()
            end_target_date = datetime.strptime(env_end, "%Y-%m-%d").date()
            if end_target_date < start_target_date:
                raise ValueError("END date is earlier than START date")
            print(f"수동 기간 설정: {env_start} ~ {env_end}")
        except Exception as e:
            print(f"WARNING 수동 기간 설정 실패: {e}")
            env_start = ""
            env_end = ""

    discovered_papers = None

    if not (env_start and env_end):
        # Calculate search date range - search backwards from yesterday until papers found
        # Always search day by day, maximum 2 weeks back
        us_today = us_now.date()
        us_yesterday = us_today - timedelta(days=1)  # arXiv doesn't publish today's papers

        print("어제부터 역순으로 논문을 찾습니다. (최대 3일)")
        # Try to find papers starting from yesterday, going back up to 3 days
        found_papers = False
        for days_back in range(1, 4):  # 1일전(어제) ~ 3일전
            test_date = us_today - timedelta(days=days_back)
            test_start = datetime.combine(test_date, datetime.min.time())
            test_end = datetime.combine(test_date + timedelta(days=1), datetime.min.time())

            print(f"{days_back}일 전({test_date}) 논문 확인 중...")
            test_papers = fetch_arxiv_data(['cs.AI', 'cs.LG'], test_start, test_end)

            if test_papers and len(test_papers) > 0:
                print(f"{days_back}일 전({test_date})에 {len(test_papers)}개 논문 발견!")
                start_target_date = test_date
                end_target_date = test_date
                discovered_papers = test_papers  # 재사용을 위해 저장
                found_papers = True
                break
            else:
                print(f"{days_back}일 전({test_date})에 논문이 없습니다.")

        if not found_papers:
            print("최근 3일 동안 논문을 찾을 수 없습니다. 어제 날짜로 검색을 시도합니다.")
            start_target_date = us_yesterday
            end_target_date = us_yesterday

    start_date = datetime.combine(start_target_date, datetime.min.time())
    end_date = datetime.combine(end_target_date + timedelta(days=1), datetime.min.time())
    subjects = ['cs.AI', 'cs.LG']
    
    print(f"수집 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"대상 주제: {', '.join(subjects)}")
    print("" * 60)
    
    print(f"======================================================== 통합 검색: {', '.join(subjects)} ========================================================")
    print(f" = = = = = = = = = = =   {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    if discovered_papers is not None:
        papers_data = discovered_papers  # 탐색 루프에서 이미 가져온 데이터 재사용
    else:
        papers_data = fetch_arxiv_data(subjects, start_date, end_date)
    
    # Check if request failed
    if papers_data is None:
        failed_requests = [{
            'Subjects': ', '.join(subjects),
            'Start_date': start_date.strftime('%Y-%m-%d'),
            'End_date': end_date.strftime('%Y-%m-%d'),
            'Failed_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }]
        all_papers_data = []
    else:
        all_papers_data = papers_data
        failed_requests = []
    
    # Remove internal duplicates and sort
    unique_papers_data = remove_internal_duplicates(all_papers_data)
    
    # Sort by URL in descending order
    unique_papers_data.sort(key=lambda x: x['abs_url'], reverse=True)
    
    print("" * 60)
    print(f"수집 완료: 총 {len(unique_papers_data)}개 논문")
    print(f"중복 제거: {len(all_papers_data) - len(unique_papers_data)}개")
    
    save_results(unique_papers_data, start_date, end_date)
    
    # Save failed requests if any
    if failed_requests:
        save_failed_requests(failed_requests, start_date, end_date)
        print(f"⚠️ {len(failed_requests)}개의 요청이 실패했습니다. Failed_list.csv를 확인하세요.")
    
    print("Phase 1 완료!")

if __name__ == "__main__":
    main()
