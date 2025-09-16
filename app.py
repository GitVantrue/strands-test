# Streamlit 메인 애플리케이션

import streamlit as st
import asyncio
from datetime import datetime
from typing import List, Dict
from agent import StrandsAgentManager

def main():
    """메인 애플리케이션 진입점"""
    # Streamlit 페이지 설정
    st.set_page_config(
        page_title="Strands Agent 챗봇",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # 세션 상태 초기화
    initialize_session_state()
    
    # 사이드바 - 에이전트 상태 및 정보
    with st.sidebar:
        st.header("🔧 에이전트 상태")
        
        # 에이전트 초기화 상태
        if st.session_state.agent_initialized:
            st.success("✅ 에이전트 초기화 완료")
            
            # 사용 가능한 툴 정보 표시
            if st.session_state.agent_manager:
                tools_info = st.session_state.agent_manager.get_available_tools()
                
                st.subheader("📊 사용 가능한 툴")
                st.write(f"**로컬 툴**: {tools_info['local_tools']['count']}개")
                with st.expander("로컬 툴 목록"):
                    for tool in tools_info['local_tools']['tools']:
                        st.write(f"• {tool}")
                
                mcp_status = "🟢 연결됨" if tools_info['mcp_tools']['connected'] else "🔴 연결 안됨"
                st.write(f"**MCP 서버**: {mcp_status}")
                
                # 툴 사용 통계
                if st.button("📈 사용 통계 보기"):
                    stats = st.session_state.agent_manager.get_tool_usage_statistics()
                    if stats['total_executions'] > 0:
                        st.write(f"**총 실행 횟수**: {stats['total_executions']}")
                        st.write(f"**성공률**: {stats['success_rate']:.1%}")
                        st.write(f"**평균 실행 시간**: {stats['average_execution_time']:.3f}초")
                    else:
                        st.write("아직 툴 사용 기록이 없습니다.")
        else:
            st.warning("⏳ 에이전트 초기화 대기 중")
        
        st.markdown("---")
        
        # 도움말 및 사용 가이드
        st.subheader("💡 사용 가이드")
        
        # 기본 기능 안내
        with st.expander("📋 사용 가능한 기능", expanded=False):
            st.markdown("""
            **🗓️ 날짜 조회**
            - '오늘 날짜 알려줘'
            - '현재 날짜는?'
            
            **🧮 수학 계산**
            - '15 + 25는 얼마야?'
            - '100 나누기 4'
            - '3.14 × 2'
            
            **🔄 복합 요청**
            - '오늘 날짜와 10 * 5 계산해줘'
            - '현재 날짜 알려주고 50 - 20도 계산해줘'
            """)
        
        # 팁과 주의사항
        with st.expander("💡 사용 팁", expanded=False):
            st.markdown("""
            **✅ 효과적인 사용법**
            - 명확하고 구체적인 요청을 하세요
            - 한 번에 여러 작업을 요청할 수 있습니다
            - 계산 시 숫자와 연산자를 명확히 구분하세요
            
            **⚠️ 주의사항**
            - 0으로 나누기는 불가능합니다
            - 매우 큰 숫자는 처리 시간이 오래 걸릴 수 있습니다
            - 네트워크 문제 시 일부 기능이 제한될 수 있습니다
            """)
        
        # 문제 해결 가이드
        with st.expander("🔧 문제 해결", expanded=False):
            st.markdown("""
            **🌐 연결 문제**
            - 인터넷 연결을 확인하세요
            - 페이지를 새로고침해보세요
            - MCP 서버 재연결 버튼을 사용하세요
            
            **⏰ 응답 지연**
            - 더 간단한 요청을 시도해보세요
            - 잠시 후 다시 시도하세요
            - 채팅을 초기화하고 다시 시작하세요
            
            **❌ 오류 발생**
            - 요청 내용을 다시 확인하세요
            - 다른 방식으로 표현해보세요
            - 시스템 상태를 확인하세요
            """)
        
        # 현재 시스템 상태 요약
        if st.session_state.agent_initialized and st.session_state.agent_manager:
            st.subheader("📊 시스템 상태")
            mcp_status = st.session_state.agent_manager.get_mcp_status()
            
            if mcp_status["connected"]:
                st.success("🟢 모든 기능 사용 가능")
            else:
                st.warning("🟡 로컬 기능만 사용 가능")
                st.info("날짜 조회와 수학 계산은 정상 작동합니다")
            
            # 최근 활동 요약
            stats = st.session_state.agent_manager.get_tool_usage_statistics()
            if stats['total_executions'] > 0:
                st.write(f"**이번 세션**: 툴 {stats['total_executions']}회 실행, 성공률 {stats['success_rate']:.1%}")
        else:
            st.info("🔄 첫 메시지를 보내면 시스템이 초기화됩니다")
    
    # 페이지 제목과 컨트롤
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🤖 Strands Agent 챗봇")
    with col2:
        if st.button("🗑️ 채팅 초기화", help="채팅 기록을 모두 삭제합니다"):
            reset_chat_history()
            st.rerun()
    
    st.markdown("---")
    
    # 에이전트 상태 표시
    show_agent_status()
    
    # 채팅 기록 표시
    display_chat_history()
    
    # 사용자 입력창 (향상된 UI)
    with st.container():
        # 입력 도움말
        if not st.session_state.messages or len(st.session_state.messages) <= 1:
            st.info("💬 첫 메시지를 보내보세요! 예: '오늘 날짜 알려줘' 또는 '10 + 5는?'")
        
        col1, col2, col3 = st.columns([3, 1, 0.5])
        
        with col1:
            # 동적 placeholder 생성
            placeholder_examples = [
                "오늘 날짜 알려줘",
                "15 + 25는 얼마야?",
                "100 나누기 4",
                "현재 날짜와 3 × 7 계산해줘"
            ]
            
            import random
            current_placeholder = random.choice(placeholder_examples)
            
            user_input = st.text_input(
                "메시지를 입력하세요...",
                key="user_input",
                placeholder=f"예: {current_placeholder}",
                label_visibility="collapsed",
                help="Enter 키를 눌러서도 전송할 수 있습니다"
            )
        
        with col2:
            send_button = st.button("📤 전송", type="primary", use_container_width=True)
        
        with col3:
            # 빠른 예시 버튼
            if st.button("💡", help="빠른 예시", use_container_width=True):
                st.session_state.show_quick_examples = not st.session_state.get('show_quick_examples', False)
        
        # 빠른 예시 버튼들
        if st.session_state.get('show_quick_examples', False):
            st.markdown("**빠른 예시:**")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("📅 오늘 날짜", use_container_width=True):
                    st.session_state.user_input = "오늘 날짜 알려줘"
                    handle_user_input("오늘 날짜 알려줘")
                    st.rerun()
            
            with col2:
                if st.button("🧮 10 + 5", use_container_width=True):
                    st.session_state.user_input = "10 + 5는 얼마야?"
                    handle_user_input("10 + 5는 얼마야?")
                    st.rerun()
            
            with col3:
                if st.button("✖️ 7 × 8", use_container_width=True):
                    st.session_state.user_input = "7 곱하기 8"
                    handle_user_input("7 곱하기 8")
                    st.rerun()
            
            with col4:
                if st.button("🔄 복합 요청", use_container_width=True):
                    st.session_state.user_input = "오늘 날짜와 15 + 25 계산해줘"
                    handle_user_input("오늘 날짜와 15 + 25 계산해줘")
                    st.rerun()
        
        # 입력 길이 표시
        if user_input:
            char_count = len(user_input)
            max_chars = 10000
            
            if char_count > max_chars * 0.8:  # 80% 이상일 때 경고
                color = "red" if char_count > max_chars else "orange"
                st.markdown(f"<small style='color:{color}'>글자 수: {char_count}/{max_chars}</small>", 
                          unsafe_allow_html=True)
    
    # 사용자 입력 처리 (Enter 키 지원)
    if (send_button or user_input.endswith('\n')) and user_input.strip():
        # Enter로 전송된 경우 개행 문자 제거
        clean_input = user_input.strip().rstrip('\n')
        if clean_input:
            handle_user_input(clean_input)
            # 입력창 초기화
            st.session_state.user_input = ""
            st.rerun()

def initialize_session_state():
    """세션 상태 초기화"""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "안녕하세요! Strands Agent 챗봇입니다. 무엇을 도와드릴까요?",
                "timestamp": datetime.now()
            }
        ]
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if "agent_manager" not in st.session_state:
        st.session_state.agent_manager = None
        st.session_state.agent_initialized = False

