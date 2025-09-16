@echo off
REM Strands Agent Chatbot 실행 스크립트 (Windows)
REM 이 스크립트는 애플리케이션을 시작하기 전에 필요한 환경 설정을 확인합니다.

echo 🚀 Strands Agent Chatbot 시작 중...
echo ==================================

REM 1. Python 버전 확인
echo 📋 Python 버전 확인 중...
python --version
if %errorlevel% neq 0 (
    echo ❌ Python이 설치되지 않았거나 PATH에 없습니다
    pause
    exit /b 1
)

REM 2. 가상환경 활성화 (존재하는 경우)
if exist "venv\Scripts\activate.bat" (
    echo 🔧 가상환경 활성화 중...
    call venv\Scripts\activate.bat
)

REM 3. 의존성 설치 확인
echo 📦 의존성 확인 중...
if exist "requirements.txt" (
    pip install -r requirements.txt --quiet
    echo ✅ 의존성 설치 완료
) else (
    echo ❌ requirements.txt 파일을 찾을 수 없습니다
    pause
    exit /b 1
)

REM 4. 환경변수 파일 확인
echo 🔑 환경변수 확인 중...
if exist ".env" (
    echo ✅ .env 파일 발견
) else (
    echo ⚠️  .env 파일이 없습니다. .env.example을 참고하여 생성해주세요
)

REM 5. 포트 설정
if not defined STREAMLIT_SERVER_PORT set STREAMLIT_SERVER_PORT=8501
if not defined STREAMLIT_SERVER_ADDRESS set STREAMLIT_SERVER_ADDRESS=0.0.0.0

echo.
echo 🌐 서버 시작 정보:
echo    주소: http://%STREAMLIT_SERVER_ADDRESS%:%STREAMLIT_SERVER_PORT%
echo    로컬 접속: http://localhost:%STREAMLIT_SERVER_PORT%
echo.

REM 6. Streamlit 애플리케이션 시작
echo 🎯 Streamlit 애플리케이션 시작...
streamlit run app.py --server.port=%STREAMLIT_SERVER_PORT% --server.address=%STREAMLIT_SERVER_ADDRESS% --server.headless=true

echo.
echo 👋 애플리케이션이 종료되었습니다.
pause