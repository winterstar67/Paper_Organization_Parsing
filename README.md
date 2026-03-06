# arXiv 논문 기관 분석 파이프라인

> arXiv 논문의 저자 소속 기관을 자동으로 추출하고, 지정한 기관의 논문을 Gmail로 보고받는 로컬 파이프라인입니다.

---

## 프로젝트 개요

이 프로젝트는 사용자가 직접 준비한 논문 풀(CSV 파일)을 입력으로 받아, 각 논문의 HTML 또는 PDF에서 저자 소속 기관 정보를 추출합니다. 추출된 기관 정보를 정해진 규칙으로 필터링한 뒤, 관심 기관의 논문 목록을 Gmail API를 통해 이메일로 발송합니다.

파이프라인은 직접 크롤링 단계 없이 동작하며, 모든 처리는 로컬 파일(HTML/PDF)을 기반으로 수행됩니다.

**메인 실행 파일:** `src/integrated.py`

---

## 파이프라인 구조

파이프라인은 총 5단계(Phase)로 구성됩니다.

| Phase | 설명 |
|-------|------|
| Phase 1 | 입력 CSV 논문 데이터 정규화 |
| Phase 2 | HTML 파일에서 저자/기관 원문 텍스트 추출 |
| Phase 3 | 규칙 기반 기관 정보 파싱 및 필터링 |
| Phase 4 | HTML + PDF 기관 정보 통합 |
| Phase 5 | 필터링된 논문 목록을 Gmail API로 이메일 발송 |

---

## 입력 데이터 준비

### 입력 파일 경로

파이프라인의 기본 입력 파일 경로는 아래와 같습니다.

```
input/paper_pool.csv
```

환경변수 `PAPER_POOL_PATH`를 설정하면 다른 경로의 CSV 파일을 사용할 수 있습니다.

---

### 필수 컬럼

| 컬럼명 | 필수 여부 | 설명 |
|--------|-----------|------|
| `Title` | 필수 | 논문 제목 |
| `html_path` | 조건부 필수 | 논문 HTML 파일의 경로. `pdf_path`와 둘 중 최소 1개는 반드시 제공해야 합니다. |
| `pdf_path` | 조건부 필수 | 논문 PDF 파일의 경로. `html_path`와 둘 중 최소 1개는 반드시 제공해야 합니다. |

> `html_path`와 `pdf_path` 중 유효한 로컬 파일이 하나도 존재하지 않는 행(row)은 처리가 불가능합니다.

---

### 선택 컬럼

| 컬럼명 | 설명 |
|--------|------|
| `Authors` | 저자 목록 |
| `Abstract` | 논문 초록 |
| `Submitted` | 논문 제출일 |

---

### 파일 경로 규칙

`html_path` 및 `pdf_path`에는 절대 경로와 상대 경로를 모두 사용할 수 있습니다.

- **상대 경로**는 프로젝트 루트 디렉터리를 기준으로 해석됩니다.
  - 예시: `input/sources/Yes_organ_1.html`
- **절대 경로** 예시: `/mnt/c/.../input/sources/Yes_organ_1.html`
- 원격 URL(http/https)은 소스 파일로 사용되지 않습니다. 이 파이프라인은 로컬 파일만 처리합니다.

---

### CSV 예시

```csv
Title,Authors,Abstract,Submitted,html_path,pdf_path
"Sample Paper A","Alice; Bob","...",2026-03-01,input/sources/Yes_organ_1.html,input/sources/Yes_organ_3.pdf
"Sample Paper B","Charlie","...",2026-03-01,input/sources/No_organ_1.html,input/sources/No_organ_2.pdf
```

---

## 환경 설정

### .env 파일 생성

프로젝트 루트의 `env_example.txt`를 참고하여 `.env` 파일을 생성하세요.

```bash
cp env_example.txt .env
```

이후 `.env` 파일을 열어 아래 환경변수 값을 설정하세요.

---

