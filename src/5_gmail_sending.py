#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
5_2_gmail_api_sending.py
Gmail API Sending Module for arXiv Paper Notifications

Description:
    Phase 5-2: Enhanced email notification with Gmail API
    - Sends comprehensive paper summary via Gmail API
    - Includes sample papers and statistics
    - Attaches CSV file without HTML columns
    - Uses Google API authentication

Author: AI Assistant
Date: 2025-08-26
"""

import os
import json
import base64
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import dotenv

# Gmail API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GMAIL_API_AVAILABLE = True
except ImportError:
    print("WARNING Gmail API 라이브러리가 설치되지 않았습니다.")
    print("다음 명령어로 설치하세요: pip install google-auth google-auth-oauthlib google-api-python-client")
    GMAIL_API_AVAILABLE = False

# Load environment variables
dotenv.load_dotenv()

# Gmail API 스코프 - (test) Gmail_API.py와 동일한 권한 사용
SCOPES = ['https://mail.google.com/']

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
PAR_DIR = os.path.dirname(CUR_DIR)

def create_directories() -> None:
    """
    필요한 디렉토리들을 생성합니다.
    
    Creates necessary directories for Gmail sending and backup storage.
    
    Input: None
    
    Output: None (creates directories)
        - results: Results directory
        - backup/5_gmail_api: Backup directory for Gmail API operations
    
    Example:
        >>> create_directories()
        디렉토리 생성 완료
    """
    os.makedirs(f"{PAR_DIR}/results", exist_ok=True)
    os.makedirs(f"{PAR_DIR}/backup/5_gmail_api", exist_ok=True)
    print("디렉토리 생성 완료")

def authenticate_gmail_api() -> Optional[Any]:
    """
    Gmail API 인증을 수행합니다.
    
    Performs Gmail API authentication using OAuth 2.0 credentials and manages token lifecycle.
    
    Input: None (uses credentials.json and token.json files)
    
    Output:
        - service: Optional[Any] - Gmail API service object or None if authentication fails
            - Ex: Gmail API service object for sending emails
    
    Authentication flow:
        1. Load existing token.json if available
        2. Refresh expired tokens if possible
        3. Perform new OAuth flow if needed using credentials.json
        4. Save token for future use
    
    Example:
        >>> service = authenticate_gmail_api()
        [OK] Gmail API 인증 성공
        >>> service is not None
        True
    """
    if not GMAIL_API_AVAILABLE:
        return None
    
    creds = None
    
    # 기존 토큰 파일이 있으면 로드
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # 유효한 credentials가 없으면 새로 인증
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except:
                creds = None
                
        if not creds:
            if not os.path.exists('credentials.json'):
                print("❌ credentials.json 파일이 필요합니다.")
                print("Google Cloud Console에서 OAuth 2.0 credentials를 다운로드하고")
                print("credentials.json으로 저장해주세요.")
                return None
                
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 토큰을 파일로 저장
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)

def load_latest_data() -> Optional[pd.DataFrame]:
    """
    최신 처리된 데이터를 로드합니다.
    
    Loads the latest processed paper data from Phase 4 results for email generation.
    
    Input: None
    
    Output:
        - df: Optional[pd.DataFrame] - DataFrame with processed paper data or None if no data found
            - Ex: DataFrame with columns ['ID', 'Title', 'Authors', 'organization', 'Abstract', etc.]
    
    Example:
        >>> df = load_latest_data()
        데이터 로드 성공: results/4_organ_integrate.csv (25개 논문)
        >>> df is not None
        True
        >>> len(df)
        25
    """
    # 4단계 결과를 시도
    files_to_try = [
        f"{PAR_DIR}//results/4_organ_integrate.csv"
    ]
    
    for file_path in files_to_try:
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                print(f"데이터 로드 성공: {file_path} ({len(df)}개 논문)")
                return df
            except Exception as e:
                print(f"파일 로드 실패 {file_path}: {str(e)}")
                continue
    
    print("❌ 사용 가능한 데이터 파일을 찾을 수 없습니다.")
    return None

def get_sample_papers(df: pd.DataFrame, n: int = 5) -> List[Dict[str, Any]]:
    """
    샘플 논문들을 선택합니다.
    
    Selects sample papers for email display, prioritizing papers with organization information.
    
    Input:
        - df: pd.DataFrame - DataFrame containing paper data
            - Ex: DataFrame with columns ['Title', 'Authors', 'Abstract', 'organization', etc.]
        - n: int - Number of sample papers to select
            - Ex: 5
    
    Output:
        - samples: List[Dict[str, Any]] - List of sample paper dictionaries
            - Ex: [
                {
                    'title': 'AI Research Paper',
                    'abstract': 'This paper presents...',
                    'authors': 'John Doe; Jane Smith',
                    'organizations': ['Stanford University', 'MIT'],
                    'submitted': '2025-05-08',
                    'subjects': 'Computer Science - Artificial Intelligence',
                    'url': 'https://arxiv.org/abs/2405.12345'
                }
            ]
    
    Example:
        >>> df = pd.DataFrame({'Title': ['Paper A'], 'organization': ['["MIT"]'], 'Authors': ['John Doe']})
        >>> samples = get_sample_papers(df, n=1)
        >>> len(samples)
        1
        >>> samples[0]['organizations']
        ['MIT']
    """
    try:
        # 기관 정보가 있는 논문 우선
        if 'organization' in df.columns:
            df_with_orgs = df[df['organization'].notna() & (df['organization'] != '') & (df['organization'] != '[]')].copy()
            if len(df_with_orgs) >= n:
                sample_df = df_with_orgs.head(n)
            else:
                sample_df = df.head(n)
        else:
            sample_df = df.head(n)
        
        samples = []
        for _, row in sample_df.iterrows():
            # 기관 정보 처리
            organizations = []
            if 'organization' in row and row['organization']:
                try:
                    if row['organization'] != '[]':
                        organizations = json.loads(row['organization'])
                except:
                    organizations = []
            
            sample = {
                'title': row.get('Title', 'No title available'),
                'abstract': row.get('Abstract', 'No abstract available'),
                'authors': row.get('Authors', 'No authors available'),
                'organizations': organizations if organizations else ['No organizations detected'],
                'submitted': row.get('Submitted', 'Unknown'),
                'subjects': row.get('Subjects', 'Unknown'),
                'url': row.get('abs_url', '')
            }
            samples.append(sample)
            
        return samples
    except Exception as e:
        print(f"샘플 논문 선택 중 오류: {str(e)}")
        return []

def create_csv_attachment(df: pd.DataFrame) -> str:
    """
    HTML 컬럼을 제거한 CSV 첨부파일을 생성합니다.
    
    Creates a clean CSV attachment by removing HTML columns for email attachment.
    
    Input:
        - df: pd.DataFrame - DataFrame containing all paper data including HTML columns
            - Ex: DataFrame with columns ['ID', 'Title', 'html_raw_text', 'html_raw_text_with_tags', 'organization']
    
    Output:
        - attachment_path: str - Path to created CSV attachment file
            - Ex: 'results/papers_for_email_20250830_143025.csv'
    
    Example:
        >>> df = pd.DataFrame({'ID': ['1'], 'Title': ['Paper'], 'html_raw_text': ['<div>'], 'organization': ['["MIT"]']})
        >>> path = create_csv_attachment(df)
        첨부파일에서 html_raw_text 컬럼 제거
        첨부파일 생성 완료: results/papers_for_email_20250830_143025.csv (1개 논문, 3개 컬럼)
        >>> 'papers_for_email' in path
        True
    """
    try:
        # HTML 관련 컬럼 제거
        html_columns = ['html_raw_text', 'html_raw_text_with_tags', 'html_raw_text_with_tags_filtered']
        
        # Originally_announced: Phase 1에서 날짜 필터링 자체를 Originally_announced 기준으로 필터링하기 때문에 
        # Submitted column의 날짜와 동일한 의미이다. 의미가 겹치므로, 더 정확한 날짜값을 제공하는 Submitted를 남기고 삭제한다.
        # unified_organ: organization column과 동일하고 lowercase 여부의 차이여서 의미가 중복된다.
        redundant_columns = ['Originally_announced', 'unified_organ']
        
        columns_to_remove = html_columns + redundant_columns
        
        df_clean = df.copy()
        for col in columns_to_remove:
            if col in df_clean.columns:
                df_clean = df_clean.drop(columns=[col])
                print(f"첨부파일에서 {col} 컬럼 제거")
        
        # 임시 파일로 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        attachment_path = f"{PAR_DIR}//results/papers_for_email_{timestamp}.csv"
        df_clean.to_csv(attachment_path, index=False, encoding='utf-8-sig')
        
        print(f"첨부파일 생성 완료: {attachment_path} ({len(df_clean)}개 논문, {len(df_clean.columns)}개 컬럼)")
        return attachment_path
        
    except Exception as e:
        print(f"첨부파일 생성 중 오류: {str(e)}")
        return ""

def create_email_content(df: pd.DataFrame, samples: List[Dict[str, Any]], start_date_str: str, end_date_str: str) -> str:
    """
    이메일 HTML 콘텐츠를 생성합니다.
    
    Creates comprehensive HTML email content with statistics, sample papers, and organization information.
    
    Input:
        - df: pd.DataFrame - DataFrame containing all paper data
            - Ex: DataFrame with columns ['Title', 'Authors', 'organization', 'Abstract', 'Submitted', etc.]
        - samples: List[Dict[str, Any]] - List of sample paper dictionaries
            - Ex: [{'title': 'Paper A', 'organizations': ['MIT'], 'abstract': 'Research on...'}]
        - start_date_str: str - Start date for report period
            - Ex: '250508'
        - end_date_str: str - End date for report period
            - Ex: '250509'
    
    Output:
        - html_content: str - Complete HTML email content
            - Ex: '<html><head><style>...</style></head><body><div class="header">...</div></body></html>'
    
    Example:
        >>> df = pd.DataFrame({'Title': ['Paper A'], 'organization': ['["MIT"]']})
        >>> samples = [{'title': 'Paper A', 'organizations': ['MIT']}]
        >>> html = create_email_content(df, samples, '250508', '250509')
        >>> '<html>' in html
        True
        >>> 'MIT' in html
        True
    """
    # 전체 통계
    total_papers = len(df)
    
    # 기관 정보 통계
    papers_with_orgs = 0
    all_organizations = set()
    
    if 'organization' in df.columns:
        for _, row in df.iterrows():
            if row['organization'] and row['organization'] != '[]':
                try:
                    orgs = json.loads(row['organization'])
                    if orgs:
                        papers_with_orgs += 1
                        all_organizations.update(orgs)
                except:
                    continue
    
    unique_orgs_count = len(all_organizations)
    
    # Extract date range from data
    if 'Submitted' in df.columns and len(df) > 0:
        submitted_dates = pd.to_datetime(df['Submitted'], errors='coerce')
        publication_start = submitted_dates.min().strftime('%Y-%m-%d')
        publication_end = submitted_dates.max().strftime('%Y-%m-%d')
    else:
        publication_start = "N/A"
        publication_end = "N/A"
    
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                      color: white; padding: 25px; border-radius: 8px; margin-bottom: 25px; }}
            .stats {{ background-color: #f8f9fa; padding: 20px; border-radius: 8px; 
                     margin-bottom: 25px; border-left: 4px solid #007bff; }}
            .stat-item {{ display: inline-block; margin-right: 25px; }}
            .stat-number {{ font-size: 28px; font-weight: bold; color: #007bff; }}
            .stat-label {{ font-size: 14px; color: #6c757d; }}
            .paper {{ border-bottom: 1px solid #dee2e6; padding: 20px 0; }}
            .paper-title {{ font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 8px; }}
            .paper-authors {{ color: #6c757d; margin-bottom: 5px; }}
            .paper-orgs {{ background-color: #e3f2fd; padding: 8px 12px; border-radius: 4px;
                          color: #1565c0; font-weight: 500; margin-bottom: 8px; }}
            .paper-meta {{ color: #868e96; font-size: 14px; margin-bottom: 10px; }}
            .paper-abstract {{ color: #495057; font-size: 15px; line-height: 1.5;
                             border-left: 3px solid #17a2b8; padding-left: 15px; margin-bottom: 10px;
                             background-color: #f8f9fa; padding: 15px; border-radius: 4px; }}
            .paper-url {{ margin-top: 10px; }}
            .paper-url a {{ color: #007bff; text-decoration: none; font-weight: 500; }}
            .paper-url a:hover {{ text-decoration: underline; }}
            .footer {{ margin-top: 30px; padding: 15px; background-color: #f8f9fa; 
                      border-radius: 4px; font-size: 12px; color: #6c757d; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 arXiv Papers Daily Report</h1>
            <p><strong>생성 시간:</strong> {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}</p>
            <p><strong>논문 출판 날짜 범위:</strong> {publication_start} ~ {publication_end}</p>
            <p>최신 AI/ML 논문 수집 결과를 알려드립니다.</p>
        </div>
        
        <div class="stats">
            <h2>[STATS] 수집 통계</h2>
            <div class="stat-item">
                <div class="stat-number">{total_papers}</div>
                <div class="stat-label">총 논문 수</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{papers_with_orgs}</div>
                <div class="stat-label">기관 정보 보유</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{unique_orgs_count}</div>
                <div class="stat-label">고유 기관 수</div>
            </div>
        </div>
        
        <h2>[PAPERS] 샘플 논문 ({len(samples)}개)</h2>
    """
    
    # 샘플 논문들 추가
    for i, paper in enumerate(samples, 1):
        # Abstract 길이 제한
        abstract = paper['abstract']
        if len(abstract) > 400:
            abstract = abstract[:400] + "..."
        
        orgs_display = ', '.join(paper['organizations']) if paper['organizations'] else 'No organizations detected'
        
        html_content += f"""
        <div class="paper">
            <div class="paper-title">{i}. {paper['title']}</div>
            <div class="paper-authors"><strong>저자:</strong> {paper['authors']}</div>
            <div class="paper-orgs"><strong>🏢 소속 기관:</strong> {orgs_display}</div>
            <div class="paper-meta">
                <strong>제출일:</strong> {paper['submitted']} | 
                <strong>분야:</strong> {paper['subjects']}
            </div>
            <div class="paper-abstract">
                <strong>📝 초록:</strong><br>{abstract}
            </div>
            <div class="paper-url">
                <a href="{paper['url']}" target="_blank">🔗 arXiv에서 전체 논문 보기</a>
            </div>
        </div>
        """
    
    # 발견된 모든 기관들
    if unique_orgs_count > 0:
        # Sort organizations alphabetically for better readability
        sorted_orgs = sorted(list(all_organizations))
        org_list = ', '.join(sorted_orgs)
            
        html_content += f"""
        <div style="margin-top: 25px; padding: 15px; background-color: #fff3cd; border-radius: 4px;">
            <h3>🏛️ 발견된 모든 기관 ({unique_orgs_count}개)</h3>
            <p style="line-height: 1.6;">{org_list}</p>
        </div>
        """
    
    html_content += f"""
        <div class="footer">
            <p><strong>📎 첨부파일:</strong> 전체 논문 데이터 (CSV 형식, HTML 컬럼 제외)</p>
            <p>이 이메일은 arXiv 논문 자동 수집 시스템에서 생성되었습니다.</p>
            <p>더 자세한 정보가 필요하시면 첨부된 CSV 파일을 확인해주세요.</p>
        </div>
    </body>
    </html>
    """
    
    return html_content

