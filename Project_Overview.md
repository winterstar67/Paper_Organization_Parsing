# arXiv 논문 메타데이터 수집기 프로젝트

## 이 파일의 목적
- 이 프로젝트를 처음 보는 사람들을 위한 가이드이다. 주로 Overview와 함께 아래 내용들을 정리한다.
    - 프로젝트의 motivation
    - 프로젝트의 목적
    - 프로젝트 구조
    - 프로젝트 내의 각 코드 파일과 폴더의 기능
- 프로젝트 구조, 디렉토리, 각 코드의 역할을 쉽게 이해할 수 있도록 작성해야 한다.
- 이 파일을 작성할 때는 반드시 한국어로 작성해야 한다.

---

## 🎯 프로젝트 개요

이 프로젝트는 **arXiv에서 최신 AI/ML 논문들의 메타데이터를 자동으로 수집하고 정리하는 시스템**입니다.

### 핵심 기능
- 최근 발표된 arXiv 논문들의 상세 정보 수집
- 논문 제목, 저자, 소속기관, 주제 분야 등 체계적 분류
- CSV 형태로 데이터 저장 및 누적 관리
- 저자의 과거 소속 기관 추적 (빅테크 경력 포함)

### 수집하는 데이터
- **논문 제목** (Title)
- **저자 정보** (Authors)
- **주제 분야** (Subjects)
- **제출일/발표일** (Submitted/Announced dates)
- **arXiv URL** 및 HTML URL
- **HTML 저자 상세 정보** (ltx_authors 태그 내용)
- **실패한 요청 추적** (Failed_list.csv)

---

## 📁 프로젝트 디렉토리 구조

```
3_Paper_collect_and_extract_organization_of_paper/
├── 📄 1_URLs of Paper Abstract Page.py     # 메인 데이터 수집 스크립트
├── 📄 2_html_raw_text.py                   # HTML 저자 정보 추출 스크립트
├── 📄 2_1_html_raw_text_check.py           # HTML 데이터 검증 도구
├── 📁 results/                             # 수집된 데이터 저장소
│   ├── 1_URL_of_paper_abstractions.csv    # 메인 데이터 파일
│   ├── 2_html_raw_text.csv                # HTML 저자 정보 파일
│   ├── html_raw_text.p                    # HTML 데이터 pickle 파일
│   ├── html_raw_text.txt                  # HTML 데이터 텍스트 파일
│   └── Failed_list.csv                    # 실패한 요청 기록
├── 📁 backup/                              # 백업 파일들
│   ├── 1_URL_of_paper_abstractions/       # 메인 데이터 백업
│   ├── 2_html_raw_text/                   # HTML 데이터 백업
│   └── Failed/                            # 실패 요청 백업
├── 📄 Project_Overview.md                  # 이 파일 - 프로젝트 가이드
├── 📄 Work_state.md                        # 작업 진행 상황 기록
└── 📄 CLAUDE.md                           # AI 개발 보조 설정 파일
```

---

## 🔧 각 Python 파일의 기능

### 1. `1_URLs of Paper Abstract Page.py` ⭐ **메인 스크립트**
**역할**: arXiv 검색 결과 페이지에서 논문 메타데이터 수집
- **입력**: 날짜 범위 (기본: 최근 2일)
- **대상 주제**: cs.AI, cs.LG, cs.CL, cs.CV
- **출력**: `results/1_URL_of_paper_abstractions.csv`

**수집하는 정보**:
- ✅ 수집 시간 (Collected_date)
- ✅ arXiv 논문 URL (abs_url)
- ✅ HTML URL (html_url)
- ✅ 논문 제목 (Title)
- ✅ 저자 목록 (Authors)
- ✅ 제출일 (Submitted)
- ✅ 발표일 (Originally_announced)
- ✅ 주제 분야 (Subjects)
- ✅ 실패한 요청 기록 (Subject, Start_date, End_date, Failed_time)

**주요 기능**:
- 중복 논문 자동 스킵 및 업데이트 처리
- 기존 데이터에 신규 데이터 누적 저장
- 일별 백업 파일 자동 생성
- 20회마다 10초 대기 (서버 부하 방지)
- 실패한 요청 자동 기록 및 백업
- URL 기반 중복 제거 및 정렬
- 논문 제출일 변경 시 자동 업데이트