@st.cache_resource
def get_agent_manager():
    """에이전트 매니저 인스턴스를 캐시하여 반환"""
    return StrandsAgentManager()

async def initialize_agent():
    """에이전트 초기화 (비동기)"""
    if st.session_state.agent_manager is None:
        st.session_state.agent_manager = get_agent_manager()
    
    if not st.session_state.agent_initialized:
        await st.session_state.agent_manager.initialize()
        st.session_state.agent_initialized = True

def run_async_function(coro):
    """비동기 함수를 동기 방식으로 실행"""
    try:
        # 기존 이벤트 루프가 있는지 확인
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 이미 실행 중인 루프가 있으면 새 스레드에서 실행
            import concurrent.futures
            import threading
            
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # 이벤트 루프가 없으면 새로 생성
        return asyncio.run(coro)

def reset_chat_history():
    """채팅 기록 초기화"""
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "채팅이 초기화되었습니다. 새로운 대화를 시작해보세요!",
            "timestamp": datetime.now()
        }
    ]
    st.session_state.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

def display_chat_history():
    """채팅 기록 표시"""
    st.markdown("### 채팅 기록")
    
    # 메시지가 없으면 안내 메시지 표시
    if not st.session_state.messages:
        st.info("아직 메시지가 없습니다. 첫 메시지를 보내보세요!")
        return
    
    # 채팅 메시지들을 순서대로 표시
    for message in st.session_state.messages:
        display_message(message)

