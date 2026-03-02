#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
integrated.py
Integrated Local Paper Parsing and Gmail Notification System

Description:
    - Runs the complete local paper parsing pipeline (phases 1-5)
    - Phase 1-4: Input pool normalization, HTML extraction, organization parsing, data integration
    - Phase 5: Gmail notification with filtered results
    - Configurable organizations via .env file

Author: AI Assistant
Date: 2025-08-25
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime
import dotenv

# Load environment variables
dotenv.load_dotenv()

# Import the Gmail sending module
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("gmail_sending", "gmail_sending.py")
    gmail_sending = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gmail_sending)
except Exception as e:
    print(f"WARNING: gmail_sending.py를 불러올 수 없습니다: {e}")
    gmail_sending = None

def run_script(script_name: str, input_data: str = None, show_realtime: bool = False, timeout: int = 1800) -> bool:
    """Run a Python script and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {script_name}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    try:
        # Start the subprocess
        print(f"[LOG] Starting subprocess for {script_name}")
        start_time = datetime.now()
        
        if show_realtime:
            # For Phase 2, show real-time output without capturing
            print(f"[LOG] Running with real-time output (not captured)")
            if input_data:
                # If input is needed, use Popen for more control
                process = subprocess.Popen([sys.executable, script_name], 
                                         stdin=subprocess.PIPE, 
                                         stdout=None, stderr=None,
                                         text=True)
                process.communicate(input=input_data)
                result_code = process.wait()
            else:
                result_code = subprocess.run([sys.executable, script_name], timeout=timeout).returncode
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            print(f"\n[LOG] Subprocess completed in {execution_time:.1f} seconds")
            print(f"[LOG] Return code: {result_code}")
            
            return result_code == 0
        else:
            # Normal execution with output capture
            result = subprocess.run([sys.executable, script_name],
                                  capture_output=True, text=True, timeout=timeout,
                                  input=input_data)  # Pass input for interactive scripts
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            print(f"[LOG] Subprocess completed in {execution_time:.1f} seconds")
            print(f"[LOG] Return code: {result.returncode}")
            
            if result.returncode == 0:
                print(f"OK {script_name} completed successfully")
                if result.stdout:
                    print("Output (first 2000 chars):")
                    stdout_preview = result.stdout[:2000] + "..." if len(result.stdout) > 2000 else result.stdout
                    print(stdout_preview)
                if result.stderr:
                    print("Stderr (first 1000 chars):")
                    stderr_preview = result.stderr[:1000] + "..." if len(result.stderr) > 1000 else result.stderr
                    print(stderr_preview)
                return True
            else:
                print(f"ERROR {script_name} failed with return code: {result.returncode}")
                if result.stdout:
                    print("Stdout output (first 2000 chars):")
                    stdout_preview = result.stdout[:2000] + "..." if len(result.stdout) > 2000 else result.stdout
                    print(stdout_preview)
                if result.stderr:
                    print("Stderr output (first 2000 chars):")
                    stderr_preview = result.stderr[:2000] + "..." if len(result.stderr) > 2000 else result.stderr
                    print(stderr_preview)
                return False
            
    except subprocess.TimeoutExpired:
        print(f"ERROR {script_name} timed out after {timeout}s")
        print(f"[LOG] Timeout occurred at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return False
    except Exception as e:
        print(f"ERROR Error running {script_name}: {str(e)}")
        print(f"[LOG] Exception occurred at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return False





def main():
    """메인 함수 - 통합 파이프라인을 실행합니다."""
    print("로컬 논문 파싱 및 알림 통합 시스템 시작")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    parser = argparse.ArgumentParser(description="로컬 논문 파싱 통합 파이프라인 (기간 인자 호환)")
    parser.add_argument('--PAPER_START_DATE', type=str, default=None, help='수집 시작 날짜 (YYYY-MM-DD)')
    parser.add_argument('--PAPER_END_DATE', type=str, default=None, help='수집 종료 날짜 (YYYY-MM-DD)')
    args = parser.parse_args()

    # CLI args take priority, then fall back to env vars
    period_start = args.PAPER_START_DATE or os.getenv("PAPER_START_DATE", "").strip()
    period_end = args.PAPER_END_DATE or os.getenv("PAPER_END_DATE", "").strip()

    if period_start and period_end:
        os.environ["PAPER_START_DATE"] = period_start
        os.environ["PAPER_END_DATE"] = period_end
        print(f"[설정] 수동 기간: {period_start} ~ {period_end}")
    else:
        print("[설정] 수동 기간 미설정: 입력 논문 풀의 Submitted 컬럼 기준으로 처리")
    
    # Step 1: Run Phase 1 - Input pool normalization
    print(f"\n[PHASE 1] 로컬 입력 논문 풀 정규화 시작")
    print(f"[PHASE 1] 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if not run_script("1_input_pool_prepare.py"):
        print("ERROR Phase 1 실패. 파이프라인을 중단합니다.")
        return
    print(f"[PHASE 1] 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # # Step 1-aux_1: Add citation counts (OpenAlex -> Semantic Scholar)
    # print(f"\n[PHASE 1-aux_1] 인용 수 추가 시작")
    # if not run_script("1-aux_1_citation_fetching.py", timeout=300):
    #     print("WARNING Phase 1-aux_1 실패/타임아웃. 인용 수 없이 계속 진행합니다.")
    
    # Step 2: Run Phase 2 - HTML Raw Text Extraction
    print(f"\n[PHASE 2] HTML 텍스트 추출 시작")
    print(f"[PHASE 2] 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[PHASE 2] 실시간 진행상황을 표시합니다...")
    if not run_script("2_html_raw_text.py", show_realtime=True):
        print("ERROR Phase 2 실패. 파이프라인을 중단합니다.")
        return
    print(f"[PHASE 2] 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 3: Run Phase 3 - Organization Parsing with Pre-registered Organizations
    print(f"\nPhase 3: 사전 등록된 기관을 통한 정보 파싱")
    # Automatically select pre-registered organizations mode (option 2) for automated execution
    if not run_script("3_parsing_meta_data.py", "2\n"):
        print("ERROR Phase 3 실패. 파이프라인을 중단합니다.")
        return

    # Step 3-aux_1: Run PDF first-page extraction for remaining papers
    print(f"\nPhase 3-aux_1: PDF 1페이지 텍스트 추출")
    if not run_script("3-aux_1_pdf_version_collecting.py"):
        print("WARNING Phase 3-aux_1 실패. PDF 기반 보조 데이터 없이 계속 진행합니다.")

    # Step 3-aux_2: Filter PDFs using email patterns
    print(f"\nPhase 3-aux_2: 이메일 패턴 기반 PDF 필터링")
    if not run_script("3-aux_2_pdf_parsing.py"):
        print("WARNING Phase 3-aux_2 실패. PDF 기반 기관 데이터 없이 계속 진행합니다.")

    # Step 4: Run Phase 4 - Organization Integration
    print(f"\nPhase 4: 기관 데이터 통합")
    if not run_script("organ_integrate.py"):
        print("ERROR Phase 4 실패. 파이프라인을 중단합니다.")
        return

    # Step 5: Run Phase 5 - Gmail Notification
    print(f"\nPhase 5: Gmail 알림 발송")
    if gmail_sending is None:
        print("ERROR Phase 5 모듈을 불러올 수 없어 Gmail 발송을 건너뜁니다.")
        print("   - Phase 1-4는 성공적으로 완료되었습니다.")
        return
    
    if not run_script("gmail_sending.py"):
        print("WARNING Phase 5 실패. 이메일 발송에 문제가 있었습니다.")
        print("   - Phase 1-4는 성공적으로 완료되었습니다.")
        return
    
    print(f"\n통합 파이프라인 완료!")
    print(f"   - 모든 Phase (1-5) 성공적으로 실행됨")
    print(f"   - 논문 수집, 처리, 필터링, 이메일 발송 완료")
    print(f"   - 결과는 results/ 폴더에서 확인할 수 있습니다")

if __name__ == "__main__":
    main()
