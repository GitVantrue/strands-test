# 환경변수 설정 가이드

이 문서는 Strands Agent Chatbot을 실행하기 위한 환경변수 설정 방법을 설명합니다.

## 📋 필수 환경변수

### 1. Notion API 키 (선택사항)

Notion 연동 기능을 사용하려면 Notion API 키가 필요합니다.

```bash
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### Notion API 키 발급 방법:

1. **Notion 계정 로그인**: https://www.notion.so
2. **Integration 생성**: https://www.notion.so/my-integrations
3. **새 Integration 만들기**:
   - "New integration" 클릭
   - 이름 입력 (예: "Strands Agent")
   - Workspace 선택
   - "Submit" 클릭
4. **API 키 복사**: "Internal Integration Token" 복사
5. **페이지 권한 부여**: 사용할 Notion 페이지에서 Integration 권한 추가

### 2. Smithery API 키 (선택사항)

Smithery 호스팅 MCP 서버를 사용하려면 Smithery API 키가 필요합니다.

```bash
SMITHERY_API_KEY=your_smithery_api_key_here
```

#### Smithery API 키 발급 방법:

1. **Smithery 계정 생성**: https://smithery.ai
2. **API 키 발급**: 대시보드에서 API 키 생성
3. **키 복사**: 생성된 API 키 복사

## 🔧 선택적 환경변수

### 애플리케이션 설정

```bash
# 로깅 레벨 (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Streamlit 서버 포트 (기본값: 8501)
STREAMLIT_SERVER_PORT=8501

# Streamlit 서버 주소 (기본값: 0.0.0.0)
STREAMLIT_SERVER_ADDRESS=0.0.0.0

# MCP 서버 연결 타임아웃 (초, 기본값: 30)
MCP_CONNECTION_TIMEOUT=30

# 툴 실행 타임아웃 (초, 기본값: 10)
TOOL_EXECUTION_TIMEOUT=10
```

## 📁 환경변수 파일 설정

### 1. .env 파일 생성

프로젝트 루트 디렉토리에 `.env` 파일을 생성합니다:

```bash
# .env.example 파일을 복사하여 시작
cp .env.example .env
```

### 2. .env 파일 편집

텍스트 에디터로 `.env` 파일을 열고 실제 값으로 수정합니다:

```bash
# 예시
NOTION_API_KEY=secret_abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
LOG_LEVEL=INFO
STREAMLIT_SERVER_PORT=8501
```

## 🖥️ 운영체제별 설정

### Linux/macOS

```bash
# 터미널에서 직접 설정
export NOTION_API_KEY="your_api_key_here"
export LOG_LEVEL="INFO"

# 또는 .bashrc/.zshrc에 추가
echo 'export NOTION_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

### Windows

```cmd
# 명령 프롬프트에서 설정
set NOTION_API_KEY=your_api_key_here
set LOG_LEVEL=INFO

# 또는 시스템 환경변수에서 설정
# 제어판 > 시스템 > 고급 시스템 설정 > 환경변수
```

### PowerShell

```powershell
# PowerShell에서 설정
$env:NOTION_API_KEY="your_api_key_here"
$env:LOG_LEVEL="INFO"
```

## 🔒 보안 주의사항

### 1. API 키 보안

- **절대로 API 키를 코드에 하드코딩하지 마세요**
- **Git에 .env 파일을 커밋하지 마세요** (.gitignore에 추가됨)
- **API 키를 공개 저장소에 업로드하지 마세요**

### 2. 권한 관리

- **최소 권한 원칙**: 필요한 권한만 부여
- **정기적인 키 갱신**: API 키를 주기적으로 갱신
- **사용하지 않는 키 삭제**: 더 이상 사용하지 않는 API 키는 즉시 삭제

## 🧪 환경변수 테스트

환경변수가 올바르게 설정되었는지 확인하는 방법:

### Python에서 확인

```python
import os
from dotenv import load_dotenv

load_dotenv()

# API 키 확인 (보안상 일부만 표시)
notion_key = os.getenv('NOTION_API_KEY')
if notion_key:
    print(f"✅ NOTION_API_KEY 설정됨: {notion_key[:10]}...")
else:
    print("❌ NOTION_API_KEY 설정되지 않음")

# 로그 레벨 확인
log_level = os.getenv('LOG_LEVEL', 'INFO')
print(f"📊 LOG_LEVEL: {log_level}")
```

### 터미널에서 확인

```bash
# Linux/macOS
echo $NOTION_API_KEY
echo $LOG_LEVEL

# Windows CMD
echo %NOTION_API_KEY%
echo %LOG_LEVEL%

# Windows PowerShell
echo $env:NOTION_API_KEY
echo $env:LOG_LEVEL
```

## 🚨 문제 해결

### 일반적인 문제들

1. **"환경변수를 찾을 수 없음" 오류**
   - `.env` 파일이 프로젝트 루트에 있는지 확인
   - 파일 이름이 정확한지 확인 (`.env`, `.env.txt` 아님)
   - 환경변수 이름의 대소문자 확인

2. **"API 키가 유효하지 않음" 오류**
   - API 키가 올바르게 복사되었는지 확인
   - 키에 공백이나 특수문자가 포함되지 않았는지 확인
   - API 키가 만료되지 않았는지 확인

3. **"권한 거부" 오류**
   - Notion에서 Integration 권한이 올바르게 설정되었는지 확인
   - 사용하려는 페이지에 Integration이 추가되었는지 확인

### 도움말

문제가 지속되면 다음을 확인해보세요:

1. **로그 확인**: `LOG_LEVEL=DEBUG`로 설정하여 상세 로그 확인
2. **테스트 스크립트 실행**: `python3 test_mcp_connection.py`
3. **의존성 확인**: `pip list | grep mcp`

## 📞 지원

추가 도움이 필요하면:

- **Notion API 문서**: https://developers.notion.com/
- **Smithery 문서**: https://smithery.ai/docs
- **MCP 문서**: https://modelcontextprotocol.io/