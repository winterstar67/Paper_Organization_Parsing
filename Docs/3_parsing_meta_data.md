# 3_parsing_meta_data.py 기능 설명서

## 개요

Phase 3 스크립트로 Phase 2에서 수집한 HTML 데이터를 분석하여 연구기관 정보를 추출합니다. AI 기반 추출과 사전 기관 매칭 두 가지 모드를 지원합니다.

## 핵심 기능

### 1. 처리 모드 선택

**AI 모드 (모드 1)**
- ChatGPT API + 사전 기관 목록 모두 사용
- OpenAI API 키 필요
- 높은 정확도의 기관 추출 가능
- 토큰 사용량 추적

**사전 기관 전용 모드 (모드 2)**
- 환경변수 `KNOWN_ORGANIZATIONS`에 설정된 기관만 검색
- API 비용 없음
- 빠른 처리 속도
- 정확히 일치하는 기관만 추출

### 2. 데이터 처리 파이프라인

#### 입력 데이터
- **소스**: `results/2_html_raw_text.csv`
- **주요 컬럼**: `html_raw_text_with_tags_filtered`, `Authors`

#### 처리 단계

**1단계: HTML 정리**
- 불필요한 style, href, id 등 속성 제거
- 이미지 태그, br 태그 정리
- 종료 태그만 있는 줄 제거
- 연속 공백과 줄바꿈 정리

**2단계: 저자 이름 제거**
- `Authors` 컬럼의 저자 이름들을 HTML에서 제거
- 세미콜론으로 구분된 저자 목록 처리
- 단어 경계 확인하여 정확한 제거

**3단계: 기관 추출**
- **AI 모드**: GPT API로 기관 추출 + 사전 기관 보완
- **사전 기관 모드**: 사전 설정 기관만 텍스트 매칭

### 3. 결과 저장 방식

#### 컬럼 정리 기능 (신규 추가)

**항상 제거되는 컬럼들**:
- `html_raw_text`
- `html_raw_text_with_tags`
- `html_raw_text_with_tags_filtered`

**사전 기관 모드에서 추가로 제거되는 컬럼들**:
- `input_tokens`
- `output_tokens`

#### AI 모드 저장 파일들

**1) 메인 결과 파일**
- `results/3_parsing_meta_data.csv`: 전체 결과 (HTML 컬럼 제거됨)

**2) 상세 결과 파일**
- `results/3_parsing_meta_data_ai_full.csv`: GPT 전체 결과 (HTML 컬럼 제거됨)
- `results/3_parsing_meta_data_ai_filtered.csv`: 사전 기관 필터링된 결과

**3) 백업 및 중간 파일**
- `backup/3_parsing_meta_data/3_parsing_meta_data_YYYY-MM-DD HHMM.csv`
- `results/3_parsing_meta_data_processing.csv`: 처리 중 중간 저장

#### 사전 기관 전용 모드 저장

**메인 결과 파일**:
- `results/3_parsing_meta_data.csv`: 사전 기관이 발견된 논문만 (HTML, 토큰 컬럼 제거됨)

## 환경 설정

### 필수 환경변수

```env
# AI 모드 사용 시 필수
OPENAI_API_KEY=your_openai_api_key_here
GPT_MODEL=gpt-3.5-turbo

# 사전 기관 목록 (JSON 형식)
KNOWN_ORGANIZATIONS=["Google", "Microsoft", "OpenAI", "Stanford University", "MIT", "Carnegie Mellon University"]

# 타겟 기관 (Phase 4에서 사용)
TARGET_ORGANIZATIONS=["Google", "Microsoft"]
```

### GPT 프롬프트 설계

**추출 대상**:
- 대학교, 연구소, 기업, 연구실, 센터
- Carnegie Mellon University, Google, MIT, Microsoft Research 등

**제외 대상**:
- 저자 이름
- 이메일 주소
- 도시명, 국가명

## 처리 성능 및 최적화

### 배치 처리
- 10개 논문마다 중간 저장 실행
- 진행률과 예상 완료 시간 표시
- 에러 발생 시 부분 결과 보존

### 메모리 최적화
- HTML 컬럼 제거로 저장 용량 대폭 감소
- 처리 중간에만 HTML 데이터 유지
- 최종 결과에서는 essential 컬럼만 보존

### 토큰 사용량 추적
- API 호출별 input/output 토큰 기록
- 총 사용량 통계 제공
- 비용 예측 가능

## 실행 시나리오

