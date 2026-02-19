# Dockerfile은 컨테이너 이미지를 만드는 레시피로, FROM으로 지정한 베이스 이미지 위에
# 의존성 설치와 코드 복사를 순서대로 적용해 실행 가능한 환경을 조립합니다.
# "빌드"는 이 레시피를 실행해 새 이미지를 만들어 두는 과정입니다.
#
# 빌드 실행 방법
# 1) Docker CLI 직접 사용:   docker build -t paper-pipeline:dev .
#    - 단일 이미지 생성에 집중할 때 사용하며, -t 옵션으로 이미지 이름(tag)을 지정합니다.
#      - docker  : Docker 명령줄 도구
#      - build   : Dockerfile을 읽어 이미지를 생성하라는 하위 명령
#      - -t      : 'tag' 옵션. 이미지 이름(예: paper-pipeline)과 태그(dev)를 지정
#      - .       : 현재 디렉터리를 빌드 컨텍스트로 사용 (Dockerfile과 소스 위치)
# 2) Docker Compose 사용:    docker compose up --build
#    - 여러 서비스(컨테이너)를 한꺼번에 다루는 설정 파일(docker-compose.yml)을 기준으로 필요 시 이미지도 빌드하고 컨테이너를 바로 실행합니다.
#    - docker compose build               : 모든 서비스를 한 번에 빌드만 수행 (컨테이너 미실행)
#    - docker compose up --build --no-start: 빌드 후 컨테이너 생성까지만 진행하고 실행은 나중에 별도로 up

# Dockerfile에서 설치해서 사용할 python 버전 정의
FROM python:3.11-slim

# 파이썬이 실행 속도 최적화를 위해 생성하는 .pyc 바이트코드 캐시 파일을 만들지 않고,
# stdout을 버퍼 없이 즉시 흘려보내도록 해서 컨테이너 로그를 실시간으로 확인
#    예: 버퍼링 상태에서 `python script.py > log.txt`로 실행하면 print 출력이 모였다가 나중에 기록되지만,
#        이 설정을 켜면 print 직후 log.txt에서도 바로 결과를 확인할 수 있음
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 도커 컨테이너 내에서 명령어를 실행하는 위치
WORKDIR /app

# 프로젝트가 의존하는 패키지 목록(requirements.txt)만 먼저 복사해서
# Docker 레이어 캐시를 활용할 수 있게 준비
COPY requirements.txt .

# 베이스 이미지(모듈러 Debian Slim) 빌드 단계에서 requirements.txt에 기록된 패키지를 설치
# -> 이미지를 한 번 빌드하면 해당 패키지들이 이미지 안에 포함되며, 이후 컨테이너 실행 시 재설치하지 않음
RUN pip install --no-cache-dir -r requirements.txt

# 이후 단계에서 소스 코드와 설정 등 프로젝트 파일 전체를 복사
COPY . .

# 도커 컨테이너를 실행하면 아래 명령어를 실행하라는 뜻.
CMD ["python", "src/integrated.py"]
