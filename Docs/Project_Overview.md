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
- AI 기반 조직 정보 추출 및 정규화
- Gmail을 통한 자동 알림 시스템

### 수집하는 데이터
- **논문 제목** (Title)
- **저자 정보** (Authors)
- **주제 분야** (Subjects: cs.AI, cs.LG, cs.CL, cs.CV)
- **제출일/발표일** (Submitted/Announced dates)
- **arXiv URL** 및 HTML URL
- **논문 코멘트** (Comments: 페이지 수, 수락 정보 등)
- **저널 참조** (Journal_ref: 출판된 저널 정보)
- **논문 초록** (Abstract)
- **HTML 저자 상세 정보** (ltx_authors 태그 내용)
- **AI 추출 조직 정보** (OpenAI GPT-3.5-turbo 기반)
- **정규화된 기관명** (통합 조직 데이터)

---

## 📁 프로젝트 디렉토리 구조

```
3_Paper_collect_and_extract_organization_of_paper/
├── 📁 src/                                   # 메인 소스코드 디렉토리
│   ├── 📄 1_URLs of Paper Abstract Page.py   # Phase 1: arXiv 검색 & 메타데이터 수집
│   ├── 📄 2_html_raw_text.py                 # Phase 2: HTML 저자 정보 추출
│   ├── 📄 3_parsing_meta_data.py             # Phase 3: AI 기반 조직 정보 추출
│   ├── 📄 4_organ_integrate.py               # Phase 4: 조직 데이터 통합 및 정규화
│   ├── 📄 5_gmail_sending.py                 # Phase 5: Gmail 알림 발송
│   ├── 📄 integrated.py                      # 전체 파이프라인 통합 실행 스크립트
│   ├── 📄 credentials.json                   # Gmail API 인증 정보
│   └── 📄 token.json                         # Gmail API 토큰
├── 📁 results/                               # 처리 결과 및 데이터 파일
│   ├── 📄 1_URL_of_paper_abstractions.csv    # Phase 1 결과: 기본 논문 메타데이터
│   ├── 📄 2_html_raw_text.csv                # Phase 2 결과: HTML 저자 정보
│   ├── 📄 2_2_failed_papers.csv              # HTML 추출 실패한 논문 목록
│   ├── 📄 3_parsing_meta_data.csv            # Phase 3 결과: AI 추출 조직 정보
│   ├── 📄 3_parsing_meta_data_processing.csv # Phase 3 중간 처리 파일
│   ├── 📄 4_organ_integrate.csv              # Phase 4 결과: 최종 통합 데이터
│   └── 📄 html_raw_text.* (p/txt)            # 다중 형식 HTML 데이터
├── 📁 backup/                                # 자동 백업 파일들
│   ├── 📁 1_URL_of_paper_abstractions/       # Phase 1 백업 (타임스탬프별)
│   ├── 📁 2_html_raw_text/                   # Phase 2 백업 (타임스탬프별)
│   ├── 📁 3_parsing_meta_data/               # Phase 3 백업 (타임스탬프별)
│   └── 📁 4_organ_integrate/                 # Phase 4 백업 (타임스탬프별)
├── 📁 Example_files/                         # HTML 구조 샘플 및 문서화
│   └── 📁 2_Extract author and Organization infos/ # 다양한 저자 정보 형식 예시
├── 📁 Docs/                                  # 프로젝트 문서
│   ├── 📄 CLAUDE.md                          # Claude Code 작업 가이드
│   ├── 📄 Project_Overview.md                # 이 파일 - 한국어 프로젝트 개요
│   └── 📄 Work_state.md                      # 개발 진행 상황 기록
└── 📄 .env                                   # 환경변수 설정 파일 (수동 생성 필요)
```

---

## 🔧 각 Python 파일의 기능 및 실행 순서