### AI 모드 실행 예시

```
============================================================
Phase 3: 논문 메타데이터 파싱 및 기관 추출
============================================================
처리 모드를 선택하세요:
1. AI 모드 (GPT + 사전 기관): ChatGPT API와 사전 설정 기관 모두 사용
2. 사전 기관 전용 모드: 사전 설정 기관 목록만 사용 (API 비용 없음)
모드를 선택하세요 (1 또는 2): 1

선택된 모드: AI 모드 (GPT + 사전 기관)
============================================================
총 68개의 논문 데이터를 로드했습니다.
사전 설정 기관 6개 로드 완료

논문 메타데이터 파싱 시작
총 68개 논문 처리 예정
10개 논문마다 중간 저장 실행
사전 설정 기관: 6개
처리 모드: AI + 사전 기관

[  1/68] (1.5%) Paper 1
경과시간: 0.0분 | 예상 남은시간: 34.2분
Cleaned HTML length: 1024 characters
HTML after author removal: 891 characters
Paper 1 - Token usage: 156 input, 23 output
Paper 1 - GPT response: ["Stanford University", "Google Research"]
GPT 추출 기관 (2개): ["Stanford University", "Google Research"]
사전 설정 기관 발견 (2개): ["Stanford University", "Google"]
INFO GPT가 누락한 기관 추가: Google
최종 기관 (3개): ["Stanford University", "Google Research", "Google"]
저장용 DataFrame에서 제거된 컬럼: ['html_raw_text', 'html_raw_text_with_tags', 'html_raw_text_with_tags_filtered']
OK 중간 저장 완료 (10개 논문 처리됨): results/3_parsing_meta_data.csv
```

### 사전 기관 전용 모드 실행 예시

```
모드를 선택하세요 (1 또는 2): 2

선택된 모드: 사전 기관 전용 모드
============================================================
총 68개의 논문 데이터를 로드했습니다.
사전 설정 기관 6개 로드 완료

[  1/68] (1.5%) Paper 1
Cleaned HTML length: 1024 characters
HTML after author removal: 891 characters
사전 설정 기관 발견 (1개): ["Stanford University"]
최종 기관 (1개): ["Stanford University"]
저장용 DataFrame에서 제거된 컬럼: ['html_raw_text', 'html_raw_text_with_tags', 'html_raw_text_with_tags_filtered', 'input_tokens', 'output_tokens']
```

## 결과 분석

### 통계 정보

**AI 모드 결과**:
```
=== 기관 추출 결과 통계 ===
Paper 1: 3개 기관 - ["Stanford University", "Google Research", "Google"] (토큰: 156+23)
Paper 2: 1개 기관 - ["MIT"] (토큰: 134+15)
...

전체 추출된 기관 수: 127개
기관 정보가 있는 논문: 45개
전체 논문 수: 68개
사전 설정 기관과 일치하는 논문: 23개
총 토큰 사용량: 8456 input + 1234 output = 9690 total

=== 전체 고유 기관 목록 (34개) ===
- Carnegie Mellon University
- Google
- Google Research
- MIT
- Microsoft
- Microsoft Research
- OpenAI
- Stanford University
...
```

**사전 기관 전용 모드 결과**:
```
전체 추출된 기관 수: 67개
기관 정보가 있는 논문: 23개
전체 논문 수: 68개
사전 기관 전용 모드 - API 비용 없음
```

## 에러 처리

### 일반적인 에러 상황
- OpenAI API 키 누락: 사전 기관 전용 모드 권장
- 네트워크 오류: 중간 저장된 결과 활용
- JSON 파싱 실패: 빈 배열로 처리
- HTML 정리 실패: 원본 HTML 사용

### 복구 방법
- `results/3_parsing_meta_data_processing.csv`에서 중간 결과 확인
- 백업 폴더에서 이전 결과 복구 가능
- 개별 논문 처리 실패는 빈 배열로 처리하고 계속 진행

## 성능 팁

### 비용 절약
- 사전 기관 전용 모드 사용 (API 비용 0원)
- 필요한 기관만 `KNOWN_ORGANIZATIONS`에 설정

### 처리 속도 향상
- HTML 컬럼 제거로 I/O 성능 향상
- 중간 저장으로 재시작 시간 단축
- 배치 처리로 메모리 효율성 개선

### 정확도 향상
- AI 모드에서 GPT + 사전 기관 조합 사용
- 저자 이름 제거로 false positive 감소
- 정제된 HTML로 추출 품질 향상