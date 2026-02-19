#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
organ_integrate.py
Organization Data Integration and Processing Script

Description:
    Phase 4: Organization data processing and normalization
    - Processes organization data from 3_parsing_meta_data.csv
    - Extracts unique organizations to All_organization.txt
    - Adds unified_organ column with normalized organization names
    - Implements backup functionality and CSV processing

Author: AI Assistant
Date: 2025-08-24
"""

import ast
import pandas as pd
import json
import re
from datetime import datetime
import os
from typing import List, Dict, Optional, Any
import dotenv
from pipeline_config import results_dir, PROJECT_DIR

# Load environment variables
dotenv.load_dotenv()

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


def ensure_json_list_string(value: Any) -> str:
    """Normalize organization column values to JSON list strings."""
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return "[]"
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
        try:
            parsed = ast.literal_eval(stripped)
            if isinstance(parsed, list):
                return json.dumps(parsed, ensure_ascii=False)
        except (ValueError, SyntaxError):
            pass

    return "[]"

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
        - Saves organ_integrate.csv with backup functionality
    
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
    
    # Input and output file paths
    html_input_file = os.path.join(results_dir('Phase_3'), '3_parsing_meta_data.csv')
    pdf_input_file = os.path.join(results_dir('Phase_3-aux_2'), '3-aux_2_pdf_parsing.csv')
    output_csv = os.path.join(results_dir('Phase_4'), 'organ_integrate.csv')
    output_txt = os.path.join(results_dir('Phase_4'), 'All_organization.txt')

    # Check if input file exists
    if not os.path.exists(html_input_file):
        print(f"⚠️ 오류: 입력 파일을 찾을 수 없음: {html_input_file}")
        print("먼저 Phase 3을 실행하여 3_parsing_meta_data.csv를 생성해주세요.")
        return

    print(f"Reading HTML-based organization data from: {html_input_file}")

    # Read the HTML-based CSV file
    try:
        df_html = pd.read_csv(html_input_file)
        print(f"HTML 기반 데이터 {len(df_html)}건 로드 완료")

        if 'Submitted' in df_html.columns and len(df_html) > 0:
            submitted_dates_html = pd.to_datetime(df_html['Submitted'], errors='coerce')
            start_date = submitted_dates_html.min().strftime('%y%m%d')
            end_date = submitted_dates_html.max().strftime('%y%m%d')
        else:
            current_date = datetime.now().strftime('%y%m%d')
            start_date = current_date
            end_date = current_date

        print(f"논문 날짜 범위 (HTML 기반): {start_date} ~ {end_date}")

    except Exception as e:
        print(f"CSV 파일 읽기 오류: {e}")
        return

    df_html['organization'] = df_html['organization'].apply(ensure_json_list_string)
    df_html['pdf_or_html'] = 'html'

    # Load PDF-based organization data if available
    if os.path.exists(pdf_input_file):
        try:
            df_pdf = pd.read_csv(pdf_input_file, encoding='utf-8-sig')
            print(f"PDF 기반 데이터 {len(df_pdf)}건 로드 완료")
        except Exception as e:
            print(f"WARNING PDF 기반 CSV를 읽는 중 오류 발생: {e}")
            df_pdf = pd.DataFrame()
    else:
        print(f"INFO PDF 기반 결과 파일을 찾지 못했습니다: {pdf_input_file}")
        df_pdf = pd.DataFrame()

    if not df_pdf.empty:
        if 'pdf_based_organization' in df_pdf.columns:
            df_pdf = df_pdf.rename(columns={'pdf_based_organization': 'organization'})
        if 'organization' not in df_pdf.columns:
            df_pdf['organization'] = []

        df_pdf['organization'] = df_pdf['organization'].apply(ensure_json_list_string)
        df_pdf['pdf_or_html'] = 'pdf'

        for column in df_html.columns:
            if column not in df_pdf.columns:
                df_pdf[column] = ''

        df = pd.concat([df_html, df_pdf[df_html.columns]], ignore_index=True)
        print(f"총 {len(df)}건 (HTML {len(df_html)}건 + PDF {len(df_pdf)}건) 통합 완료")
    else:
        df = df_html.copy()
        print(f"PDF 기반 데이터가 없어 HTML {len(df)}건만 처리합니다.")

    if 'Submitted' in df.columns and len(df) > 0:
        submitted_dates_all = pd.to_datetime(df['Submitted'], errors='coerce')
        all_start = submitted_dates_all.min().strftime('%y%m%d')
        all_end = submitted_dates_all.max().strftime('%y%m%d')
        print(f"통합 데이터 기준 논문 날짜 범위: {all_start} ~ {all_end}")
    else:
        current_date = datetime.now().strftime('%y%m%d')
        all_start = current_date
        all_end = current_date

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
        with open(output_txt, 'w', encoding='utf-8') as f:
            for org in unique_organizations:
                f.write(f"{org}\n")
        print(f"기관 리스트 저장 완료 ({len(unique_organizations)}개 기관)")

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
    
    # Reorder columns: priority columns first, then the rest
    priority_columns = ['ID', 'collected_at_kst', 'Title', 'organization', 'Subjects', 'Authors',
                        'Comments', 'abs_url', 'html_url', 'pdf_url']
    remaining_columns = [col for col in df.columns if col not in priority_columns]
    df = df[[col for col in priority_columns if col in df.columns] + remaining_columns]

    # Save main result file (덮어쓰기)
    print(f"메인 결과 파일 저장: {output_csv}")
    try:
        df.to_csv(output_csv, index=False, encoding='utf-8-sig')
        print(f"메인 결과 파일 저장 완료")
    except Exception as e:
        print(f"메인 결과 파일 저장 오류: {e}")
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
    
    print("\n상위 10개 기관:")
    for i, org in enumerate(unique_organizations[:10], 1):
        print(f"{i:2d}. {org}")
    
    print("Phase 4 완료!")

if __name__ == "__main__":
    process_organization_data()