### Phase 1: `1_URLs of Paper Abstract Page.py` ⭐ **메인 데이터 수집 스크립트**
**역할**: arXiv 검색 결과 페이지에서 논문 메타데이터 수집
- **입력**: 역순 검색 방식 (어제부터 2주 전까지 하루씩 검색)
- **대상 주제**: cs.AI, cs.LG (AI/ML 핵심 분야)
- **출력**: `results/1_URL_of_paper_abstractions.csv`, `results/ID_TABLE.csv`

**수집하는 정보**:
- ✅ 수집 시간 (Collected_date)
- ✅ arXiv 논문 URL (abs_url)
- ✅ HTML URL (html_url)
- ✅ 논문 제목 (Title)
- ✅ 저자 목록 (Authors)
- ✅ 제출일 (Submitted)
- ✅ 발표일 (Originally_announced)
- ✅ 주제 분야 (Subjects)
- ✅ 논문 초록 (Abstract)
- ✅ 논문 코멘트 (Comments)
- ✅ 저널 참조 (Journal_ref)

**주요 기능**:
- **역순 날짜 검색**: 어제부터 시작하여 논문이 발견될 때까지 하루씩 역순 검색 (최대 2주)
- **다중 주제 통합 검색**: cs.AI, cs.LG를 하나의 URL로 동시 검색
- **하루 단위 검색**: 항상 1일 단위로만 검색하여 정확성 확보
- **논문 발견 시 중단**: 논문이 있는 날짜를 찾으면 해당 날짜만 수집하고 종료
- **Submitted 날짜 표준화**: "8 Jan 2024" → "2024-01-08" 자동 변환
- **ID 테이블 관리**: ID, Paper_Title, Submitted 3컬럼 체계적 관리
- **중복 제거**: 제목 기반 중복 논문 자동 필터링
- **백업 시스템**: 검색 날짜 범위 기반 백업 파일 자동 생성 (StartDate_EndDate 형식)

### Phase 2: `2_html_raw_text.py` **HTML 저자 정보 추출 스크립트**
**역할**: arXiv HTML 페이지에서 상세 저자 정보 추출
- **입력**: `results/1_URL_of_paper_abstractions.csv`
- **처리**: 각 논문의 HTML URL에서 `<div class="ltx_authors">` 태그 내용 추출
- **출력**: 
  - `results/2_html_raw_text.csv` (메인 결과 파일)
  - `results/2_2_failed_papers.csv` (실패한 논문 목록)
  - `results/html_raw_text.p/.txt` (다중 형식)

**수집하는 정보**:
- ✅ 기존 메타데이터 + html_raw_text 컬럼
- ✅ 저자 상세 정보 (소속 기관 포함)
- ✅ 특수 문자(\\n, \\xa) 그대로 보존

**처리 결과**:
- **성공**: ltx_authors 태그의 모든 텍스트
- **HTML 접근 불가**: "NO_HTML"
- **태그 없음**: "NO_ltx_authors"

**주요 기능**:
- ✅ 실패한 논문 별도 추적 및 재시도 목록 생성
- ✅ 요청 간 5.2초 대기 (약 21분/243개 논문)
- ✅ 다중 형식 출력 (CSV, Pickle, TXT)
- ✅ 논문 날짜 범위 기반 자동 백업 시스템

### Phase 3: `3_parsing_meta_data.py` **AI 기반 조직 정보 추출 스크립트**
**역할**: HTML 데이터에서 OpenAI GPT-3.5-turbo를 활용한 조직 정보 추출
- **입력**: `results/2_html_raw_text.csv`
- **AI 활용**: OpenAI GPT-3.5-turbo API
- **출력**: 
  - `results/3_parsing_meta_data.csv` (메인 결과 파일)
  - `results/3_parsing_meta_data_processing.csv` (처리 중간 파일)

**수집하는 정보**:
- ✅ 기존 메타데이터 + organization 컬럼
- ✅ 대학교, 연구소, 기업 등 모든 조직 정보
- ✅ JSON 형식 리스트로 구조화된 조직 데이터
- ✅ input_tokens, output_tokens 컬럼으로 API 비용 추적