def handle_user_input(user_input: str):
    """사용자 입력 처리 (향상된 에러 처리)"""
    # 입력 검증
    if not user_input or not user_input.strip():
        st.warning("메시지를 입력해주세요.")
        return
    
    if len(user_input) > 10000:
        st.error("메시지가 너무 깁니다. 10,000자 이하로 입력해주세요.")
        return
    
    # 사용자 메시지를 세션 상태에 추가
    user_message = {
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now()
    }
    st.session_state.messages.append(user_message)
    
    # 에이전트 초기화 확인
    if not st.session_state.agent_initialized:
        with st.spinner("에이전트를 초기화하는 중..."):
            try:
                run_async_function(initialize_agent())
            except ConnectionError:
                error_response = {
                    "role": "assistant",
                    "content": "네트워크 연결에 문제가 있습니다. 인터넷 연결을 확인하고 다시 시도해주세요.",
                    "timestamp": datetime.now(),
                    "error_type": "connection"
                }
                st.session_state.messages.append(error_response)
                return
            except TimeoutError:
                error_response = {
                    "role": "assistant",
                    "content": "초기화 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.",
                    "timestamp": datetime.now(),
                    "error_type": "timeout"
                }
                st.session_state.messages.append(error_response)
                return
            except Exception as e:
                error_response = {
                    "role": "assistant",
                    "content": generate_user_friendly_error_message(e, "initialization"),
                    "timestamp": datetime.now(),
                    "error_type": "initialization"
                }
                st.session_state.messages.append(error_response)
                return
    
    # 에이전트를 통한 메시지 처리 (향상된 UI 피드백)
    progress_container = st.empty()
    status_container = st.empty()
    
    try:
        # 처리 단계별 진행 상황 표시
        with progress_container.container():
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("🔍 메시지 분석 중...")
            progress_bar.progress(20)
            
            # 비동기 에이전트 호출을 동기 방식으로 처리 (타임아웃 적용)
            status_text.text("🛠️ 적절한 툴 선택 중...")
            progress_bar.progress(40)
            
            status_text.text("⚙️ 툴 실행 중...")
            progress_bar.progress(60)
            
            response = run_async_function_with_timeout(
                st.session_state.agent_manager.process_message(user_input),
                timeout=60  # 60초 타임아웃
            )
            
            status_text.text("📝 응답 생성 중...")
            progress_bar.progress(80)
            
            # 에이전트 상태 및 툴 사용 정보 수집
            agent_status = st.session_state.agent_manager.get_mcp_status()
            recent_logs = st.session_state.agent_manager.get_recent_tool_activity(limit=5)
            
            status_text.text("✅ 완료!")
            progress_bar.progress(100)
            
            # 사용된 툴 정보 추출
            tool_info = []
            for log in recent_logs:
                if log['timestamp'] > user_message['timestamp']:  # 이번 요청에서 사용된 툴만
                    tool_info.append({
                        'name': log['tool_name'],
                        'type': log['tool_type'],
                        'success': not (isinstance(log.get('result'), str) and log['result'].startswith("ERROR:")),
                        'execution_time': log['execution_time'],
                        'reason': log.get('reason', '알 수 없음'),
                        'error': log.get('result') if isinstance(log.get('result'), str) and log['result'].startswith("ERROR:") else None
                    })
            
            bot_response = {
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now(),
                "agent_status": agent_status,
                "tool_info": tool_info,
                "processing_steps": [
                    "메시지 분석 완료",
                    f"툴 {len(tool_info)}개 선택",
                    f"툴 실행 완료 (성공: {len([t for t in tool_info if t['success']])}, 실패: {len([t for t in tool_info if not t['success']])})",
                    "응답 생성 완료"
                ]
            }
            st.session_state.messages.append(bot_response)
            
        # 진행 상황 표시 제거
        progress_container.empty()
        status_container.empty()
            
    except TimeoutError:
            error_response = {
                "role": "assistant",
                "content": "응답 생성 시간이 초과되었습니다. 더 간단한 요청을 시도해보세요.",
                "timestamp": datetime.now(),
                "error_type": "timeout"
            }
            st.session_state.messages.append(error_response)
            
    except MemoryError:
            error_response = {
                "role": "assistant",
                "content": "메모리 부족으로 요청을 처리할 수 없습니다. 페이지를 새로고침하고 더 간단한 요청을 시도해주세요.",
                "timestamp": datetime.now(),
                "error_type": "memory"
            }
            st.session_state.messages.append(error_response)
            
    except Exception as e:
        error_response = {
            "role": "assistant",
            "content": generate_user_friendly_error_message(e, "processing"),
            "timestamp": datetime.now(),
            "error_type": "processing"
        }
        st.session_state.messages.append(error_response)
    
    # 진행 상황 표시 제거 (에러 발생 시에도)
    progress_container.empty()
    status_container.empty()