### 2. `2_html_raw_text.py` **HTML 저자 정보 추출 스크립트**
**역할**: arXiv HTML 페이지에서 상세 저자 정보 추출
- **입력**: `results/1_URL_of_paper_abstractions.csv`
- **처리**: 각 논문의 HTML URL에서 `<div class="ltx_authors">` 태그 내용 추출
- **출력**: 
  - `results/2_html_raw_text.csv` (CSV 형식)
  - `results/html_raw_text.p` (Pickle 형식)
  - `results/html_raw_text.txt` (텍스트 형식)

**수집하는 정보**:
- ✅ 기존 메타데이터 + html_raw_text 컬럼
- ✅ 저자 상세 정보 (소속 기관 포함)
- ✅ 특수 문자(\n, \xa) 그대로 보존

**처리 결과**:
- **성공**: ltx_authors 태그의 모든 텍스트
- **HTML 접근 불가**: "NO_HTML"
- **태그 없음**: "NO_ltx_authors"

**주요 기능**:
- 백업 파일 자동 생성
- 요청 간 1초 대기, 20개마다 10초 대기
- 처리 결과 통계 출력
- 다중 형식 출력 (CSV, Pickle, TXT)

### 3. `2_1_html_raw_text_check.py` **HTML 데이터 검증 도구**
**역할**: 수집된 HTML 저자 정보 데이터의 품질 검증
- **입력**: `results/2_html_raw_text.csv`, `html_raw_text.p`, `html_raw_text.txt`
- **기능**: 
  - 세 가지 형식(CSV, Pickle, TXT) 데이터 로드 및 비교
  - 데이터 일관성 검증
  - 특수 문자 보존 확인
  - 처리 결과 통계 분석

**검증 항목**:
- ✅ 파일별 데이터 개수 일치 확인
- ✅ 성공/실패 상태별 분류 통계
- ✅ 첫 번째 성공 데이터 미리보기
- ✅ 특수 문자(줄바꿈 등) 보존 상태 확인


---

## 🚀 사용 방법

### 1. 환경 설정
```bash
pip install requests beautifulsoup4 pandas
```

### 2. 데이터 수집 실행
```bash
# Phase 1: 기본 논문 목록 수집
python "1_URLs of Paper Abstract Page.py"

# Phase 2: HTML 저자 정보 추출
python "2_html_raw_text.py"

# Phase 3: 수집된 데이터 검증
python "2_1_html_raw_text_check.py"
```

### 3. 결과 확인
- **메인 파일**: `results/1_URL_of_paper_abstractions.csv`
- **저자 정보 파일**: `results/2_html_raw_text.csv`
- **추가 데이터**: `results/html_raw_text.p` (Pickle), `results/html_raw_text.txt` (텍스트)
- **실패 기록**: `results/Failed_list.csv`
- **백업 파일**: `backup/` 디렉토리 내 각 단계별 백업

---

## 📊 현재 상태

### ✅ 완성된 기능 (2025-08-24)
#### Phase 1: 기본 데이터 수집 (완료)
- arXiv 검색 페이지 크롤링 및 메타데이터 추출
- 중복 검사 및 업데이트 처리
- 실패한 요청 자동 추적

#### Phase 2: HTML 저자 정보 추출 (완료)
- 개별 논문 HTML 페이지에서 상세 저자 정보 수집
- 다중 형식 출력 (CSV, Pickle, TXT)

#### Phase 3: 데이터 검증 도구 (완료)
- 수집된 데이터의 품질 검증
- 형식별 데이터 일관성 확인

---

## 🎯 프로젝트의 최종 목표

1. **논문 메타데이터 자동 수집**: 최신 AI/ML 논문들의 체계적 수집
2. **저자 상세 정보 추출**: HTML 페이지에서 저자 소속 기관 등 상세 정보 수집
3. **데이터 분석**: 연구 트렌드, 기관별 연구 현황 분석
4. **자동화**: 정기적인 데이터 수집 및 업데이트 시스템

이 프로젝트는 AI/ML 연구 동향을 파악하고, 저자들의 소속 기관 정보를 통해 연구 생태계를 이해하는데 도움을 주는 것을 목표로 합니다.