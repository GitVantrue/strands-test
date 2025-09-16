# Strands Agent Chatbot

AI 에이전트 기반 채팅봇으로, 로컬 커스텀 툴과 MCP(Model Context Protocol) 서버를 통합하여 다양한 기능을 제공합니다.

## 🌟 주요 기능

### 💬 대화형 채팅 인터페이스
- **Streamlit 기반 웹 UI**: 직관적이고 사용하기 쉬운 채팅 인터페이스
- **실시간 응답**: 사용자 입력에 대한 즉시 응답
- **채팅 기록**: 세션 동안 대화 내용 유지

### 🛠️ 다양한 툴 지원
- **로컬 커스텀 툴**: 날짜 조회, 수학 계산 등
- **MCP 통합**: Notion 등 외부 서비스 연동
- **지능형 툴 선택**: 사용자 요청에 맞는 최적의 툴 자동 선택

### 🔧 강력한 에러 처리
- **Graceful Degradation**: MCP 서버 연결 실패 시에도 로컬 툴로 계속 동작
- **자동 재시도**: 네트워크 오류 시 자동 재연결
- **상세한 로깅**: 문제 진단을 위한 포괄적인 로그 시스템

## 🚀 빠른 시작

### 1. 저장소 클론

```bash
git clone <repository-url>
cd strands-agent-chatbot
```

### 2. 의존성 설치

```bash
# Python 가상환경 생성 (권장)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 또는
venv\Scripts\activate     # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 3. 환경변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집하여 실제 API 키 입력
# SMITHERY_API_KEY=your_actual_api_key
# SMITHERY_PROFILE=your_actual_profile
```

자세한 환경변수 설정 방법은 [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md)를 참고하세요.

### 4. 애플리케이션 실행

#### 간편 실행 (권장)

```bash
# Linux/macOS
./run.sh

# Windows
run.bat
```

#### 직접 실행

```bash
streamlit run app.py
```

### 5. 웹 브라우저에서 접속

기본적으로 http://localhost:8501 에서 애플리케이션에 접속할 수 있습니다.

## 📁 프로젝트 구조

```
strands-agent-chatbot/
├── app.py                 # Streamlit 웹 애플리케이션
├── agent.py              # 핵심 에이전트 로직
├── tools.py              # 로컬 커스텀 툴 구현
├── requirements.txt      # Python 의존성
├── .env.example         # 환경변수 템플릿
├── run.sh               # Linux/macOS 실행 스크립트
├── run.bat              # Windows 실행 스크립트
├── README.md            # 이 파일
├── ENVIRONMENT_SETUP.md # 환경변수 설정 가이드
├── DEPLOYMENT.md        # 배포 가이드
└── tests/               # 테스트 파일들
    ├── test_core_functionality.py
    ├── test_performance_stability.py
    └── test_mcp_connection.py
```

## 🔧 사용 가능한 툴

### 로컬 툴
- **current_date**: 현재 날짜 조회
- **add**: 두 수의 덧셈
- **subtract**: 두 수의 뺄셈
- **multiply**: 두 수의 곱셈
- **divide**: 두 수의 나눗셈

### MCP 툴 (Notion 연동 시)
- **create_page**: Notion 페이지 생성
- **update_page**: Notion 페이지 업데이트
- **search_pages**: Notion 페이지 검색
- **get_page**: 특정 페이지 조회
- **list_databases**: 데이터베이스 목록 조회
- **query_database**: 데이터베이스 쿼리

## 💡 사용 예시

### 기본 기능
```
사용자: 오늘 날짜 알려줘
봇: 오늘 날짜는 2025-09-16입니다.

사용자: 15 + 25는 얼마야?
봇: 15 + 25 = 40입니다.
```

### 복합 기능
```
사용자: 오늘 날짜와 100 나누기 4 결과를 알려줘
봇: 오늘 날짜는 2025-09-16이고, 100 ÷ 4 = 25입니다.
```

## 🌐 AWS EC2 배포

### 사전 요구사항

- **AWS 계정** 및 EC2 인스턴스
- **Python 3.8+** 설치
- **Git** 설치
- **포트 8501** 보안 그룹에서 열기

### 배포 단계

#### 1. EC2 인스턴스 생성

```bash
# Amazon Linux 2 또는 Ubuntu 20.04+ 권장
# 인스턴스 타입: t2.micro 이상
# 보안 그룹: HTTP(80), HTTPS(443), Custom TCP(8501) 허용
```

#### 2. 서버 접속 및 환경 설정