### 환경변수 설명

| 환경변수 | 필수 여부 | 설명 |
|----------|-----------|------|
| `OPENAI_API_KEY` | 필수 | OpenAI API 키 |
| `RECIPIENT_EMAIL` | 필수 | 결과 이메일을 수신할 주소 |
| `TARGET_ORGANIZATIONS` | 필수 | 필터링 대상 기관명 목록 (JSON 배열 형식) |
| `KNOWN_ORGANIZATIONS` | 필수 | 기관명 정규화에 사용할 알려진 기관명 목록 |
| `EMAIL_PATTERNS` | 필수 | 기관별 이메일 도메인 패턴 (JSON 객체 형식) |
| `LLM_MODEL_BLACKLIST` | 필수 | 오탐 방지를 위한 LLM 모델명 블랙리스트 |
| `PAPER_POOL_PATH` | 선택 | 기본값(`input/paper_pool.csv`) 대신 사용할 입력 CSV 파일 경로 |

---

### Gmail API 설정

Gmail API를 처음 설정하는 경우 아래 단계를 순서대로 진행하세요.

1. [Google Cloud Console](https://console.cloud.google.com/)에서 **Gmail API**를 활성화합니다.
2. **OAuth 2.0 클라이언트 ID**를 생성합니다. 애플리케이션 유형은 **데스크톱 앱(Desktop App)**으로 선택하세요.
3. 발급된 자격증명 JSON 파일을 다운로드하여 `src/credentials.json` 경로에 저장합니다.
4. 파이프라인을 처음 실행하면 브라우저를 통한 OAuth 인증 화면이 표시됩니다. 인증을 완료하면 `src/token.json` 파일이 자동으로 생성됩니다. 이후 실행부터는 저장된 토큰이 사용됩니다.

---

### 의존성 설치

```bash
pip install -r requirements.txt
```

---

## 실행 방법

### 전체 파이프라인 실행

```bash
cd src && python integrated.py
```

### Phase 1만 단독 실행 (선택 사항)

입력 데이터 정규화 단계만 별도로 실행하려는 경우 아래 명령어를 사용하세요.

```bash
python 1_input_pool_prepare.py --input ../input/paper_pool.csv
```

---

## 최종 출력 결과

파이프라인 실행이 완료되면 `results/` 폴더에 각 Phase별 중간 결과 CSV 파일이 생성됩니다.

### Phase별 결과 파일

| Phase | 출력 파일 | 설명 |
|-------|-----------|------|
| Phase 1 | `results/1_URL_of_paper_abstractions.csv` | 정규화된 논문 풀. 컬럼명 통일 및 유효하지 않은 행 제거가 적용됩니다. |
| Phase 2 | `results/2_html_raw_text.csv` | HTML 파일에서 추출한 저자 및 소속 기관 원문 텍스트가 포함됩니다. |
| Phase 3 | `results/3_parsing_meta_data.csv` | 규칙 기반으로 파싱된 기관 정보가 포함됩니다. 블랙리스트 및 패턴 필터링이 적용됩니다. |
| Phase 4 | `results/organ_integrate.csv` | HTML과 PDF에서 각각 추출한 기관 정보를 통합한 최종 기관 데이터입니다. |
| Phase 5 | Gmail 이메일 발송 | `TARGET_ORGANIZATIONS`에 해당하는 논문 목록이 HTML 형식 이메일로 발송됩니다. |

### 이메일에 포함되는 정보

발송되는 이메일에는 필터링된 각 논문에 대해 아래 정보가 포함됩니다.

- 논문 제목
- 저자
- 소속 기관
- 제출일

---

## 프로젝트 구조

```
.
├── src/                  # 파이프라인 스크립트 및 메인 실행 파일
├── input/                # 입력 논문 풀 및 소스 파일 (HTML/PDF)
├── results/              # Phase별 중간 및 최종 결과 파일
└── env_example.txt       # 환경변수 설정 템플릿
```