**주요 기능**:
- ✅ HTML 전처리: 불필요한 속성 제거 및 정리
- ✅ GPT API 통합: 영어 프롬프트로 정확한 조직 추출
- ✅ 토큰 사용량 실시간 추적
- ✅ 10개 배치 처리 및 중간 저장
- ✅ 중복 제거 및 오류 처리
- ✅ 논문 날짜 범위 기반 자동 백업 시스템

**처리 결과**:
- **성공**: JSON 형식 조직 리스트 (예: `["Google", "TU Delft"]`)
- **실패**: 빈 리스트 `[]`

### Phase 4: `4_organ_integrate.py` **조직 데이터 통합 및 정규화 스크립트**
**역할**: 조직 정보 통합 및 정규화 처리
- **입력**: `results/3_parsing_meta_data.csv`
- **처리**: 조직 데이터 추출, 정규화, 통합
- **출력**: 
  - `results/4_organ_integrate.csv` (최종 통합 결과)
  - `All_organization.txt` (고유 조직 목록)

**수집하는 정보**:
- ✅ 기존 메타데이터 + unified_organ 컬럼
- ✅ 정규화된 조직명 (소문자, 특수문자 제거)
- ✅ 고유 조직 목록 추출

**주요 기능**:
- ✅ JSON 형식 조직 데이터 파싱
- ✅ 조직명 정규화 (소문자, 영숫자만 유지)
- ✅ 중복 제거 및 고유 조직 추출
- ✅ 논문 날짜 범위 기반 자동 백업 시스템
- ✅ 상세 통계 및 예시 출력

**정규화 예시**:
- "Carnegie Mellon University" → "carnegiemellonuniversity"

### Phase 5: `5_gmail_sending.py` **Gmail 알림 발송 스크립트**
**역할**: 특정 조직별 논문 필터링 및 Gmail을 통한 알림 발송
- **입력**: `results/4_organ_integrate.csv`
- **필터링**: 환경변수 TARGET_ORGANIZATIONS 기반
- **발송**: Gmail SMTP 서버 사용
- **출력**: 필터링된 논문 리스트 이메일

**주요 기능**:
- ✅ 조직별 논문 자동 필터링
- ✅ HTML 형식 이메일 생성 (논문 날짜 범위 표시 및 모든 기관 목록 포함)
- ✅ Gmail API 인증 및 발송
- ✅ 날짜 범위 기반 이메일 제목 생성
- ✅ 필터링 결과 로컬 저장

### 통합 실행: `integrated.py` **전체 파이프라인 오케스트레이터**
**역할**: Phase 1-5를 순차적으로 실행하는 통합 스크립트
- **기능**: 전 단계 자동 실행 및 로깅
- **오류 처리**: 각 단계별 상세 오류 처리
- **로깅**: 실행 시간 및 진행 상황 추적
- **백업**: 자동 백업 관리

**주요 특징**:
- ✅ Windows 인코딩 문제 자동 해결
- ✅ Phase별 실행 시간 측정
- ✅ 실시간 진행 상황 출력
- ✅ 오류 발생 시 중단 및 로그 기록

---

## 🚀 사용 방법

### 1. 환경 설정
```bash
# 필수 Python 패키지 설치
pip install requests beautifulsoup4 pandas pytz openai python-dotenv

# Gmail 기능 사용 시 추가 설치
pip install google-auth google-auth-oauthlib google-api-python-client
```

### 2. 환경변수 설정
프로젝트 루트에 `.env` 파일 생성:
```env
# Phase 3 AI 처리를 위한 필수 설정
OPENAI_API_KEY=your_openai_api_key
GPT_MODEL=gpt-3.5-turbo

# 조직 필터링 설정 (JSON 형식)
KNOWN_ORGANIZATIONS=["Google", "Microsoft", "OpenAI", "Stanford University"]
TARGET_ORGANIZATIONS=["Google", "Microsoft"]

# Gmail 설정 (선택사항)
GMAIL_USER=your_email@gmail.com
GMAIL_PASSWORD=your_app_password
```

