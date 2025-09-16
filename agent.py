"""
Strands Agent 관리 클래스
Smithery MCP 서버와 로컬 커스텀 툴을 통합하는 에이전트를 관리합니다.
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

import structlog
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 환경변수 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv가 설치되지 않은 경우 무시
    pass

# 로컬 툴 임포트
from tools import current_date, add, subtract, multiply, divide


@dataclass
class ToolExecutionLog:
    """툴 실행 로그를 위한 데이터 클래스"""
    tool_name: str
    tool_type: str  # "mcp" 또는 "local"
    parameters: Dict[str, Any]
    execution_time: float
    result: Any
    timestamp: datetime


class StrandsAgentManager:
    """
    Strands Agent를 관리하고 MCP 서버 및 로컬 툴과의 통합을 처리하는 클래스
    """
    
    def __init__(self):
        """
        StrandsAgentManager 초기화
        - 로깅 설정
        - MCP 클라이언트 초기화
        - 로컬 툴 등록
        """
        # 로깅 설정
        self.logger = structlog.get_logger(__name__)
        self._setup_logging()
        
        # MCP 관련 속성
        self.mcp_client: Optional[ClientSession] = None
        self.mcp_connected: bool = False
        self.mcp_connection_error: Optional[str] = None
        self.mcp_last_error_time: Optional[datetime] = None
        
        # 로컬 툴 등록
        self.local_tools: Dict[str, callable] = {}
        self._register_local_tools()
        
        # 실행 로그
        self.execution_logs: List[ToolExecutionLog] = []
        
        # 에러 처리 설정
        self.max_consecutive_errors = 5
        self.consecutive_error_count = 0
        self.circuit_breaker_open = False
        self.circuit_breaker_reset_time: Optional[datetime] = None
        
        self.logger.info("StrandsAgentManager 초기화 완료")
    
    def _setup_logging(self) -> None:
        """로깅 시스템 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # structlog 설정
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    def _register_local_tools(self) -> None:
        """로컬 커스텀 툴들을 등록 (Strands Agent 스타일)"""
        from tools import get_all_tools
        
        # 데코레이터로 등록된 툴들 가져오기
        all_tools = get_all_tools()
        self.local_tools = {name: info['function'] for name, info in all_tools.items()}
        
        self.logger.info(
            "로컬 툴 등록 완료",
            tool_count=len(self.local_tools),
            tools=list(self.local_tools.keys())
        )
    
    async def initialize(self) -> None:
        """
        에이전트 초기화 - MCP 서버 연결 시도
        """
        self.logger.info("에이전트 초기화 시작")
        
        try:
            await self._setup_mcp_connection()
            self.logger.info("에이전트 초기화 완료", mcp_connected=self.mcp_connected)
        except Exception as e:
            self.logger.error("에이전트 초기화 중 오류 발생", error=str(e))
            # MCP 연결 실패해도 로컬 툴은 사용 가능하므로 계속 진행
    
    async def _setup_mcp_connection(self) -> None:
        """
        Smithery MCP 서버 연결 설정 (HTTP)
        API 키를 통한 인증 및 연결 실패 시 재시도 로직 포함
        향상된 에러 처리 및 graceful degradation 지원
        """
        # Smithery 설정 (직접 입력)
        api_key = os.getenv('SMITHERY_API_KEY', '20f09ddc-b65d-448c-9c3b-4199c5cc7892')
        profile = os.getenv('SMITHERY_PROFILE', 'profitable-cicada-SuKab9')
        
        if not api_key or not profile:
            self.logger.warning("Smithery API 키 또는 프로필이 설정되지 않음 - MCP 서버 연결 건너뜀")
            self.mcp_connection_error = "Smithery API 키 또는 프로필이 설정되지 않았습니다"
            return
        
        max_retries = 3
        retry_delay = 2  # 초
        connection_timeout = 30  # 연결 타임아웃
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"MCP 서버 연결 시도 {attempt + 1}/{max_retries}")
                
                # Smithery HTTP MCP 서버 연결 설정
                from mcp.client.streamable_http import streamablehttp_client
                from urllib.parse import urlencode
                
                base_url = "https://server.smithery.ai/@smithery/notion/mcp"
                params = {"api_key": api_key, "profile": profile}
                url = f"{base_url}?{urlencode(params)}"
                
                self.logger.info(f"Smithery MCP 서버 연결 중: {base_url}")
                
                # HTTP 클라이언트로 연결 시도 (타임아웃 설정)
                async with streamablehttp_client(url) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        # 연결 테스트
                        await asyncio.wait_for(
                            self._test_mcp_connection(session), 
                            timeout=connection_timeout
                        )
                        
                        # 툴 목록 가져와서 저장
                        tools_result = await session.list_tools()
                        tools = tools_result.tools if hasattr(tools_result, 'tools') else []
                        
                        # MCP 툴 등록
                        for tool in tools:
                            self.mcp_tools[tool.name] = {
                                'name': tool.name,
                                'description': tool.description,
                                'schema': tool.inputSchema
                            }
                        
                        self.mcp_connected = True
                        self.mcp_connection_error = None
                        
                        self.logger.info(f"Smithery MCP 서버 연결 성공 - {len(tools)}개 툴 사용 가능")
                        return
                        
            except asyncio.TimeoutError:
                error_msg = f"MCP 서버 연결 타임아웃 ({connection_timeout}초)"
                self.logger.warning(f"{error_msg} (시도 {attempt + 1}/{max_retries})")
                self.mcp_connection_error = error_msg
                
            except ConnectionError as e:
                error_msg = f"MCP 서버 연결 실패: {str(e)}"
                self.logger.warning(f"{error_msg} (시도 {attempt + 1}/{max_retries})")
                self.mcp_connection_error = error_msg
                
            except FileNotFoundError:
                error_msg = "MCP 서버 실행 파일을 찾을 수 없습니다"
                self.logger.error(f"{error_msg} - smithery-mcp-server가 설치되어 있는지 확인하세요")
                self.mcp_connection_error = error_msg
                break  # 파일이 없으면 재시도해도 의미 없음
                
            except PermissionError:
                error_msg = "MCP 서버 실행 권한이 없습니다"
                self.logger.error(error_msg)
                self.mcp_connection_error = error_msg
                break  # 권한 문제는 재시도해도 의미 없음
                
            except Exception as e:
                error_msg = f"예상치 못한 MCP 연결 오류: {str(e)}"
                self.logger.warning(f"{error_msg} (시도 {attempt + 1}/{max_retries})")
                self.mcp_connection_error = error_msg
            
            # 마지막 시도가 아니면 재시도 대기
            if attempt < max_retries - 1:
                self.logger.info(f"{retry_delay}초 후 재시도...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)  # 지수 백오프 (최대 30초)
        
        # 모든 재시도 실패
        self.logger.error("MCP 서버 연결 최종 실패 - 로컬 툴만 사용 가능")
        self.mcp_connected = False
        if not hasattr(self, 'mcp_connection_error') or not self.mcp_connection_error:
            self.mcp_connection_error = "모든 연결 시도가 실패했습니다"
    
    async def _test_mcp_connection(self, session: ClientSession) -> None:
        """
        MCP 연결 테스트
        
        Args:
            session: MCP 클라이언트 세션
        """
        try:
            # 서버 정보 요청으로 연결 테스트
            server_info = await session.initialize()
            self.logger.info("MCP 서버 정보 수신", server_info=server_info)
            
            # 사용 가능한 툴 목록 요청
            tools_result = await session.list_tools()
            tools = tools_result.tools if hasattr(tools_result, 'tools') else []
            self.logger.info("MCP 툴 목록 수신", tool_count=len(tools))
            
        except Exception as e:
            self.logger.error("MCP 연결 테스트 실패", error=str(e))
            raise
    
    def _log_tool_execution(self, tool_name: str, tool_type: str, 
                           parameters: Dict[str, Any], execution_time: float, 
                           result: Any, success: bool = True, error: str = None,
                           selection_reason: str = None) -> None:
        """
        툴 실행 로그 기록 (향상된 버전)
        
        Args:
            tool_name: 툴 이름
            tool_type: 툴 타입 ("local" 또는 "mcp")
            parameters: 툴 매개변수
            execution_time: 실행 시간 (초)
            result: 실행 결과
            success: 실행 성공 여부
            error: 에러 메시지 (실패 시)
            selection_reason: 툴 선택 이유
        """
        log_entry = ToolExecutionLog(
            tool_name=tool_name,
            tool_type=tool_type,
            parameters=parameters,
            execution_time=execution_time,
            result=result,
            timestamp=datetime.now()
        )
        
        self.execution_logs.append(log_entry)
        
        # 상세 로깅
        log_data = {
            "tool_name": tool_name,
            "tool_type": tool_type,
            "execution_time": execution_time,
            "parameters": parameters,
            "success": success,
            "result_type": type(result).__name__,
            "result_size": len(str(result)) if result is not None else 0,
            "selection_reason": selection_reason
        }
        
        if error:
            log_data["error"] = error
            log_data["error_type"] = type(error).__name__ if isinstance(error, Exception) else "string"
        
        if success:
            self.logger.info("툴 실행 성공", **log_data)
        else:
            self.logger.error("툴 실행 실패", **log_data)
        
        # 성능 모니터링 로깅
        if execution_time > 1.0:  # 1초 이상 걸린 경우
            self.logger.warning("툴 실행 시간 초과", 
                              tool_name=tool_name,
                              execution_time=execution_time,
                              threshold=1.0)
        
        # 결과 크기 모니터링
        result_size = len(str(result)) if result is not None else 0
        if result_size > 10000:  # 10KB 이상인 경우
            self.logger.warning("툴 결과 크기 초과",
                              tool_name=tool_name,
                              result_size=result_size,
                              threshold=10000)
    
    async def process_message(self, message: str) -> str:
        """
        사용자 메시지를 처리하고 적절한 툴을 선택하여 실행 (향상된 에러 처리)
        
        Args:
            message: 사용자 입력 메시지
            
        Returns:
            str: 처리된 응답 메시지
        """
        self.logger.info("메시지 처리 시작", message=message)
        
        try:
            # 입력 검증
            if not message or not message.strip():
                return "메시지를 입력해주세요."
            
            # 메시지 길이 제한 (DoS 방지)
            if len(message) > 10000:
                return "메시지가 너무 깁니다. 10,000자 이하로 입력해주세요."
            
            # 메시지 분석 및 툴 선택
            selected_tools = await self._analyze_message_and_select_tools(message)
            
            # 툴 선택 과정 로깅
            self.log_tool_selection_reasoning(message, selected_tools)
            
            if not selected_tools:
                self.logger.warning("적절한 툴을 찾지 못함", message=message)
                fallback_response = self._generate_fallback_response(message)
                return fallback_response
            
            # 선택된 툴들 실행 (에러 처리 포함)
            results = await self._execute_selected_tools_safely(selected_tools)
            
            # 모든 툴이 실패한 경우 처리
            if not any(r['success'] for r in results):
                self.logger.warning("모든 툴 실행 실패", message=message)
                return self._generate_error_response(results)
            
            # 결과 통합 및 응답 생성
            response = await self._integrate_tool_results(message, selected_tools, results)
            
            # 결과 통합 과정 로깅
            self.log_result_integration_process(results, response)
            
            self.logger.info("메시지 처리 완료", 
                           tools_used=len(selected_tools),
                           successful_tools=len([r for r in results if r['success']]),
                           failed_tools=len([r for r in results if not r['success']]),
                           response_length=len(response))
            
            return response
            
        except asyncio.TimeoutError:
            error_msg = "요청 처리 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
            self.logger.error("메시지 처리 타임아웃", message=message)
            return error_msg
            
        except MemoryError:
            error_msg = "메모리 부족으로 요청을 처리할 수 없습니다. 더 간단한 요청을 시도해주세요."
            self.logger.error("메모리 부족 에러", message=message)
            return error_msg
            
        except Exception as e:
            error_msg = self._generate_graceful_error_message(e)
            self.logger.error("메시지 처리 실패", 
                            error=str(e), 
                            error_type=type(e).__name__,
                            message=message)
            return error_msg
    
    def _generate_fallback_response(self, message: str) -> str:
        """
        툴을 찾지 못했을 때의 대체 응답 생성
        
        Args:
            message: 원본 메시지
            
        Returns:
            str: 대체 응답
        """
        # MCP 연결 상태에 따른 안내
        if not self.mcp_connected and self.mcp_connection_error:
            return (f"죄송합니다. 현재 일부 기능이 제한되어 있습니다.\n"
                   f"사용 가능한 기능: 날짜 조회, 수학 계산\n"
                   f"예시: '오늘 날짜 알려줘', '15 + 25는 얼마야?'")
        
        return ("죄송합니다. 요청을 처리할 수 있는 적절한 기능을 찾지 못했습니다.\n"
               "사용 가능한 기능:\n"
               "• 날짜 조회: '오늘 날짜 알려줘'\n"
               "• 수학 계산: '15 + 25는 얼마야?'")
    
    def _generate_error_response(self, results: List[Dict[str, Any]]) -> str:
        """
        모든 툴이 실패했을 때의 에러 응답 생성
        
        Args:
            results: 툴 실행 결과들
            
        Returns:
            str: 에러 응답
        """
        error_types = set()
        for result in results:
            if 'error' in result:
                error_types.add(type(result.get('error', '')).__name__)
        
        if 'ZeroDivisionError' in error_types:
            return "계산 오류: 0으로 나눌 수 없습니다."
        elif 'TypeError' in error_types:
            return "입력 오류: 올바른 숫자를 입력해주세요."
        elif 'TimeoutError' in error_types:
            return "처리 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
        else:
            return "요청 처리 중 오류가 발생했습니다. 다른 방식으로 시도해보세요."
    
    def _generate_graceful_error_message(self, error: Exception) -> str:
        """
        예외에 따른 사용자 친화적 에러 메시지 생성
        
        Args:
            error: 발생한 예외
            
        Returns:
            str: 사용자 친화적 에러 메시지
        """
        error_type = type(error).__name__
        
        if error_type == 'ConnectionError':
            return "네트워크 연결에 문제가 있습니다. 잠시 후 다시 시도해주세요."
        elif error_type == 'TimeoutError':
            return "요청 처리 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
        elif error_type == 'MemoryError':
            return "메모리 부족으로 요청을 처리할 수 없습니다. 더 간단한 요청을 시도해주세요."
        elif error_type == 'PermissionError':
            return "권한 문제로 요청을 처리할 수 없습니다."
        elif 'JSON' in error_type or 'Parse' in error_type:
            return "데이터 처리 중 오류가 발생했습니다. 다시 시도해주세요."
        else:
            return f"일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
    
    async def _execute_selected_tools_safely(self, selected_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        선택된 툴들을 안전하게 실행 (향상된 에러 처리)
        
        Args:
            selected_tools: 실행할 툴들의 정보
            
        Returns:
            List[Dict[str, Any]]: 실행 결과들
        """
        results = []
        
        for tool_info in selected_tools:
            tool_name = tool_info['name']
            tool_type = tool_info['type']
            parameters = tool_info['parameters']
            reason = tool_info['reason']
            
            try:
                self.logger.info(f"툴 실행 시작: {tool_name}", 
                               tool_type=tool_type,
                               parameters=parameters,
                               reason=reason)
                
                # 툴 타입별 실행
                if tool_type == 'local':
                    # 로컬 툴 실행 (타임아웃 적용)
                    result = await asyncio.wait_for(
                        self.execute_local_tool(tool_name, selection_reason=reason, **parameters),
                        timeout=10.0  # 로컬 툴 타임아웃 10초
                    )
                elif tool_type == 'mcp':
                    # MCP 툴 안전 실행
                    result = await self.safe_mcp_operation(
                        self._execute_mcp_tool, tool_name, parameters
                    )
                    if result is None:
                        raise Exception("MCP 서버를 사용할 수 없습니다")
                else:
                    raise ValueError(f"알 수 없는 툴 타입: {tool_type}")
                
                results.append({
                    'tool_name': tool_name,
                    'tool_type': tool_type,
                    'parameters': parameters,
                    'result': result,
                    'success': True,
                    'reason': reason
                })
                
            except asyncio.TimeoutError:
                error_msg = f"툴 실행 시간 초과: {tool_name}"
                self.logger.error(error_msg, tool_name=tool_name, timeout=10.0)
                
                results.append({
                    'tool_name': tool_name,
                    'tool_type': tool_type,
                    'parameters': parameters,
                    'result': error_msg,
                    'success': False,
                    'reason': reason,
                    'error': 'TimeoutError'
                })
                
            except Exception as e:
                error_msg = f"툴 실행 실패: {str(e)}"
                self.logger.error(f"툴 실행 오류: {tool_name}", 
                                error=str(e),
                                error_type=type(e).__name__,
                                tool_type=tool_type,
                                parameters=parameters)
                
                results.append({
                    'tool_name': tool_name,
                    'tool_type': tool_type,
                    'parameters': parameters,
                    'result': error_msg,
                    'success': False,
                    'reason': reason,
                    'error': str(e)
                })
        
        return results
    
    async def _execute_mcp_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        MCP 툴 실행 (향후 구현)
        
        Args:
            tool_name: MCP 툴 이름
            parameters: 툴 매개변수
            
        Returns:
            Any: 툴 실행 결과
        """
        # TODO: 실제 MCP 툴 실행 로직 구현
        raise NotImplementedError("MCP 툴 실행은 향후 구현 예정")
    
    def get_available_tools(self) -> Dict[str, Any]:
        """사용 가능한 툴 목록 반환"""
        return {
            "local_tools": {
                "count": len(self.local_tools),
                "tools": list(self.local_tools.keys()),
                "details": self.get_all_local_tools_info()
            },
            "mcp_tools": {
                "count": 0,
                "tools": [],  # TODO: MCP 연결 후 업데이트
                "connected": self.mcp_connected
            },
            "total_tools": len(self.local_tools)
        }
    
    def get_execution_logs(self) -> List[ToolExecutionLog]:
        """실행 로그 반환"""
        return self.execution_logs.copy()
    
    def clear_logs(self) -> None:
        """실행 로그 초기화"""
        self.execution_logs.clear()
        self.logger.info("실행 로그 초기화 완료")
    
    async def reconnect_mcp(self) -> bool:
        """
        MCP 서버 재연결 시도
        
        Returns:
            bool: 재연결 성공 여부
        """
        self.logger.info("MCP 서버 재연결 시도")
        self.mcp_connected = False
        self.mcp_client = None
        
        try:
            await self._setup_mcp_connection()
            return self.mcp_connected
        except Exception as e:
            self.logger.error("MCP 서버 재연결 실패", error=str(e))
            return False
    
    def is_mcp_available(self) -> bool:
        """MCP 서버 사용 가능 여부 확인"""
        return self.mcp_connected and self.mcp_client is not None
    
    async def handle_mcp_error(self, error: Exception) -> None:
        """
        MCP 관련 에러 처리 (향상된 버전)
        
        Args:
            error: 발생한 에러
        """
        self.logger.error("MCP 에러 발생", error=str(error), error_type=type(error).__name__)
        
        # 에러 카운트 증가
        self.consecutive_error_count += 1
        self.mcp_last_error_time = datetime.now()
        
        # Circuit Breaker 패턴 적용
        if self.consecutive_error_count >= self.max_consecutive_errors:
            self.circuit_breaker_open = True
            self.circuit_breaker_reset_time = datetime.now()
            self.logger.warning(
                "MCP Circuit Breaker 활성화 - 일시적으로 MCP 사용 중단",
                consecutive_errors=self.consecutive_error_count
            )
        
        # 연결 관련 에러인 경우 재연결 시도 (Circuit Breaker가 열리지 않은 경우만)
        if not self.circuit_breaker_open and isinstance(error, (ConnectionError, asyncio.TimeoutError)):
            self.logger.info("연결 에러로 인한 MCP 재연결 시도")
            success = await self.reconnect_mcp()
            if success:
                self.consecutive_error_count = 0  # 성공 시 에러 카운트 리셋
        
        # MCP 연결 상태 업데이트
        self.mcp_connected = False
        self.mcp_connection_error = str(error)
    
    def reset_circuit_breaker(self) -> bool:
        """
        Circuit Breaker 리셋 시도
        
        Returns:
            bool: 리셋 성공 여부
        """
        if not self.circuit_breaker_open:
            return True
        
        # 5분 후 자동 리셋 시도
        if (self.circuit_breaker_reset_time and 
            (datetime.now() - self.circuit_breaker_reset_time).total_seconds() > 300):
            
            self.circuit_breaker_open = False
            self.consecutive_error_count = 0
            self.circuit_breaker_reset_time = None
            
            self.logger.info("MCP Circuit Breaker 자동 리셋")
            return True
        
        return False
    
    def get_mcp_status(self) -> Dict[str, Any]:
        """
        MCP 연결 상태 정보 반환
        
        Returns:
            Dict[str, Any]: MCP 상태 정보
        """
        return {
            "connected": self.mcp_connected,
            "connection_error": self.mcp_connection_error,
            "last_error_time": self.mcp_last_error_time,
            "consecutive_errors": self.consecutive_error_count,
            "circuit_breaker_open": self.circuit_breaker_open,
            "circuit_breaker_reset_time": self.circuit_breaker_reset_time
        }
    
    async def safe_mcp_operation(self, operation_func, *args, **kwargs) -> Any:
        """
        MCP 작업을 안전하게 실행하는 래퍼 함수
        
        Args:
            operation_func: 실행할 MCP 작업 함수
            *args, **kwargs: 함수에 전달할 인자들
            
        Returns:
            Any: 작업 결과 또는 None (실패 시)
        """
        # Circuit Breaker 체크
        if self.circuit_breaker_open:
            if not self.reset_circuit_breaker():
                self.logger.warning("MCP Circuit Breaker가 열려있어 작업을 건너뜀")
                return None
        
        # MCP 연결 상태 체크
        if not self.mcp_connected:
            self.logger.warning("MCP 서버가 연결되지 않아 작업을 건너뜀")
            return None
        
        try:
            result = await operation_func(*args, **kwargs)
            # 성공 시 에러 카운트 리셋
            self.consecutive_error_count = 0
            return result
            
        except Exception as e:
            await self.handle_mcp_error(e)
            return None
    
    async def execute_local_tool(self, tool_name: str, selection_reason: str = None, **kwargs) -> Any:
        """
        로컬 툴 실행 (향상된 로깅 포함)
        
        Args:
            tool_name: 실행할 툴 이름
            selection_reason: 툴 선택 이유
            **kwargs: 툴에 전달할 매개변수
            
        Returns:
            Any: 툴 실행 결과
            
        Raises:
            ValueError: 존재하지 않는 툴 이름
            Exception: 툴 실행 중 발생한 에러
        """
        if tool_name not in self.local_tools:
            raise ValueError(f"존재하지 않는 로컬 툴: {tool_name}")
        
        start_time = datetime.now()
        
        try:
            self.logger.info(f"로컬 툴 실행 시작: {tool_name}", 
                           parameters=kwargs,
                           selection_reason=selection_reason)
            
            # 매개변수 검증 로깅
            if not self.validate_tool_parameters(tool_name, kwargs):
                self.logger.warning(f"툴 매개변수 검증 실패: {tool_name}", parameters=kwargs)
            
            # 툴 함수 실행
            tool_function = self.local_tools[tool_name]
            result = tool_function(**kwargs)
            
            # 실행 시간 계산
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 향상된 로그 기록
            self._log_tool_execution(
                tool_name=tool_name,
                tool_type="local",
                parameters=kwargs,
                execution_time=execution_time,
                result=result,
                success=True,
                selection_reason=selection_reason
            )
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 상세 에러 로깅
            self.logger.error(
                f"로컬 툴 실행 실패: {tool_name}",
                error=str(e),
                error_type=type(e).__name__,
                parameters=kwargs,
                execution_time=execution_time,
                selection_reason=selection_reason
            )
            
            # 에러도 향상된 로그에 기록
            self._log_tool_execution(
                tool_name=tool_name,
                tool_type="local",
                parameters=kwargs,
                execution_time=execution_time,
                result=f"ERROR: {str(e)}",
                success=False,
                error=str(e),
                selection_reason=selection_reason
            )
            
            raise
    
    def get_local_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """
        로컬 툴 정보 반환
        
        Args:
            tool_name: 툴 이름
            
        Returns:
            Dict[str, Any]: 툴 정보 (이름, 설명, 매개변수 등)
        """
        if tool_name not in self.local_tools:
            return {}
        
        tool_function = self.local_tools[tool_name]
        
        return {
            "name": tool_name,
            "type": "local",
            "description": tool_function.__doc__ or "설명 없음",
            "function": tool_function.__name__
        }
    
    def get_all_local_tools_info(self) -> List[Dict[str, Any]]:
        """모든 로컬 툴 정보 반환"""
        return [self.get_local_tool_info(tool_name) for tool_name in self.local_tools.keys()]
    
    def log_tool_selection_reasoning(self, message: str, selected_tools: List[Dict[str, Any]]) -> None:
        """
        툴 선택 과정 로깅
        
        Args:
            message: 원본 메시지
            selected_tools: 선택된 툴들
        """
        self.logger.info("툴 선택 과정",
                        message=message,
                        selected_tools_count=len(selected_tools),
                        selected_tools=[{
                            'name': tool['name'],
                            'type': tool['type'],
                            'reason': tool['reason']
                        } for tool in selected_tools])
    
    def log_result_integration_process(self, results: List[Dict[str, Any]], final_response: str) -> None:
        """
        결과 통합 과정 로깅
        
        Args:
            results: 툴 실행 결과들
            final_response: 최종 통합 응답
        """
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]
        
        self.logger.info("결과 통합 과정",
                        total_results=len(results),
                        successful_results=len(successful_results),
                        failed_results=len(failed_results),
                        final_response_length=len(final_response),
                        successful_tools=[r['tool_name'] for r in successful_results],
                        failed_tools=[r['tool_name'] for r in failed_results])
    
    async def call_tool_by_name(self, tool_name: str, tool_type: str = "auto", **kwargs) -> Any:
        """
        툴 이름으로 툴 호출 (로컬 또는 MCP)
        
        Args:
            tool_name: 툴 이름
            tool_type: 툴 타입 ("local", "mcp", "auto")
            **kwargs: 툴 매개변수
            
        Returns:
            Any: 툴 실행 결과
        """
        if tool_type == "local" or (tool_type == "auto" and tool_name in self.local_tools):
            return await self.execute_local_tool(tool_name, **kwargs)
        elif tool_type == "mcp" or tool_type == "auto":
            # TODO: MCP 툴 실행 로직 (향후 구현)
            raise NotImplementedError("MCP 툴 실행은 향후 구현 예정")
        else:
            raise ValueError(f"알 수 없는 툴 타입: {tool_type}")
    
    def validate_tool_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """
        툴 매개변수 검증
        
        Args:
            tool_name: 툴 이름
            parameters: 검증할 매개변수
            
        Returns:
            bool: 검증 성공 여부
        """
        if tool_name not in self.local_tools:
            return False
        
        try:
            # 간단한 매개변수 검증 (실제 호출 없이)
            tool_function = self.local_tools[tool_name]
            
            # 함수 시그니처 검사는 향후 개선 가능
            # 현재는 기본적인 검증만 수행
            return True
            
        except Exception as e:
            self.logger.warning(f"툴 매개변수 검증 실패: {tool_name}", error=str(e))
            return False
    
    async def _analyze_message_and_select_tools(self, message: str) -> List[Dict[str, Any]]:
        """
        메시지를 분석하고 적절한 툴을 선택 (LLM 스타일)
        
        Args:
            message: 사용자 메시지
            
        Returns:
            List[Dict[str, Any]]: 선택된 툴들의 정보 리스트
        """
        self.logger.info("메시지 분석 시작", message=message)
        
        # 간단한 패턴 매칭으로 툴 선택
        selected_tools = self._simple_tool_selection(message)
        
        # 툴 정보에 타입 추가
        for tool in selected_tools:
            tool['type'] = 'local'  # 현재는 모두 로컬 툴
        
        # MCP 툴 추가 (Notion 관련)
        if self.mcp_connected:
            message_lower = message.lower()
            mcp_keywords = ['notion', '노션', '메모', '문서', '페이지', '노트']
            if any(keyword in message_lower for keyword in mcp_keywords):
                selected_tools.append({
                    'name': 'search',  # 실제 Smithery Notion MCP 툴명
                    'type': 'mcp',
                    'parameters': {'query': message},
                    'reason': 'Notion 관련 키워드 감지'
                })
                self.logger.info("MCP 툴 선택", reason="Notion 관련 키워드 감지")
        
        self.logger.info("툴 선택 완료", 
                        selected_count=len(selected_tools),
                        tools=[tool['name'] for tool in selected_tools])
        
        return selected_tools
    
    def _simple_tool_selection(self, message: str) -> List[Dict[str, Any]]:
        """간단한 패턴 매칭으로 툴 선택"""
        message_lower = message.lower().strip()
        selected_tools = []
        
        # 날짜 관련
        if any(word in message_lower for word in ['날짜', '오늘', '현재', 'date', 'today']):
            selected_tools.append({
                'name': 'current_date',
                'parameters': {},
                'reason': '날짜 관련 키워드 감지'
            })
        
        # 수학 연산 - 간단한 패턴
        import re
        
        # 덧셈: "15 + 25", "15 더하기 25"
        add_patterns = [r'(\d+)\s*\+\s*(\d+)', r'(\d+)\s*더하기\s*(\d+)']
        for pattern in add_patterns:
            matches = re.findall(pattern, message_lower)
            for match in matches:
                selected_tools.append({
                    'name': 'add',
                    'parameters': {'a': int(match[0]), 'b': int(match[1])},
                    'reason': f'덧셈 패턴 감지: {match[0]} + {match[1]}'
                })
        
        # 뺄셈: "50 - 30", "50 빼기 30"
        sub_patterns = [r'(\d+)\s*-\s*(\d+)', r'(\d+)\s*빼기\s*(\d+)']
        for pattern in sub_patterns:
            matches = re.findall(pattern, message_lower)
            for match in matches:
                selected_tools.append({
                    'name': 'subtract',
                    'parameters': {'a': int(match[0]), 'b': int(match[1])},
                    'reason': f'뺄셈 패턴 감지: {match[0]} - {match[1]}'
                })
        
        # 곱셈: "7 * 8", "7 곱하기 8"
        mul_patterns = [r'(\d+)\s*[*×]\s*(\d+)', r'(\d+)\s*곱하기\s*(\d+)']
        for pattern in mul_patterns:
            matches = re.findall(pattern, message_lower)
            for match in matches:
                selected_tools.append({
                    'name': 'multiply',
                    'parameters': {'a': int(match[0]), 'b': int(match[1])},
                    'reason': f'곱셈 패턴 감지: {match[0]} × {match[1]}'
                })
        
        # 나눗셈: "100 / 4", "100 나누기 4"
        div_patterns = [r'(\d+)\s*[/÷]\s*(\d+)', r'(\d+)\s*나누기\s*(\d+)']
        for pattern in div_patterns:
            matches = re.findall(pattern, message_lower)
            for match in matches:
                selected_tools.append({
                    'name': 'divide',
                    'parameters': {'a': int(match[0]), 'b': int(match[1])},
                    'reason': f'나눗셈 패턴 감지: {match[0]} ÷ {match[1]}'
                })
        
        return selected_tools
    
    def _extract_math_operations(self, message: str) -> List[Dict[str, Any]]:
        """
        메시지에서 수학 연산을 추출
        
        Args:
            message: 사용자 메시지
            
        Returns:
            List[Dict[str, Any]]: 추출된 수학 연산들
        """
        import re
        operations = []
        
        # 기본 수학 연산 패턴들
        patterns = [
            # "A + B" 형태
            (r'(\d+(?:\.\d+)?)\s*\+\s*(\d+(?:\.\d+)?)', 'add', '덧셈 패턴 감지'),
            # "A - B" 형태  
            (r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', 'subtract', '뺄셈 패턴 감지'),
            # "A * B" 또는 "A × B" 형태
            (r'(\d+(?:\.\d+)?)\s*[*×]\s*(\d+(?:\.\d+)?)', 'multiply', '곱셈 패턴 감지'),
            # "A / B" 또는 "A ÷ B" 형태
            (r'(\d+(?:\.\d+)?)\s*[/÷]\s*(\d+(?:\.\d+)?)', 'divide', '나눗셈 패턴 감지'),
        ]
        
        for pattern, operation, reason in patterns:
            matches = re.findall(pattern, message)
            for match in matches:
                try:
                    a = float(match[0])
                    b = float(match[1])
                    
                    # 정수로 변환 가능하면 정수로 변환
                    if a.is_integer():
                        a = int(a)
                    if b.is_integer():
                        b = int(b)
                    
                    operations.append({
                        'name': operation,
                        'type': 'local',
                        'parameters': {'a': a, 'b': b},
                        'reason': reason
                    })
                except ValueError:
                    continue
        
        # 자연어 수학 표현 처리
        natural_patterns = [
            (r'(\d+(?:\.\d+)?)\s*더하기\s*(\d+(?:\.\d+)?)', 'add', '자연어 덧셈 감지'),
            (r'(\d+(?:\.\d+)?)\s*빼기\s*(\d+(?:\.\d+)?)', 'subtract', '자연어 뺄셈 감지'),
            (r'(\d+(?:\.\d+)?)\s*곱하기\s*(\d+(?:\.\d+)?)', 'multiply', '자연어 곱셈 감지'),
            (r'(\d+(?:\.\d+)?)\s*나누기\s*(\d+(?:\.\d+)?)', 'divide', '자연어 나눗셈 감지'),
            # 추가 한국어 패턴들
            (r'(\d+(?:\.\d+)?)\s*을?\s*(\d+(?:\.\d+)?)\s*으?로\s*나눠?줘?', 'divide', '자연어 나눗셈 감지'),
            (r'(\d+(?:\.\d+)?)\s*을?\s*(\d+(?:\.\d+)?)\s*으?로\s*나누', 'divide', '자연어 나눗셈 감지'),
            (r'(\d+(?:\.\d+)?)\s*나누기\s*(\d+(?:\.\d+)?)', 'divide', '자연어 나눗셈 감지'),
        ]
        
        for pattern, operation, reason in natural_patterns:
            matches = re.findall(pattern, message)
            for match in matches:
                try:
                    a = float(match[0])
                    b = float(match[1])
                    
                    if a.is_integer():
                        a = int(a)
                    if b.is_integer():
                        b = int(b)
                    
                    operations.append({
                        'name': operation,
                        'type': 'local',
                        'parameters': {'a': a, 'b': b},
                        'reason': reason
                    })
                except ValueError:
                    continue
        
        return operations
    
    async def _execute_selected_tools(self, selected_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        선택된 툴들을 실행
        
        Args:
            selected_tools: 실행할 툴들의 정보
            
        Returns:
            List[Dict[str, Any]]: 실행 결과들
        """
        results = []
        
        for tool_info in selected_tools:
            tool_name = tool_info['name']
            tool_type = tool_info['type']
            parameters = tool_info['parameters']
            reason = tool_info['reason']
            
            try:
                self.logger.info(f"툴 실행 시작: {tool_name}", 
                               tool_type=tool_type,
                               parameters=parameters,
                               reason=reason)
                
                if tool_type == 'local':
                    result = await self.execute_local_tool(tool_name, selection_reason=reason, **parameters)
                elif tool_type == 'mcp':
                    # TODO: MCP 툴 실행 로직 구현
                    result = f"MCP 툴 '{tool_name}' 실행은 향후 구현 예정"
                else:
                    raise ValueError(f"알 수 없는 툴 타입: {tool_type}")
                
                results.append({
                    'tool_name': tool_name,
                    'tool_type': tool_type,
                    'parameters': parameters,
                    'result': result,
                    'success': True,
                    'reason': reason
                })
                
            except Exception as e:
                error_msg = f"툴 실행 실패: {str(e)}"
                self.logger.error(f"툴 실행 오류: {tool_name}", 
                                error=str(e),
                                tool_type=tool_type,
                                parameters=parameters)
                
                results.append({
                    'tool_name': tool_name,
                    'tool_type': tool_type,
                    'parameters': parameters,
                    'result': error_msg,
                    'success': False,
                    'reason': reason,
                    'error': str(e)
                })
        
        return results
    
    async def _integrate_tool_results(self, original_message: str, 
                                    selected_tools: List[Dict[str, Any]], 
                                    results: List[Dict[str, Any]]) -> str:
        """
        툴 실행 결과들을 통합하여 최종 응답 생성
        
        Args:
            original_message: 원본 사용자 메시지
            selected_tools: 선택된 툴들
            results: 툴 실행 결과들
            
        Returns:
            str: 통합된 최종 응답
        """
        if not results:
            return "실행할 수 있는 툴이 없습니다."
        
        # 성공한 결과와 실패한 결과 분리
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]
        
        response_parts = []
        
        # 성공한 결과들 처리
        if successful_results:
            if len(successful_results) == 1:
                result = successful_results[0]
                if result['tool_name'] == 'current_date':
                    response_parts.append(f"오늘 날짜는 {result['result']}입니다.")
                elif result['tool_name'] in ['add', 'subtract', 'multiply', 'divide']:
                    operation_names = {
                        'add': '덧셈',
                        'subtract': '뺄셈', 
                        'multiply': '곱셈',
                        'divide': '나눗셈'
                    }
                    op_name = operation_names.get(result['tool_name'], '계산')
                    params = result['parameters']
                    response_parts.append(
                        f"{params['a']} {self._get_operation_symbol(result['tool_name'])} {params['b']} = {result['result']}"
                    )
                else:
                    response_parts.append(f"{result['tool_name']} 결과: {result['result']}")
            else:
                # 여러 결과 통합
                response_parts.append("요청하신 작업들의 결과입니다:")
                for i, result in enumerate(successful_results, 1):
                    if result['tool_name'] == 'current_date':
                        response_parts.append(f"{i}. 현재 날짜: {result['result']}")
                    elif result['tool_name'] in ['add', 'subtract', 'multiply', 'divide']:
                        params = result['parameters']
                        response_parts.append(
                            f"{i}. {params['a']} {self._get_operation_symbol(result['tool_name'])} {params['b']} = {result['result']}"
                        )
                    else:
                        response_parts.append(f"{i}. {result['tool_name']}: {result['result']}")
        
        # 실패한 결과들 처리
        if failed_results:
            if successful_results:
                response_parts.append("\n다음 작업에서 오류가 발생했습니다:")
            else:
                response_parts.append("요청 처리 중 오류가 발생했습니다:")
            
            for result in failed_results:
                response_parts.append(f"- {result['tool_name']}: {result['result']}")
        
        # 툴 사용 정보 로깅
        self.logger.info("결과 통합 완료",
                        total_tools=len(results),
                        successful_tools=len(successful_results),
                        failed_tools=len(failed_results),
                        response_length=len('\n'.join(response_parts)))
        
        return '\n'.join(response_parts)
    
    def _get_operation_symbol(self, operation_name: str) -> str:
        """수학 연산 이름을 기호로 변환"""
        symbols = {
            'add': '+',
            'subtract': '-',
            'multiply': '×',
            'divide': '÷'
        }
        return symbols.get(operation_name, '?')
    
    def get_tool_usage_statistics(self) -> Dict[str, Any]:
        """
        툴 사용 통계 반환
        
        Returns:
            Dict[str, Any]: 툴 사용 통계 정보
        """
        if not self.execution_logs:
            return {
                "total_executions": 0,
                "tool_usage": {},
                "average_execution_time": 0,
                "success_rate": 0,
                "error_summary": {}
            }
        
        total_executions = len(self.execution_logs)
        tool_usage = {}
        total_time = 0
        successful_executions = 0
        error_summary = {}
        
        for log in self.execution_logs:
            # 툴별 사용 횟수
            if log.tool_name not in tool_usage:
                tool_usage[log.tool_name] = {
                    "count": 0,
                    "total_time": 0,
                    "successes": 0,
                    "errors": 0,
                    "tool_type": log.tool_type
                }
            
            tool_usage[log.tool_name]["count"] += 1
            tool_usage[log.tool_name]["total_time"] += log.execution_time
            total_time += log.execution_time
            
            # 성공/실패 카운트
            if isinstance(log.result, str) and log.result.startswith("ERROR:"):
                tool_usage[log.tool_name]["errors"] += 1
                error_type = log.result.split(":")[1].strip() if ":" in log.result else "Unknown"
                error_summary[error_type] = error_summary.get(error_type, 0) + 1
            else:
                tool_usage[log.tool_name]["successes"] += 1
                successful_executions += 1
        
        # 평균 실행 시간 계산
        for tool_name in tool_usage:
            tool_data = tool_usage[tool_name]
            if tool_data["count"] > 0:
                tool_data["average_time"] = tool_data["total_time"] / tool_data["count"]
                tool_data["success_rate"] = tool_data["successes"] / tool_data["count"]
        
        return {
            "total_executions": total_executions,
            "tool_usage": tool_usage,
            "average_execution_time": total_time / total_executions if total_executions > 0 else 0,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "error_summary": error_summary,
            "session_start_time": self.execution_logs[0].timestamp if self.execution_logs else None,
            "last_execution_time": self.execution_logs[-1].timestamp if self.execution_logs else None
        }
    
    def get_recent_tool_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        최근 툴 활동 내역 반환
        
        Args:
            limit: 반환할 최대 항목 수
            
        Returns:
            List[Dict[str, Any]]: 최근 툴 활동
        """
        # 최근 로그를 시간순으로 정렬하여 반환
        sorted_logs = sorted(self.execution_logs, key=lambda x: x.timestamp, reverse=True)
        
        recent_activity = []
        for log in sorted_logs[:limit]:
            activity = {
                'tool_name': log.tool_name,
                'tool_type': log.tool_type,
                'parameters': log.parameters,
                'execution_time': log.execution_time,
                'timestamp': log.timestamp,
                'success': not (isinstance(log.result, str) and log.result.startswith("ERROR:")),
                'result': log.result
            }
            recent_activity.append(activity)
        
        return recent_activity
    
    def log_tool_selection_reasoning(self, message: str, selected_tools: List[Dict[str, Any]]) -> None:
        """
        툴 선택 과정과 이유를 상세히 로깅
        
        Args:
            message: 원본 사용자 메시지
            selected_tools: 선택된 툴들
        """
        self.logger.info("툴 선택 과정 분석",
                        original_message=message,
                        message_length=len(message),
                        selected_tool_count=len(selected_tools),
                        available_local_tools=len(self.local_tools),
                        mcp_available=self.mcp_connected)
        
        for i, tool in enumerate(selected_tools):
            self.logger.info(f"선택된 툴 #{i+1}",
                           tool_name=tool['name'],
                           tool_type=tool['type'],
                           selection_reason=tool['reason'],
                           parameters=tool['parameters'])
        
        # 선택되지 않은 툴들에 대한 분석도 로깅
        all_available_tools = set(self.local_tools.keys())
        selected_tool_names = {tool['name'] for tool in selected_tools if tool['type'] == 'local'}
        unselected_tools = all_available_tools - selected_tool_names
        
        if unselected_tools:
            self.logger.debug("선택되지 않은 로컬 툴들",
                            unselected_tools=list(unselected_tools),
                            reason="메시지 패턴과 매치되지 않음")
    
    def log_result_integration_process(self, results: List[Dict[str, Any]], final_response: str) -> None:
        """
        결과 통합 과정을 상세히 로깅
        
        Args:
            results: 툴 실행 결과들
            final_response: 최종 통합된 응답
        """
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]
        
        self.logger.info("결과 통합 과정",
                        total_results=len(results),
                        successful_results=len(successful_results),
                        failed_results=len(failed_results),
                        final_response_length=len(final_response))
        
        # 각 결과의 통합 방식 로깅
        for result in results:
            self.logger.debug("개별 결과 처리",
                            tool_name=result['tool_name'],
                            success=result['success'],
                            result_type=type(result['result']).__name__,
                            result_length=len(str(result['result'])))
        
        # 응답 생성 전략 로깅
        if len(successful_results) == 1:
            self.logger.debug("단일 결과 응답 생성", strategy="single_result")
        elif len(successful_results) > 1:
            self.logger.debug("다중 결과 통합 응답 생성", strategy="multiple_results")
        
        if failed_results:
            self.logger.debug("실패 결과 포함 응답 생성", 
                            failed_count=len(failed_results),
                            strategy="error_handling")
    
    def export_execution_logs(self, format: str = "json") -> str:
        """
        실행 로그를 지정된 형식으로 내보내기
        
        Args:
            format: 내보낼 형식 ("json", "csv", "text")
            
        Returns:
            str: 형식화된 로그 데이터
        """
        if not self.execution_logs:
            return "실행 로그가 없습니다."
        
        if format.lower() == "json":
            import json
            log_data = []
            for log in self.execution_logs:
                log_data.append({
                    "timestamp": log.timestamp.isoformat(),
                    "tool_name": log.tool_name,
                    "tool_type": log.tool_type,
                    "parameters": log.parameters,
                    "execution_time": log.execution_time,
                    "result": str(log.result)
                })
            return json.dumps(log_data, indent=2, ensure_ascii=False)
        
        elif format.lower() == "csv":
            lines = ["timestamp,tool_name,tool_type,execution_time,parameters,result"]
            for log in self.execution_logs:
                lines.append(f"{log.timestamp.isoformat()},{log.tool_name},{log.tool_type},"
                           f"{log.execution_time},\"{log.parameters}\",\"{str(log.result)}\"")
            return "\n".join(lines)
        
        elif format.lower() == "text":
            lines = ["=== 툴 실행 로그 ===\n"]
            for i, log in enumerate(self.execution_logs, 1):
                lines.append(f"{i}. [{log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] "
                           f"{log.tool_name} ({log.tool_type}) - {log.execution_time:.3f}초")
                lines.append(f"   매개변수: {log.parameters}")
                lines.append(f"   결과: {log.result}")
                lines.append("")
            return "\n".join(lines)
        
        else:
            raise ValueError(f"지원하지 않는 형식: {format}")
    
    async def monitor_system_health(self) -> Dict[str, Any]:
        """
        시스템 상태 모니터링
        
        Returns:
            Dict[str, Any]: 시스템 상태 정보
        """
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "local_tools": {
                "available": len(self.local_tools),
                "status": "healthy"
            },
            "mcp_connection": {
                "connected": self.mcp_connected,
                "status": "healthy" if self.mcp_connected else "disconnected"
            },
            "execution_logs": {
                "total_count": len(self.execution_logs),
                "memory_usage": f"{len(str(self.execution_logs))} bytes"
            }
        }
        
        # 최근 에러 체크
        recent_errors = [log for log in self.execution_logs[-10:] 
                        if isinstance(log.result, str) and log.result.startswith("ERROR:")]
        
        if recent_errors:
            health_status["recent_errors"] = {
                "count": len(recent_errors),
                "last_error_time": recent_errors[-1].timestamp.isoformat(),
                "status": "warning"
            }
        
        # 성능 체크
        if self.execution_logs:
            avg_time = sum(log.execution_time for log in self.execution_logs) / len(self.execution_logs)
            if avg_time > 2.0:  # 평균 2초 이상
                health_status["performance"] = {
                    "average_execution_time": avg_time,
                    "status": "slow"
                }
        
        self.logger.info("시스템 상태 모니터링 완료", health_status=health_status)
        return health_status