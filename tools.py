"""
로컬 커스텀 툴 구현 (Strands Agent 스타일)
간단한 데코레이터를 사용하여 툴을 정의합니다.
"""

from datetime import datetime
from typing import Union, Dict, Any, List


def strands_tool(name: str, description: str):
    """Strands Agent의 툴로 함수를 등록하는 데코레이터"""
    def decorator(func):
        # 함수에 툴 관련 메타데이터를 추가
        func.tool_name = name
        func.tool_description = description
        return func
    return decorator


@strands_tool(
    name="current_date", 
    description="현재 날짜를 YYYY-MM-DD 형식으로 반환합니다. 오늘 날짜나 현재 날짜를 묻는 질문에 사용하세요."
)
def current_date() -> str:
    """현재 날짜를 반환합니다."""
    return datetime.now().strftime("%Y-%m-%d")


@strands_tool(
    name="add", 
    description="두 숫자를 더합니다. 덧셈, 합계, 플러스 연산에 사용하세요."
)
def add(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    """두 수를 더합니다."""
    return a + b


@strands_tool(
    name="subtract", 
    description="첫 번째 숫자에서 두 번째 숫자를 뺍니다. 뺄셈, 차이, 마이너스 연산에 사용하세요."
)
def subtract(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    """두 수를 뺍니다."""
    return a - b


@strands_tool(
    name="multiply", 
    description="두 숫자를 곱합니다. 곱셈, 곱하기, 배수 연산에 사용하세요."
)
def multiply(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    """두 수를 곱합니다."""
    return a * b


@strands_tool(
    name="divide", 
    description="첫 번째 숫자를 두 번째 숫자로 나눕니다. 나눗셈, 나누기, 몫 연산에 사용하세요."
)
def divide(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    """두 수를 나눕니다."""
    if b == 0:
        raise ZeroDivisionError("0으로 나눌 수 없습니다")
    return a / b


# 툴 수집 및 관리 함수들
def get_all_tools() -> Dict[str, Any]:
    """데코레이터로 등록된 모든 툴을 수집"""
    tools = {}
    
    # 현재 모듈의 모든 함수를 검사
    import sys
    current_module = sys.modules[__name__]
    
    for name in dir(current_module):
        obj = getattr(current_module, name)
        if callable(obj) and hasattr(obj, 'tool_name'):
            tools[obj.tool_name] = {
                'function': obj,
                'name': obj.tool_name,
                'description': obj.tool_description
            }
    
    return tools


def get_available_tools() -> List[str]:
    """사용 가능한 툴 이름 목록 반환"""
    return list(get_all_tools().keys())


def execute_tool(name: str, **kwargs) -> Any:
    """툴 실행"""
    tools = get_all_tools()
    if name not in tools:
        raise ValueError(f"Unknown tool: {name}")
    
    tool_func = tools[name]['function']
    return tool_func(**kwargs)