### 3. 실행 방법

#### 통합 실행 (권장)
```bash
cd src/
python integrated.py
```

#### 개별 단계 실행
```bash
cd src/

# Phase 1: 기본 논문 목록 수집
python "1_URLs of Paper Abstract Page.py"

# Phase 2: HTML 저자 정보 추출
python "2_html_raw_text.py"

# Phase 3: AI 기반 조직 정보 추출
python "3_parsing_meta_data.py"

# Phase 4: 조직 데이터 통합 및 정규화
python "4_organ_integrate.py"

# Phase 5: Gmail 알림 발송
python "5_gmail_sending.py"
```

### 4. 결과 확인
- **Phase 1 결과**: `results/1_URL_of_paper_abstractions.csv`
- **Phase 2 결과**: `results/2_html_raw_text.csv`
- **Phase 3 결과**: `results/3_parsing_meta_data.csv`
- **Phase 4 결과**: `results/4_organ_integrate.csv` (최종 데이터)
- **백업 파일**: `backup/` 디렉토리 내 각 단계별 논문 날짜 범위 백업 (StartDate_EndDate 형식)
- **실패 논문**: `results/2_2_failed_papers.csv` (재시도 가능)

---

## 📊 프로젝트의 현재 상태

### ✅ 완성된 기능 (2025-08-30)

#### Phase 1-5: 전체 파이프라인 (완료)
- **Phase 1**: arXiv 검색 페이지 크롤링 및 메타데이터 추출
- **Phase 2**: 개별 논문 HTML 페이지에서 상세 저자 정보 수집
- **Phase 3**: OpenAI GPT-3.5-turbo 기반 조직 정보 자동 추출
- **Phase 4**: 조직 데이터 통합 및 정규화 처리
- **Phase 5**: Gmail을 통한 조직별 논문 자동 알림

#### 최신 개선사항
- **구조 개선**: 모든 소스코드를 `src/` 디렉토리로 이동하여 체계적 관리
- **통합 파이프라인**: `integrated.py`로 전 단계 자동화 실행
- **토큰 추적**: API 사용량 정확한 모니터링 (Phase 3)
- **중간 저장**: 파일 잠금 오류 방지를 위한 중복 저장 시스템
- **백업 시스템**: 논문 날짜 범위 기반 백업 파일명 (StartDate[YYMMDD]_EndDate[YYMMDD])
- **Gmail 개선**: 날짜 범위 기반 제목 및 모든 기관 목록 표시
- **Windows 호환성**: CP949 인코딩 문제 완전 해결
- **코드 품질 개선**: 모든 함수에 타입 어노테이션 및 상세한 문서화 추가 (2025-08-30)
- **메타데이터 확장**: Comments 및 Journal_ref 컬럼 추가 (2025-08-31)
- **검색 효율성 개선**: 다중 subject 통합 검색 및 단일 날짜 범위 검색으로 요청 횟수 최소화 (2025-08-31)
- **시간대 관리 강화**: 한국/미국 시간 이중 기록, 백업 파일명 최신 제출일 기반 변경 (2025-09-03)
- **데이터 정리**: 중복 컬럼(Originally_announced, unified_organ) 제거, 사전 등록 기관 추적 (2025-09-03)
- **날짜 로직 혁신**: 공휴일/주말 알고리즘 제거, 단순한 역순 검색 방식 도입 (2025-09-03)
- **ID 테이블 확장**: ID_TABLE.csv에 Submitted 컬럼 추가, YYYY-MM-DD 표준 형식으로 저장 (2025-09-03)
- **역순 검색 시스템**: 어제부터 2주 전까지 하루 단위 역순 검색으로 논문 발견 (2025-09-03)