def send_gmail_api(service: Any, recipient_email: str, subject: str, html_content: str, attachment_path: str = "") -> bool:
    """
    Gmail API를 통해 이메일을 발송합니다.
    
    Sends email using Gmail API with HTML content and optional CSV attachment.
    
    Input:
        - service: Any - Gmail API service object from authentication
            - Ex: Gmail API service object
        - recipient_email: str - Email address of recipient
            - Ex: 'user@example.com'
        - subject: str - Email subject line
            - Ex: '[REPORT] arXiv Papers Report (250508 - 250509) - 25개 논문'
        - html_content: str - HTML email content
            - Ex: '<html><body><h1>Report</h1></body></html>'
        - attachment_path: str - Path to CSV attachment file (optional)
            - Ex: 'results/papers_for_email_20250830_143025.csv'
    
    Output:
        - success: bool - True if email sent successfully, False otherwise
            - Ex: True
    
    Example:
        >>> service = authenticate_gmail_api()
        >>> success = send_gmail_api(service, 'user@example.com', 'Test Report', '<html><body>Test</body></html>', 'data.csv')
        첨부파일 추가: data.csv
        [OK] Gmail API를 통한 이메일 발송 완료: user@example.com
        Message Id: 18c2a1b2c3d4e5f6
        >>> print(success)
        True
    """
    try:
        # 이메일 메시지 생성
        message = MIMEMultipart()
        message['to'] = recipient_email
        message['subject'] = subject
        
        # HTML 컨텐츠 추가
        html_part = MIMEText(html_content, 'html', 'utf-8')
        message.attach(html_part)
        
        # 첨부파일 추가
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {os.path.basename(attachment_path)}'
            )
            message.attach(part)
            print(f"첨부파일 추가: {attachment_path}")
        
        # 메시지를 raw 형식으로 인코딩
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Gmail API로 전송
        send_message = service.users().messages().send(
            userId="me", 
            body={'raw': raw_message}
        ).execute()
        
        print(f"[OK] Gmail API를 통한 이메일 발송 완료: {recipient_email}")
        print(f"Message Id: {send_message['id']}")
        return True
        
    except Exception as e:
        print(f"❌ Gmail API 이메일 발송 실패: {str(e)}")
        return False