```bash
# EC2 인스턴스 접속
ssh -i your-key.pem ec2-user@your-ec2-ip

# 시스템 업데이트
sudo yum update -y  # Amazon Linux
# 또는
sudo apt update && sudo apt upgrade -y  # Ubuntu

# Python 3 및 pip 설치
sudo yum install python3 python3-pip git -y  # Amazon Linux
# 또는
sudo apt install python3 python3-pip git -y  # Ubuntu
```

#### 3. 애플리케이션 배포

```bash
# 저장소 클론
git clone <repository-url>
cd strands-agent-chatbot

# 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
nano .env  # 필요한 API 키 설정
```

#### 4. 방화벽 설정

```bash
# Amazon Linux (firewalld)
sudo firewall-cmd --permanent --add-port=8501/tcp
sudo firewall-cmd --reload

# Ubuntu (ufw)
sudo ufw allow 8501/tcp
sudo ufw enable
```

#### 5. 애플리케이션 실행

```bash
# 백그라운드 실행
nohup ./run.sh > app.log 2>&1 &

# 또는 screen 사용
screen -S strands-agent
./run.sh
# Ctrl+A, D로 detach
```

#### 6. 서비스 등록 (선택사항)

systemd 서비스로 등록하여 자동 시작 설정:

```bash
# 서비스 파일 생성
sudo nano /etc/systemd/system/strands-agent.service
```

서비스 파일 내용:
```ini
[Unit]
Description=Strands Agent Chatbot
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/strands-agent-chatbot
Environment=PATH=/home/ec2-user/strands-agent-chatbot/venv/bin
ExecStart=/home/ec2-user/strands-agent-chatbot/venv/bin/streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
Restart=always

[Install]
WantedBy=multi-user.target
```

서비스 활성화:
```bash
sudo systemctl daemon-reload
sudo systemctl enable strands-agent
sudo systemctl start strands-agent
sudo systemctl status strands-agent
```

### 7. 접속 확인

웹 브라우저에서 `http://your-ec2-public-ip:8501`로 접속하여 애플리케이션이 정상 동작하는지 확인합니다.

## 🧪 테스트

### 단위 테스트 실행

```bash
# 핵심 기능 테스트
python3 test_core_functionality.py

# 성능 및 안정성 테스트
python3 test_performance_stability.py

# MCP 연결 테스트
python3 test_mcp_connection.py
```

### 통합 테스트 실행

```bash
# 모든 테스트 실행
python3 run_integration_tests.py
```

## 🔍 모니터링 및 로깅

### 로그 확인

```bash
# 애플리케이션 로그 (백그라운드 실행 시)
tail -f app.log

# systemd 서비스 로그
sudo journalctl -u strands-agent -f
```

### 로그 레벨 설정

`.env` 파일에서 로그 레벨을 조정할 수 있습니다:

```bash
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

## 🛠️ 개발 및 커스터마이징

### 새로운 로컬 툴 추가

1. `tools.py`에 새 함수 추가
2. `agent.py`의 `_register_local_tools()` 메서드에 툴 등록
3. 테스트 코드 작성

### MCP 서버 추가

1. 새 MCP 서버 설정을 `agent.py`에 추가
2. 환경변수 설정 업데이트
3. 연결 테스트 코드 작성

## 🚨 문제 해결

### 일반적인 문제들

1. **포트 8501이 이미 사용 중**
   ```bash
   # 다른 포트 사용
   export STREAMLIT_SERVER_PORT=8502
   ./run.sh
   ```

2. **MCP 서버 연결 실패**
   - 환경변수 설정 확인
   - 네트워크 연결 상태 확인
   - API 키 유효성 확인

3. **의존성 설치 오류**
   ```bash
   # pip 업그레이드
   pip install --upgrade pip
   
   # 캐시 클리어
   pip cache purge
   ```

### 로그 분석

상세한 로그를 위해 DEBUG 레벨로 설정:

```bash
export LOG_LEVEL=DEBUG
./run.sh
```

## 📚 추가 문서

- [환경변수 설정 가이드](ENVIRONMENT_SETUP.md)
- [배포 가이드](DEPLOYMENT.md)
- [API 문서](docs/API.md)

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 지원

문제가 발생하거나 질문이 있으시면:

- **Issues**: GitHub Issues 페이지에서 문제 보고
- **Documentation**: 프로젝트 문서 참고
- **Community**: 커뮤니티 포럼에서 도움 요청

---

**Happy Coding! 🚀**# strands-test