def generate_user_friendly_error_message(error: Exception, context: str) -> str:
    """
    사용자 친화적 에러 메시지 생성
    
    Args:
        error: 발생한 예외
        context: 에러 발생 컨텍스트 ("initialization", "processing")
        
    Returns:
        str: 사용자 친화적 에러 메시지
    """
    error_type = type(error).__name__
    
    if context == "initialization":
        if error_type == 'ConnectionError':
            return "서버 연결에 실패했습니다. 네트워크 연결을 확인해주세요."
        elif error_type == 'TimeoutError':
            return "초기화 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
        elif error_type == 'PermissionError':
            return "권한 문제로 초기화에 실패했습니다."
        else:
            return "초기화 중 문제가 발생했습니다. 페이지를 새로고침해주세요."
    
    elif context == "processing":
        if error_type == 'ConnectionError':
            return "네트워크 연결에 문제가 있습니다. 연결을 확인하고 다시 시도해주세요."
        elif error_type == 'TimeoutError':
            return "처리 시간이 초과되었습니다. 더 간단한 요청을 시도해주세요."
        elif error_type == 'MemoryError':
            return "메모리 부족으로 요청을 처리할 수 없습니다."
        elif 'JSON' in error_type or 'Parse' in error_type:
            return "데이터 처리 중 오류가 발생했습니다. 다시 시도해주세요."
        else:
            return "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
    
    return f"오류가 발생했습니다: {str(error)}"

def run_async_function_with_timeout(coro, timeout: int = 60):
    """
    타임아웃이 적용된 비동기 함수 실행
    
    Args:
        coro: 실행할 코루틴
        timeout: 타임아웃 시간 (초)
        
    Returns:
        코루틴 실행 결과
        
    Raises:
        TimeoutError: 타임아웃 발생 시
    """
    import asyncio
    import concurrent.futures
    import threading
    
    def run_in_thread():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
        finally:
            new_loop.close()
    
    try:
        # 기존 이벤트 루프가 있는지 확인
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 이미 실행 중인 루프가 있으면 새 스레드에서 실행
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result(timeout=timeout + 5)  # 추가 여유시간
        else:
            return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
    except RuntimeError:
        # 이벤트 루프가 없으면 새로 생성
        return asyncio.run(asyncio.wait_for(coro, timeout=timeout))

