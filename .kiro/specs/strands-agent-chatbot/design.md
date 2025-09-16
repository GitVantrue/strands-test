# 설계 문서

## 개요

Strands Agent를 활용한 Streamlit 챗봇 애플리케이션으로, Smithery Notion MCP 서버와 로컬 커스텀 툴을 통합하여 에이전트의 툴 선택 및 통합 능력을 테스트합니다. 간단한 3개 파일 구조로 구현하여 수동 배포가 용이하도록 설계합니다.

## 아키텍처

### 전체 시스템 아키텍처
```
[사용자] 
    ↓
[Streamlit UI (app.py)]
    ↓
[Strands Agent (agent.py)]
    ├─→ [Smithery MCP 서버] → [Notion 기능]
    └─→ [로컬 툴 (tools.py)] → [날짜/계산기 기능]
    ↓
[통합된 응답] → [Streamlit UI 출력]
```

### 파일 구조
```
strands-agent-chatbot/
├── app.py              # Streamlit 메인 애플리케이션
├── agent.py            # Strands Agent 설정 및 관리
├── tools.py            # 로컬 커스텀 툴 구현
├── requirements.txt    # Python 패키지 의존성
└── .env.example       # 환경변수 예시 파일
```

## 컴포넌트 및 인터페이스

### 1. app.py (Streamlit UI)
**역할**: 사용자 인터페이스 및 메인 애플리케이션 로직

**주요 기능**:
- Streamlit 채팅 인터페이스 구현
- 사용자 입력 처리 및 세션 상태 관리
- 에이전트 호출 및 응답 표시
- 로딩 상태 및 오류 처리

**인터페이스**:
```python
def main():
    # Streamlit 페이지 설정
    # 채팅 인터페이스 초기화
    # 사용자 입력 처리
    # 에이전트 응답 표시

def process_user_input(user_message: str) -> str:
    # 에이전트에 메시지 전달
    # 응답 받아서 반환
```

### 2. agent.py (Strands Agent 관리)
**역할**: Strands Agent 초기화 및 툴 통합 관리

**주요 기능**:
- Strands Agent 인스턴스 생성 및 설정
- Smithery MCP 서버 연결 관리
- 로컬 커스텀 툴 등록
- 툴 호출 로깅 및 모니터링

**인터페이스**:
```python
class StrandsAgentManager:
    def __init__(self):
        # 에이전트 초기화
        # MCP 서버 연결
        # 로컬 툴 등록
    
    async def process_message(self, message: str) -> str:
        # 메시지 처리 및 툴 호출
        # 결과 통합 및 반환
    
    def setup_mcp_connection(self):
        # Smithery MCP 서버 연결 설정
    
    def register_local_tools(self):
        # 로컬 커스텀 툴 등록
```

### 3. tools.py (로컬 커스텀 툴)
**역할**: 로컬에서 실행되는 커스텀 함수들 구현

**주요 기능**:
- 날짜 관련 함수
- 수학 계산 함수
- 에러 처리 및 검증

**인터페이스**:
```python
def current_date() -> str:
    # 현재 날짜 반환

def add(a: float, b: float) -> float:
    # 덧셈 연산

def subtract(a: float, b: float) -> float:
    # 뺄셈 연산

def multiply(a: float, b: float) -> float:
    # 곱셈 연산

def divide(a: float, b: float) -> float:
    # 나눗셈 연산 (0으로 나누기 예외 처리)
```

## 데이터 모델

### 메시지 구조
```python
@dataclass
class ChatMessage:
    role: str  # "user" 또는 "assistant"
    content: str
    timestamp: datetime
    tool_calls: Optional[List[str]] = None  # 사용된 툴 목록
```

### 툴 실행 로그
```python
@dataclass
class ToolExecutionLog:
    tool_name: str
    tool_type: str  # "mcp" 또는 "local"
    parameters: Dict[str, Any]
    execution_time: float
    result: Any
    timestamp: datetime
```

## 에러 처리

### MCP 서버 연결 오류
- 연결 실패 시 재시도 로직 (최대 3회)
- 타임아웃 설정 (30초)
- 연결 실패 시 로컬 툴만 사용하도록 fallback

### 로컬 툴 오류
- 수학 연산 시 0으로 나누기 예외 처리
- 잘못된 매개변수 타입 검증
- 함수 실행 실패 시 명확한 오류 메시지 반환

### Streamlit UI 오류
- 세션 상태 초기화 실패 처리
- 에이전트 응답 지연 시 타임아웃 처리
- 네트워크 오류 시 사용자 친화적 메시지 표시

## 테스트 전략

### 단위 테스트
- 각 로컬 툴 함수의 정확성 검증
- 에러 케이스 처리 검증
- MCP 연결 로직 테스트

### 통합 테스트
- Strands Agent와 툴 간의 통합 테스트
- MCP 서버 연결 및 응답 테스트
- 전체 워크플로우 테스트

### 사용자 시나리오 테스트
1. **단일 툴 사용**: "오늘 날짜 알려줘"
2. **계산 기능**: "15 + 25는 얼마야?"
3. **MCP 기능**: "내 노션에서 XXX 찾아줘"
4. **복합 기능**: "노션에 오늘 날짜로 메모 추가하고 2+3도 계산해줘"

### 성능 테스트
- 로컬 툴 응답 시간 (1초 이내)
- MCP 서버 응답 시간 측정
- 동시 요청 처리 능력 확인

## 배포 고려사항

### EC2 환경 설정
- Python 3.8+ 설치
- 필요한 패키지 설치 (`pip install -r requirements.txt`)
- 환경변수 설정 (SMITHERY_API_KEY)
- 보안 그룹에서 8501 포트 열기

### 실행 방법
```bash
# 환경변수 설정
export SMITHERY_API_KEY="your_api_key_here"

# 애플리케이션 실행
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

### 모니터링
- 애플리케이션 로그 파일 생성
- 툴 사용 통계 수집
- 에러 발생 빈도 추적

## 보안 고려사항

### API 키 관리
- 환경변수를 통한 API 키 관리
- .env 파일을 .gitignore에 추가
- 프로덕션 환경에서 키 로테이션 고려

### 입력 검증
- 사용자 입력 sanitization
- SQL injection 방지 (해당 시 없음)
- XSS 공격 방지

### 네트워크 보안
- HTTPS 사용 권장
- 적절한 CORS 설정
- 레이트 리미팅 고려