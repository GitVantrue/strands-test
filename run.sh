#!/bin/bash

# Strands Agent Chatbot 실행 스크립트
# 이 스크립트는 애플리케이션을 시작하기 전에 필요한 환경 설정을 확인합니다.

set -e  # 에러 발생 시 스크립트 중단

echo "🚀 Strands Agent Chatbot 시작 중..."
echo "=================================="

# 1. Python 버전 확인
echo "📋 Python 버전 확인 중..."
python3 --version

# 2. 가상환경 활성화 (존재하는 경우)
if [ -d "venv" ]; then
    echo "🔧 가상환경 활성화 중..."
    source venv/bin/activate
fi

# 3. 의존성 설치 확인
echo "📦 의존성 확인 중..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
    echo "✅ 의존성 설치 완료"
else
    echo "❌ requirements.txt 파일을 찾을 수 없습니다"
    exit 1
fi

# 4. 환경변수 파일 확인
echo "🔑 환경변수 확인 중..."
if [ -f ".env" ]; then
    echo "✅ .env 파일 발견"
    # API 키 설정 확인 (민감한 정보는 표시하지 않음)
    if grep -q "NOTION_API_KEY=your_notion_api_key_here" .env; then
        echo "⚠️  NOTION_API_KEY가 기본값으로 설정되어 있습니다"
        echo "   실제 Notion API 키로 변경해주세요"
    fi
else
    echo "⚠️  .env 파일이 없습니다. .env.example을 참고하여 생성해주세요"
fi

# 5. 포트 설정
PORT=${STREAMLIT_SERVER_PORT:-8501}
HOST=${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}

echo ""
echo "🌐 서버 시작 정보:"
echo "   주소: http://$HOST:$PORT"
echo "   로컬 접속: http://localhost:$PORT"
echo ""

# 6. Streamlit 애플리케이션 시작
echo "🎯 Streamlit 애플리케이션 시작..."
streamlit run app.py --server.port=$PORT --server.address=$HOST --server.headless=true

echo ""
echo "👋 애플리케이션이 종료되었습니다."