def display_message(message: Dict):
    """채팅 메시지를 표시하는 함수 (향상된 에러 표시)"""
    if message["role"] == "user":
        with st.chat_message("user"):
            st.write(message["content"])
            st.caption(f"🕐 {message['timestamp'].strftime('%H:%M:%S')}")
    else:
        with st.chat_message("assistant"):
            # 에러 타입에 따른 아이콘 표시
            error_type = message.get("error_type")
            if error_type:
                if error_type == "connection":
                    st.error("🌐 연결 오류")
                elif error_type == "timeout":
                    st.warning("⏰ 시간 초과")
                elif error_type == "memory":
                    st.error("💾 메모리 부족")
                elif error_type == "initialization":
                    st.warning("🔧 초기화 오류")
                elif error_type == "processing":
                    st.warning("⚠️ 처리 오류")
            
            st.write(message["content"])
            st.caption(f"🤖 {message['timestamp'].strftime('%H:%M:%S')}")
            
            # 에이전트 상태 정보 표시
            if "agent_status" in message:
                agent_status = message["agent_status"]
                if not agent_status["connected"] and agent_status["connection_error"]:
                    with st.expander("⚠️ 시스템 상태"):
                        st.warning(f"MCP 서버 연결 안됨: {agent_status['connection_error']}")
                        if agent_status["circuit_breaker_open"]:
                            st.error("🔴 Circuit Breaker 활성화 - 일시적으로 외부 서비스 사용 중단")
                        st.info("현재 로컬 기능만 사용 가능합니다 (날짜 조회, 수학 계산)")
            
            # 처리 과정 시각화
            if "processing_steps" in message:
                with st.expander("🔄 처리 과정", expanded=False):
                    for i, step in enumerate(message["processing_steps"], 1):
                        st.write(f"{i}. {step}")
            
            # 툴 사용 정보 상세 표시
            if "tool_info" in message and message["tool_info"]:
                with st.expander("🔧 사용된 툴 상세 정보", expanded=True):
                    for i, tool in enumerate(message["tool_info"], 1):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            status_icon = "✅" if tool.get("success", True) else "❌"
                            tool_type_icon = "🏠" if tool['type'] == 'local' else "🌐"
                            st.write(f"{status_icon} {tool_type_icon} **{tool['name']}**")
                            st.caption(f"선택 이유: {tool.get('reason', '알 수 없음')}")
                        
                        with col2:
                            if 'execution_time' in tool:
                                exec_time = tool['execution_time']
                                if exec_time < 0.1:
                                    time_color = "green"
                                elif exec_time < 1.0:
                                    time_color = "orange"
                                else:
                                    time_color = "red"
                                st.markdown(f"⏱️ <span style='color:{time_color}'>{exec_time:.3f}초</span>", 
                                          unsafe_allow_html=True)
                        
                        with col3:
                            if tool.get("success", True):
                                st.success("성공")
                            else:
                                st.error("실패")
                        
                        # 에러 정보 표시
                        if not tool.get("success", True) and "error" in tool:
                            st.error(f"🚨 오류: {tool['error']}")
                        
                        if i < len(message["tool_info"]):
                            st.divider()
                
                # 툴 실행 통계 요약
                successful_tools = [t for t in message["tool_info"] if t.get("success", True)]
                failed_tools = [t for t in message["tool_info"] if not t.get("success", True)]
                total_time = sum(t.get('execution_time', 0) for t in message["tool_info"])
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("총 툴 수", len(message["tool_info"]))
                with col2:
                    st.metric("성공", len(successful_tools), delta=f"{len(successful_tools)}/{len(message['tool_info'])}")
                with col3:
                    st.metric("실패", len(failed_tools), delta=f"{len(failed_tools)}/{len(message['tool_info'])}")
                with col4:
                    st.metric("총 실행시간", f"{total_time:.3f}초")
            
            # 사용자 피드백 수집
            if "feedback_collected" not in message:
                st.markdown("---")
                st.write("**이 응답이 도움이 되었나요?**")
                
                col1, col2, col3 = st.columns([1, 1, 2])
                
                with col1:
                    if st.button("👍 도움됨", key=f"helpful_{message['timestamp']}", use_container_width=True):
                        collect_feedback(message, "helpful", "사용자가 응답을 도움이 된다고 평가")
                        st.success("피드백 감사합니다!")
                        st.rerun()
                
                with col2:
                    if st.button("👎 도움안됨", key=f"not_helpful_{message['timestamp']}", use_container_width=True):
                        collect_feedback(message, "not_helpful", "사용자가 응답을 도움이 안된다고 평가")
                        st.info("피드백 감사합니다. 더 나은 서비스를 위해 노력하겠습니다.")
                        st.rerun()
                
                with col3:
                    feedback_text = st.text_input("추가 의견 (선택사항)", 
                                                key=f"feedback_text_{message['timestamp']}", 
                                                placeholder="개선사항이나 의견을 알려주세요")
                    if feedback_text and st.button("📝 의견 제출", key=f"submit_feedback_{message['timestamp']}"):
                        collect_feedback(message, "comment", feedback_text)
                        st.success("소중한 의견 감사합니다!")
                        st.rerun()