#### 🔄 날짜 범위 로직 개선 히스토리 (2025-09-03)

**arXiv 게시 메커니즘 발견**:
- **핵심 발견**: arXiv는 오늘 제출된 논문을 당일에 게시하지 않음 (최소 1일 지연)
- 2025-09-02 11:16 AM 검색에서도 당일(09-02) 논문 전혀 검색되지 않음

**구현된 날짜 전략 진화**:
1. **초기 전략**: 공휴일/주말 고려한 복잡한 날짜 계산 로직
2. **데이터 기반 전략**: ID_TABLE.csv 기반 지능형 날짜 범위 계산 (2025-09-03 오전)
3. **단순 역순 검색**: 복잡한 로직 제거, 어제부터 2주 역순 검색 방식 (2025-09-03 오후)
   - 어제(1일 전)부터 검색 시작
   - 2일 전, 3일 전, ... 최대 14일 전(2주)까지 역순 검색
   - 논문 발견 즉시 해당 날짜만 수집하고 종료
   - 항상 하루 단위로만 검색

**주요 개선사항**:
- ✅ **Submitted 날짜 표준화**: arXiv 형식을 YYYY-MM-DD로 변환하여 ID_TABLE.csv에 저장
- ✅ **단순하고 확실한 검색**: 복잡한 로직 대신 간단한 역순 검색
- ✅ **논문 누락 방지**: 최대 2주까지 검색하여 논문 발견 보장
- ✅ **중복 방지**: 기존 논문 제목 기반 자동 필터링
- ✅ **백업 파일명**: 검색 날짜 범위 기반 백업 파일 생성

**현재 상태**: 단순하고 확실한 역순 검색 시스템 완성

#### 성능 지표
- **처리 속도**: 243개 논문을 약 21분에 완전 처리
- **성공률**: HTML 추출 90%+, AI 조직 추출 60%+
- **조직 식별**: 24개 이상 고유 조직 자동 추출

---

## 🎯 프로젝트의 목표 및 확장 계획

### 현재 완료된 목표
1. **논문 메타데이터 자동 수집**: 최신 AI/ML 논문들의 체계적 수집 ✅
2. **저자 상세 정보 추출**: HTML 페이지에서 저자 소속 기관 등 상세 정보 수집 ✅
3. **AI 기반 조직 정보 추출**: OpenAI를 활용한 구조화된 조직 데이터 생성 ✅
4. **조직 데이터 통합 및 정규화**: 고유 조직 식별 및 정규화 처리 ✅
5. **이메일 알림 시스템**: Gmail 기반 자동 논문 보고서 발송 ✅
6. **통합 파이프라인**: 전 단계 자동화 실행 시스템 ✅

### 향후 확장 계획
7. **저자-기관 정확한 매핑**: 각 저자와 기관의 정확한 관계 매핑 🔄
8. **저자 이력 추적**: 저자들의 기관 변화 이력 추적 시스템 📋
9. **웹 인터페이스**: 조직별 논문 필터링 웹 애플리케이션 📋
10. **Knowledge Graph**: 저자-기관 연구 네트워크 시각화 📋
11. **소셜 미디어 통합**: 저자 SNS 계정 자동 검색 및 저장 📋
12. **맞춤형 뉴스레터**: 사용자 지정 기관 기준 일일 구독 서비스 📋

### 특별 기능
- **빅테크 경력 추적**: 현재 학계에 있더라도 과거 대기업 경험이 있는 연구자 식별
- **실시간 논문 알림**: 하루 단위 최신 논문 자동 수집 및 알림
- **다국어 지원**: 한국어 프로젝트 문서와 영어 기술 문서 병행

이 프로젝트는 AI/ML 연구 생태계의 전체적인 네트워크와 동향을 이해하여, 연구자들의 이동 패턴과 협업 관계를 분석하는 종합적인 시스템을 구축하는 것을 목표로 합니다.