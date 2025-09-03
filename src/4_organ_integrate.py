#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4_organ_integrate.py
Organization Data Integration and Processing Script

Description:
    Phase 5: Organization data processing and normalization
    - Processes organization data from 3_parsing_meta_data.csv
    - Extracts unique organizations to All_organization.txt
    - Adds unified_organ column with normalized organization names
    - Implements backup functionality and CSV processing

Author: AI Assistant
Date: 2025-08-24
"""

import pandas as pd
import json
import re
from datetime import datetime
import os
from typing import List, Dict, Optional, Any
import dotenv

# Load environment variables
dotenv.load_dotenv()

CUR_DIR = os.path.dirname(os.path.abspath(__file__))
PAR_DIR = os.path.dirname(CUR_DIR)

def create_directories() -> None:
    """
    필요한 디렉토리들을 생성합니다.
    
    Creates necessary directories for organization integration and backup storage.
    
    Input: None
    
    Output: None (creates directories)
        - backup/4_organ_integrate: Backup directory for integration results
    
    Example:
        >>> create_directories()
        디렉토리 생성 완료
    """
    os.makedirs(f"{PAR_DIR}/backup/4_organ_integrate", exist_ok=True)
    print("디렉토리 생성 완료")

def save_existing_data_to_backup(start_date_str: str, end_date_str: str) -> bool:
    """
    기존 데이터를 백업으로 저장한 후 삭제합니다.
    
    Backs up existing organization integration results before processing new data.
    
    Input:
        - start_date_str: str - Start date in YYMMDD format
            - Ex: '250508'
        - end_date_str: str - End date in YYMMDD format
            - Ex: '250509'
    
    Output:
        - backup_created: bool - True if any backup was created, False if no existing files
            - Ex: True
    
    Example:
        >>> backup_created = save_existing_data_to_backup('250508', '250509')
        기존 CSV 데이터 백업 저장: backup/4_organ_integrate/4_organ_integrate_StartDate250508_EndDate250509.csv
        기존 TXT 데이터 백업 저장: backup/4_organ_integrate/All_organization_StartDate250508_EndDate250509.txt
        >>> print(backup_created)
        True
    """
    output_csv = f"{PAR_DIR}/results/4_organ_integrate.csv"
    output_txt = "All_organization.txt"
    
    backed_up = False
    
    # CSV 파일 백업
    if os.path.exists(output_csv):
        existing_df = pd.read_csv(output_csv)
        backup_path = f"{PAR_DIR}/backup/4_organ_integrate/4_organ_integrate_StartDate{start_date_str}_EndDate{end_date_str}.csv"
        existing_df.to_csv(backup_path, index=False, encoding='utf-8-sig')
        print(f"기존 CSV 데이터 백업 저장: {backup_path}")
        backed_up = True
    
    # TXT 파일 백업
    if os.path.exists(output_txt):
        backup_txt_path = f"{PAR_DIR}/backup/4_organ_integrate/All_organization_StartDate{start_date_str}_EndDate{end_date_str}.txt"
        import shutil
        shutil.copy2(output_txt, backup_txt_path)
        print(f"기존 TXT 데이터 백업 저장: {backup_txt_path}")
        backed_up = True
    
    return backed_up

def normalize_organization_name(org_name: Any) -> str:
    """
    Normalize organization name for unified representation.
    
    Converts organization names to normalized format for deduplication and standardization.
    
    Input:
        - org_name: Any - Organization name (usually str, but handles other types)
            - Ex: 'Stanford University'
    
    Output:
        - normalized_name: str - Normalized organization name
            - Ex: 'stanforduniversity'
    
    Processing:
        - Convert to lowercase
        - Remove spaces and special characters
        - Keep only alphanumeric characters
    
    Example:
        >>> normalize_organization_name('Stanford University')
        'stanforduniversity'
        >>> normalize_organization_name('MIT (Cambridge)')
        'mitcambridge'
        >>> normalize_organization_name(None)
        ''
    """
    if not org_name or not isinstance(org_name, str):
        return ""
    
    # Convert to lowercase and remove special characters
    normalized = re.sub(r'[^a-zA-Z0-9]', '', org_name.lower())
    return normalized

def extract_organizations_from_json(json_string: str) -> List[str]:
    """
    Extract organization list from JSON string.
    
    Parses JSON string containing organization list and returns as Python list.
    
    Input:
        - json_string: str - JSON string representation of organization list
            - Ex: '["Stanford University", "MIT", "Google"]'
    
    Output:
        - organizations: List[str] - List of organization names
            - Ex: ['Stanford University', 'MIT', 'Google']
    
    Example:
        >>> extract_organizations_from_json('["MIT", "Stanford"]')
        ['MIT', 'Stanford']
        >>> extract_organizations_from_json('[]')
        []
        >>> extract_organizations_from_json('invalid json')
        []
    """
    if not json_string or json_string == '[]':
        return []
    
    try:
        organizations = json.loads(json_string)
        return organizations if isinstance(organizations, list) else []
    except (json.JSONDecodeError, TypeError):
        return []

def process_organization_data() -> None:
    """
    Main function to process organization data and create integration results.
    
    Processes organization data from Phase 3 results, extracts unique organizations,
    creates unified organization names, and saves integrated results.
    
    Input: None
    
    Output: None (processes and saves data)
        - Loads 3_parsing_meta_data.csv
        - Extracts all unique organizations to All_organization.txt
        - Adds unified_organ column with normalized organization names
        - Saves 4_organ_integrate.csv with backup functionality
    
    Processing flow:
        1. Load organization data from Phase 3 results
        2. Extract and deduplicate all organizations
        3. Create normalized organization names
        4. Save results and backups
        5. Generate comprehensive statistics
    
    Example:
        >>> process_organization_data()
        ============================================================
        Phase 4: 기관 데이터 통합 및 정규화
        ============================================================
        총 25개 논문 데이터 로드 완료
        ...
        추출된 고유 기관 수: 45
        Phase 4 완료!
    """
    print("=" * 60)
    print("Phase 4: 기관 데이터 통합 및 정규화")
    print("=" * 60)
    
    # Create necessary directories
    create_directories()
    
    # Input and output file paths
    input_file = f"{PAR_DIR}/results/3_parsing_meta_data.csv"
    output_csv = f"{PAR_DIR}/results/4_organ_integrate.csv"
    output_txt = "All_organization.txt"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"⚠️ 오류: 입력 파일을 찾을 수 없음: {input_file}")
        print("먼저 Phase 3을 실행하여 3_parsing_meta_data.csv를 생성해주세요.")
        return
    
    print(f"Reading data from: {input_file}")
    
    # Read the CSV file
    try:
        df = pd.read_csv(input_file)
        print(f"총 {len(df)}개 논문 데이터 로드 완룼")
        
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
        
        # Backup existing data
        save_existing_data_to_backup(start_date, end_date)
        
    except Exception as e:
        print(f"CSV 파일 읽기 오류: {e}")
        return
    
    # Extract all unique organizations
    all_organizations = set()
    organization_data = []
    
    print("\nProcessing organization data...")
    
    for index, row in df.iterrows():
        org_json = row.get('organization', '[]')
        organizations = extract_organizations_from_json(org_json)
        
        # Add to unique set
        for org in organizations:
            if org and isinstance(org, str):
                all_organizations.add(org)
        
        organization_data.append(organizations)
        
        if (index + 1) % 5 == 0 or (index + 1) == len(df):
            print(f"  Processed {index + 1}/{len(df)} papers")
    
    # Convert to sorted list
    unique_organizations = sorted(list(all_organizations))
    
    print(f"\nExtraction Results:")
    print(f"  - Total papers processed: {len(df)}")
    print(f"  - Papers with organizations: {sum(1 for orgs in organization_data if orgs)}")
    print(f"  - Unique organizations found: {len(unique_organizations)}")
    
    # Save unique organizations to text file
    # Save unique organizations to text file (덮어쓰기)
    print(f"\n기관 리스트 저장: {output_txt}")
    try:
        # Generate timestamp for backup
        current_time = datetime.now().strftime("%Y-%m-%d %H%M")
        
        with open(output_txt, 'w', encoding='utf-8') as f:
            for org in unique_organizations:
                f.write(f"{org}\n")
        print(f"기관 리스트 저장 완료 ({len(unique_organizations)}개 기관)")
        
        # Create backup of organization list
        backup_txt_path = f"{PAR_DIR}/backup/4_organ_integrate/All_organization_{current_time}.txt"
        with open(backup_txt_path, 'w', encoding='utf-8') as f:
            for org in unique_organizations:
                f.write(f"{org}\n")
        print(f"기관 리스트 백업 저장: {backup_txt_path}")
        
        # Save KNOWN_ORGANIZATIONS from .env to setted_organs.json
        known_organizations_str = os.getenv('KNOWN_ORGANIZATIONS', '[]')
        try:
            known_organizations = json.loads(known_organizations_str)
            setted_organs_path = f"{PAR_DIR}/backup/4_organ_integrate/setted_organs.json"
            with open(setted_organs_path, 'w', encoding='utf-8') as f:
                json.dump(known_organizations, f, ensure_ascii=False, indent=2)
            print(f"사전 등록 기관 리스트 저장: {setted_organs_path} ({len(known_organizations)}개 기관)")
        except (json.JSONDecodeError, TypeError) as e:
            print(f"KNOWN_ORGANIZATIONS 파싱 오류: {e}")
        
    except Exception as e:
        print(f"기관 리스트 저장 오류: {e}")
        return
    
    # Add unified_organ column to DataFrame
    print("\nCreating unified organization names...")
    
    unified_organs = []
    for organizations in organization_data:
        if organizations:
            # Create normalized names for each organization
            normalized_orgs = [normalize_organization_name(org) for org in organizations if org]
            # Remove empty strings and duplicates while preserving order
            normalized_orgs = list(dict.fromkeys([org for org in normalized_orgs if org]))
            unified_organs.append(normalized_orgs)
        else:
            unified_organs.append([])
    
    # Add the new column to DataFrame
    df['unified_organ'] = [json.dumps(orgs) if orgs else "[]" for orgs in unified_organs]
    
    # Show some examples of normalization
    print("\nOrganization normalization examples:")
    example_count = 0
    for i, (original, normalized) in enumerate(zip(organization_data, unified_organs)):
        if original and normalized and example_count < 3:
            print(f"  Original: {original}")
            print(f"  Normalized: {normalized}")
            print()
            example_count += 1
    
    # Save main result file (덮어쓰기)
    print(f"메인 결과 파일 저장: {output_csv}")
    try:
        df.to_csv(output_csv, index=False, encoding='utf-8-sig')
        print(f"메인 결과 파일 저장 완료")
    except Exception as e:
        print(f"메인 결과 파일 저장 오류: {e}")
        return
    
    # Create backup file with most recent submission date
    if 'Submitted' in df.columns and len(df) > 0:
        submitted_dates = pd.to_datetime(df['Submitted'], errors='coerce')
        most_recent_date = submitted_dates.max().strftime('%d %B, %Y')
        backup_file = f"{PAR_DIR}/backup/4_organ_integrate/4_organ_integrate_({most_recent_date}).csv"
    else:
        backup_file = f"{PAR_DIR}/backup/4_organ_integrate/4_organ_integrate_{current_time}.csv"
    
    print(f"백업 파일 생성: {backup_file}")
    try:
        df.to_csv(backup_file, index=False, encoding='utf-8-sig')
        print(f"백업 파일 저장 완료")
    except Exception as e:
        print(f"백업 파일 생성 오류: {e}")
        return
    
    # Final statistics
    print("\n" + "=" * 60)
    print("FINAL STATISTICS")
    print("=" * 60)
    print(f"총 처리된 논문 수: {len(df)}")
    print(f"기관 정보가 있는 논문: {sum(1 for orgs in organization_data if orgs)}")
    print(f"성공률: {sum(1 for orgs in organization_data if orgs)/len(df)*100:.1f}%")
    print(f"추출된 고유 기관 수: {len(unique_organizations)}")
    print(f"성공한 논문당 평균 기관 수: {sum(len(orgs) for orgs in organization_data if orgs) / max(sum(1 for orgs in organization_data if orgs), 1):.1f}")
    
    print("\n출력 파일:")
    print(f"- 메인 결과: {output_csv}")
    print(f"- 기관 리스트: {output_txt}")
    print(f"- 백업 파일: {backup_file}")
    
    print("\n상위 10개 기관:")
    for i, org in enumerate(unique_organizations[:10], 1):
        print(f"{i:2d}. {org}")
    
    print("Phase 4 완료!")

if __name__ == "__main__":
    process_organization_data()