def cleanup_temp_files(file_path: str) -> None:
    """
    임시 파일을 정리합니다.
    
    Removes temporary files created during email processing.
    
    Input:
        - file_path: str - Path to temporary file to delete
            - Ex: 'results/papers_for_email_20250830_143025.csv'
    
    Output: None (deletes file)
    
    Example:
        >>> cleanup_temp_files('temp_file.csv')
        임시 파일 삭제: temp_file.csv
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"임시 파일 삭제: {file_path}")
    except Exception as e:
        print(f"임시 파일 삭제 실패: {str(e)}")

def main() -> None:
    """
    메인 실행 함수
    
    Main execution function for Phase 5: Gmail API paper report sending.
    Orchestrates the complete email sending workflow with paper data and statistics.
    
    Input: None (uses environment variables and data files)
    
    Output: None (sends email)
        - Loads latest paper data from Phase 4 results
        - Authenticates with Gmail API
        - Creates HTML email content with statistics and sample papers
        - Attaches CSV file (without HTML columns)
        - Sends email to recipient specified in RECIPIENT_EMAIL env var
    
    Processing flow:
        1. Authenticate Gmail API
        2. Load latest processed data
        3. Select sample papers for display
        4. Create CSV attachment
        5. Generate HTML email content
        6. Send email with attachment
        7. Clean up temporary files
    
    Example:
        >>> main()
        ============================================================
        Phase 5: Gmail API를 통한 논문 보고서 발송
        ============================================================
        데이터 로드 성공: results/4_organ_integrate.csv (25개 논문)
        [OK] Gmail API 인증 성공
        수신자: user@example.com
        [OK] Gmail API를 통한 이메일 발송 완료: user@example.com
        Phase 5 완료!
    """
    print("=" * 60)
    print("Phase 5: Gmail API를 통한 논문 보고서 발송")
    print("=" * 60)
    
    if not GMAIL_API_AVAILABLE:
        print("Gmail API 라이브러리가 필요합니다. 프로그램을 종료합니다.")
        return
    
    # 디렉토리 생성
    create_directories()
    
    # 데이터 로드
    df = load_latest_data()
    if df is None:
        return
    
    # Extract date range from the data
    if 'Submitted' in df.columns and len(df) > 0:
        submitted_dates = pd.to_datetime(df['Submitted'], errors='coerce')
        start_date_str = submitted_dates.min().strftime('%Y%m%d')
        end_date_str = submitted_dates.max().strftime('%Y%m%d')
    else:
        current_date = datetime.now().strftime('%Y%m%d')
        start_date_str = current_date
        end_date_str = current_date
        
    print(f"논문 날짜 범위: {start_date_str} ~ {end_date_str}")
    
    # Gmail API 인증
    print("\nGmail API 인증 중...")
    service = authenticate_gmail_api()
    if service is None:
        print("Gmail API 인증에 실패했습니다.")
        return
    
    print("[OK] Gmail API 인증 성공")
    
    # 수신자 이메일 확인
    recipient_email = os.getenv('RECIPIENT_EMAIL', '')
    if not recipient_email:
        print("❌ .env 파일에 RECIPIENT_EMAIL을 설정해주세요.")
        return
    
    print(f"수신자: {recipient_email}")
    
    # 샘플 논문 선택
    samples = get_sample_papers(df, n=5)
    if not samples:
        print("샘플 논문을 선택할 수 없습니다.")
        return
    
    # 첨부파일 생성
    attachment_path = create_csv_attachment(df)
    
    # 이메일 콘텐츠 생성
    html_content = create_email_content(df, samples, start_date_str, end_date_str)
    
    # 이메일 제목 - 논문 검색 날짜 범위 기반
    subject = f"[REPORT] arXiv Papers Report ({start_date_str} - {end_date_str}) - {len(df)}개 논문"
    
    # 이메일 발송
    success = send_gmail_api(service, recipient_email, subject, html_content, attachment_path)
    
    # 임시 파일 정리
    if attachment_path:
        cleanup_temp_files(attachment_path)
    
    # 결과 출력
    print(f"\n{'='*60}")
    print("발송 결과:")
    print(f"  - 총 논문 수: {len(df)}개")
    print(f"  - 샘플 논문: {len(samples)}개")
    print(f"  - 이메일 발송: {'성공' if success else '실패'}")
    if success:
        print(f"  - 수신자: {recipient_email}")
    print("Phase 5 완료!")

if __name__ == "__main__":
    main()