def collect_feedback(message: Dict, feedback_type: str, feedback_content: str):
    """
    사용자 피드백 수집
    
    Args:
        message: 피드백 대상 메시지
        feedback_type: 피드백 유형 ("helpful", "not_helpful", "comment")
        feedback_content: 피드백 내용
    """
    # 피드백 수집 표시
    message["feedback_collected"] = True
    message["feedback"] = {
        "type": feedback_type,
        "content": feedback_content,
        "timestamp": datetime.now()
    }
    
    # 로깅 (실제 서비스에서는 데이터베이스에 저장)
    if st.session_state.agent_manager:
        st.session_state.agent_manager.logger.info(
            "사용자 피드백 수집",
            feedback_type=feedback_type,
            feedback_content=feedback_content,
            message_timestamp=message["timestamp"],
            tool_count=len(message.get("tool_info", [])),
            response_length=len(message["content"])
        )

def show_agent_status():
    """에이전트 상태를 표시하는 함수 (향상된 에러 표시)"""
    if not st.session_state.agent_initialized:
        st.info("💡 첫 메시지를 보내면 에이전트가 자동으로 초기화됩니다.")
    else:
        # 상태 표시
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("에이전트", "활성화", delta="준비됨")
        with col2:
            if st.session_state.agent_manager:
                local_count = len(st.session_state.agent_manager.local_tools)
                st.metric("로컬 툴", f"{local_count}개", delta="사용 가능")
        with col3:
            if st.session_state.agent_manager:
                mcp_status_info = st.session_state.agent_manager.get_mcp_status()
                if mcp_status_info["connected"]:
                    st.metric("MCP 서버", "연결됨", delta="정상")
                else:
                    st.metric("MCP 서버", "연결 안됨", delta="오류")
        
        # 에러 상태 상세 표시
        if st.session_state.agent_manager:
            mcp_status = st.session_state.agent_manager.get_mcp_status()
            
            if not mcp_status["connected"] and mcp_status["connection_error"]:
                with st.expander("⚠️ MCP 서버 연결 문제", expanded=False):
                    st.error(f"연결 오류: {mcp_status['connection_error']}")
                    
                    if mcp_status["last_error_time"]:
                        st.write(f"마지막 오류 시간: {mcp_status['last_error_time'].strftime('%H:%M:%S')}")
                    
                    if mcp_status["consecutive_errors"] > 0:
                        st.write(f"연속 오류 횟수: {mcp_status['consecutive_errors']}")
                    
                    if mcp_status["circuit_breaker_open"]:
                        st.warning("🔴 Circuit Breaker 활성화 - 자동 복구 대기 중")
                        if mcp_status["circuit_breaker_reset_time"]:
                            reset_time = mcp_status["circuit_breaker_reset_time"]
                            elapsed = (datetime.now() - reset_time).total_seconds()
                            remaining = max(0, 300 - elapsed)  # 5분 후 리셋
                            st.write(f"자동 복구까지: {remaining:.0f}초")
                    
                    # 수동 재연결 버튼
                    if st.button("🔄 MCP 서버 재연결 시도"):
                        with st.spinner("재연결 시도 중..."):
                            success = run_async_function(st.session_state.agent_manager.reconnect_mcp())
                            if success:
                                st.success("재연결 성공!")
                                st.rerun()
                            else:
                                st.error("재연결 실패")
                    
                    st.info("💡 현재 로컬 기능만 사용 가능합니다 (날짜 조회, 수학 계산)")

if __name__ == "__main__":
    main()