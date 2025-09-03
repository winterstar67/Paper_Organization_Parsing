# 1_URLs of Paper Abstract Page.py 기능 설명서

## 개요
Phase 1 스크립트로 arXiv에서 AI/ML 논문의 메타데이터를 수집하는 기능을 담당합니다. ID 관리 시스템을 통해 중복 방지 및 순차적 ID 부여를 지원합니다.

## 핵심 기능

### 1. ID 관리 시스템
- **ID 형식**: YYMMDD_순번 (예: 250830_1, 250830_2, 250830_3...)
- **중복 방지**: 논문 제목 기준으로 ID_TABLE.csv에서 중복 검사
- **순차 증가**: 같은 날짜 내에서 1, 2, 3... 순서대로 ID 생성

### 2. 데이터 수집 범위
- **대상 주제**: cs.AI, cs.LG, cs.CL (AI/ML 분야)
- **날짜 범위**: 어제 00:00부터 현재까지 (미국 동부시간 기준)
- **수집 데이터**: 제목, 저자, 제출일, 발표일, 주제, 초록, URL 정보

### 3. 저장 방식
- **ID_TABLE.csv**: 누적 저장 (모든 논문의 ID와 제목 기록)
- **1_URL_of_paper_abstractions.csv**: 덮어쓰기 저장 (새로 수집된 논문만)

## 실행 시나리오별 동작

### 시나리오 1: 모든 논문이 이미 ID_TABLE에 존재하는 경우
**상황**: 오늘 처음 실행했는데 모든 논문이 이미 ID_TABLE.csv에 등록되어 있음

**동작**:
```
새로운 논문: 0개
중복으로 스킵된 논문: 240개
모든 논문이 이미 ID 테이블에 존재합니다. 새로운 논문이 없습니다.
```

**결과**:
- ID_TABLE.csv: 변경 없음
- 1_URL_of_paper_abstractions.csv: 기존 파일 그대로 유지 (덮어쓰기 없음)
- 새로운 데이터 수집 없음

### 시나리오 2: ID_TABLE에 하나도 없는 논문들인 경우
**상황**: 완전히 새로운 논문들이 발견되어 ID_TABLE.csv에 전혀 없음

**동작**:
```
새로운 논문: 240개  
중복으로 스킵된 논문: 0개
ID 테이블 업데이트 완료: (총 240개 논문)
결과 파일 저장 완료 (덮어쓰기): 1_URL_of_paper_abstractions.csv
```

**결과**:
- ID_TABLE.csv: 240개 논문 새로 추가 (250830_1 ~ 250830_240)
- 1_URL_of_paper_abstractions.csv: 기존 파일을 새로운 240개 논문으로 완전 덮어쓰기
- 백업 파일 자동 생성

### 시나리오 3: ID_TABLE에 일부만 있는 경우
**상황**: 수집된 논문 중 일부는 ID_TABLE.csv에 있고, 일부는 새로운 논문

**동작**:
```
새로운 논문: 120개
중복으로 스킵된 논문: 120개  
ID 테이블 업데이트 완료: (총 360개 논문)
결과 파일 저장 완료 (덮어쓰기): 1_URL_of_paper_abstractions.csv
```

**결과**:
- ID_TABLE.csv: 120개 새 논문 추가 (250830_241 ~ 250830_360)
- 1_URL_of_paper_abstractions.csv: 기존 파일을 새로운 120개 논문으로 덮어쓰기
- 중복된 120개 논문은 처리하지 않음

## 주요 함수 설명

### 1. ID 관리 함수들
- `load_or_create_id_table()`: ID_TABLE.csv 로드 또는 생성
- `generate_paper_id(date_str, sequence_num)`: YYMMDD_순번 형식 ID 생성
- `get_next_sequence_number(id_table_df, date_str)`: 해당 날짜의 다음 순번 계산

### 2. 중복 검사 로직
```python
# 중복 검사: 논문 제목 기준
existing_titles = set(id_table_df['Paper_Title'].str.lower().str.strip())
for paper in papers_data:
    paper_title_clean = paper['Title'].lower().strip()
    if paper_title_clean not in existing_titles:
        new_papers.append(paper)  # 새로운 논문
    else:
        skipped_papers.append(paper)  # 중복 논문
```

### 3. 순차적 ID 생성 로직
```python
# 시작 순번을 한 번만 계산
start_sequence_num = get_next_sequence_number(id_table_df, current_date)

# 순차적으로 ID 생성
for i, paper in enumerate(new_papers):
    sequence_num = start_sequence_num + i  # 순차 증가
    paper_id = generate_paper_id(current_date, sequence_num)
```

## 백업 시스템

### 자동 백업 파일들
1. **ID_TABLE 백업**: `backup/ID_TABLE/ID_TABLE_YYMMDD.csv`
2. **메인 결과 백업**: `backup/1_URL_of_paper_abstractions/1_URL_of_paper_abstractions_YYYY-MM-DD HHMM.csv`

### 백업 타이밍
- ID_TABLE.csv 업데이트 후 즉시 백업
- 결과 파일 저장 후 즉시 백업

## 성능 최적화

### 요청 제한
- **20개 요청마다 10초 대기**: 서버 부하 방지
- **타임아웃 설정**: 30초 HTTP 타임아웃

### 처리 효율성
- **내부 중복 제거**: 같은 실행에서 수집된 논문 간 중복 제거
- **정렬**: arXiv URL 기준 내림차순 정렬

## 출력 예시

### 정상 실행 시
```
============================================================
Phase 1: arXiv 논문 URL 및 메타데이터 수집
============================================================
수집 기간: 2025-08-29 ~ 2025-08-30
대상 주제: cs.AI, cs.LG, cs.CL

수집 완료: 총 240개 논문
중복 제거: 76개
새로운 논문: 240개
중복으로 스킵된 논문: 0개
ID 테이블 업데이트 완료: results/ID_TABLE.csv (총 240개 논문)
ID 테이블 백업 완료: backup/ID_TABLE/ID_TABLE_250830.csv
결과 파일 저장 완료 (덮어쓰기): results/1_URL_of_paper_abstractions.csv
백업 파일 저장 완료: backup/1_URL_of_paper_abstractions/1_URL_of_paper_abstractions_2025-08-30 1504.csv
새로 수집된 논문 수: 240개
Phase 1 완료!
```

## 주의사항

1. **덮어쓰기 방식**: 1_URL_of_paper_abstractions.csv는 매번 새로 수집된 논문들로만 덮어쓰기
2. **ID 연속성**: ID_TABLE.csv를 삭제하면 ID 연속성이 깨짐
3. **날짜 변경**: 날짜가 바뀌면 ID 순번이 1부터 다시 시작
4. **제목 기반 중복 검사**: 논문 제목이 살짝 달라도 다른 논문으로 인식