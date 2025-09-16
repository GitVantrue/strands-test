# 배포 가이드

이 문서는 Strands Agent Chatbot을 다양한 환경에 배포하는 방법을 상세히 설명합니다.

## 📋 목차

1. [로컬 개발 환경](#로컬-개발-환경)
2. [AWS EC2 배포](#aws-ec2-배포)
3. [Docker 배포](#docker-배포)
4. [클라우드 플랫폼 배포](#클라우드-플랫폼-배포)
5. [프로덕션 고려사항](#프로덕션-고려사항)
6. [모니터링 및 유지보수](#모니터링-및-유지보수)

## 🖥️ 로컬 개발 환경

### 사전 요구사항

- **Python 3.8+**
- **Git**
- **pip** (Python 패키지 관리자)

### 설치 및 실행

```bash
# 1. 저장소 클론
git clone <repository-url>
cd strands-agent-chatbot

# 2. 가상환경 생성 (권장)
python3 -m venv venv

# 3. 가상환경 활성화
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 4. 의존성 설치
pip install -r requirements.txt

# 5. 환경변수 설정
cp .env.example .env
# .env 파일을 편집하여 필요한 API 키 설정

# 6. 애플리케이션 실행
./run.sh  # Linux/macOS
# 또는
run.bat   # Windows
```

## ☁️ AWS EC2 배포

### 1. EC2 인스턴스 설정

#### 인스턴스 생성

1. **AWS 콘솔**에서 EC2 서비스 접속
2. **Launch Instance** 클릭
3. **설정 선택**:
   - **AMI**: Amazon Linux 2 또는 Ubuntu 20.04 LTS
   - **Instance Type**: t2.micro (프리티어) 또는 t3.small (권장)
   - **Storage**: 8GB 이상
   - **Security Group**: 다음 포트 허용
     - SSH (22): 관리용
     - HTTP (80): 웹 접근용 (선택사항)
     - Custom TCP (8501): Streamlit 애플리케이션용

#### 보안 그룹 설정

```bash
# 인바운드 규칙
Type            Protocol    Port Range    Source
SSH             TCP         22           Your IP
HTTP            TCP         80           0.0.0.0/0
Custom TCP      TCP         8501         0.0.0.0/0
```

### 2. 서버 환경 설정

#### 인스턴스 접속

```bash
# SSH 키를 사용하여 접속
ssh -i your-key.pem ec2-user@your-ec2-public-ip
```

#### 시스템 업데이트 및 패키지 설치

```bash
# Amazon Linux 2
sudo yum update -y
sudo yum install python3 python3-pip git htop -y

# Ubuntu
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv git htop -y
```

### 3. 애플리케이션 배포

```bash
# 1. 저장소 클론
git clone <repository-url>
cd strands-agent-chatbot

# 2. 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경변수 설정
cp .env.example .env
nano .env  # 필요한 설정 입력

# 5. 실행 권한 부여
chmod +x run.sh
```

### 4. 서비스 등록 (systemd)

#### 서비스 파일 생성

```bash
sudo nano /etc/systemd/system/strands-agent.service
```

#### 서비스 파일 내용

```ini
[Unit]
Description=Strands Agent Chatbot
After=network.target

[Service]
Type=simple
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/strands-agent-chatbot
Environment=PATH=/home/ec2-user/strands-agent-chatbot/venv/bin
ExecStart=/home/ec2-user/strands-agent-chatbot/venv/bin/streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

#### 서비스 활성화

```bash
# 서비스 등록 및 시작
sudo systemctl daemon-reload
sudo systemctl enable strands-agent
sudo systemctl start strands-agent

# 상태 확인
sudo systemctl status strands-agent

# 로그 확인
sudo journalctl -u strands-agent -f
```

### 5. 리버스 프록시 설정 (Nginx)

#### Nginx 설치

```bash
# Amazon Linux 2
sudo amazon-linux-extras install nginx1 -y

# Ubuntu
sudo apt install nginx -y
```

#### Nginx 설정

```bash
sudo nano /etc/nginx/conf.d/strands-agent.conf
```

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 또는 EC2 public IP

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

#### Nginx 시작

```bash
sudo systemctl enable nginx
sudo systemctl start nginx
sudo systemctl status nginx
```

## 🐳 Docker 배포

### Dockerfile 생성

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 포트 노출
EXPOSE 8501

# 헬스체크
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# 애플리케이션 실행
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
```

### Docker Compose 설정

```yaml
version: '3.8'

services:
  strands-agent:
    build: .
    ports:
      - "8501:8501"
    environment:
      - LOG_LEVEL=INFO
      - STREAMLIT_SERVER_PORT=8501
      - STREAMLIT_SERVER_ADDRESS=0.0.0.0
    env_file:
      - .env
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Docker 실행

```bash
# 이미지 빌드
docker build -t strands-agent .

# 컨테이너 실행
docker run -d \
  --name strands-agent \
  -p 8501:8501 \
  --env-file .env \
  --restart unless-stopped \
  strands-agent

# 또는 Docker Compose 사용
docker-compose up -d
```

## 🌐 클라우드 플랫폼 배포

### Heroku 배포

#### 1. Heroku CLI 설치 및 로그인

```bash
# Heroku CLI 설치 (macOS)
brew tap heroku/brew && brew install heroku

# 로그인
heroku login
```

#### 2. Heroku 앱 생성

```bash
# 앱 생성
heroku create your-app-name

# Python 빌드팩 설정
heroku buildpacks:set heroku/python
```

#### 3. Procfile 생성

```bash
echo "web: streamlit run app.py --server.port=\$PORT --server.address=0.0.0.0 --server.headless=true" > Procfile
```

#### 4. 환경변수 설정

```bash
heroku config:set NOTION_API_KEY=your_api_key
heroku config:set LOG_LEVEL=INFO
```

#### 5. 배포

```bash
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

### Google Cloud Platform (Cloud Run)

#### 1. 프로젝트 설정

```bash
# gcloud CLI 설치 및 인증
gcloud auth login
gcloud config set project your-project-id
```

#### 2. Cloud Run 배포

```bash
# 컨테이너 이미지 빌드 및 푸시
gcloud builds submit --tag gcr.io/your-project-id/strands-agent

# Cloud Run 서비스 배포
gcloud run deploy strands-agent \
  --image gcr.io/your-project-id/strands-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8501 \
  --set-env-vars LOG_LEVEL=INFO
```

### Azure Container Instances

```bash
# 리소스 그룹 생성
az group create --name strands-agent-rg --location eastus

# 컨테이너 인스턴스 생성
az container create \
  --resource-group strands-agent-rg \
  --name strands-agent \
  --image your-registry/strands-agent:latest \
  --dns-name-label strands-agent-unique \
  --ports 8501 \
  --environment-variables LOG_LEVEL=INFO \
  --secure-environment-variables NOTION_API_KEY=your_api_key
```

## 🔧 프로덕션 고려사항

### 1. 보안 설정

#### HTTPS 설정 (Let's Encrypt)

```bash
# Certbot 설치
sudo yum install certbot python3-certbot-nginx -y  # Amazon Linux
sudo apt install certbot python3-certbot-nginx -y  # Ubuntu

# SSL 인증서 발급
sudo certbot --nginx -d your-domain.com

# 자동 갱신 설정
sudo crontab -e
# 다음 라인 추가:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

#### 방화벽 설정

```bash
# UFW (Ubuntu)
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'

# firewalld (Amazon Linux)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 2. 성능 최적화

#### Streamlit 설정 최적화

```toml
# .streamlit/config.toml
[server]
port = 8501
address = "0.0.0.0"
headless = true
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false

[theme]
base = "light"
```

#### 시스템 리소스 모니터링

```bash
# htop 설치 및 실행
sudo yum install htop -y  # Amazon Linux
sudo apt install htop -y  # Ubuntu
htop

# 메모리 사용량 확인
free -h

# 디스크 사용량 확인
df -h
```

### 3. 로그 관리

#### 로그 로테이션 설정

```bash
sudo nano /etc/logrotate.d/strands-agent
```

```
/home/ec2-user/strands-agent-chatbot/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ec2-user ec2-user
    postrotate
        systemctl reload strands-agent
    endscript
}
```

### 4. 백업 및 복구

#### 자동 백업 스크립트

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/home/ec2-user/backups"
APP_DIR="/home/ec2-user/strands-agent-chatbot"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 애플리케이션 백업
tar -czf $BACKUP_DIR/strands-agent-$DATE.tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  $APP_DIR

# 오래된 백업 삭제 (30일 이상)
find $BACKUP_DIR -name "strands-agent-*.tar.gz" -mtime +30 -delete

echo "Backup completed: strands-agent-$DATE.tar.gz"
```

#### 크론탭 설정

```bash
crontab -e
# 매일 새벽 2시에 백업
0 2 * * * /home/ec2-user/backup.sh >> /home/ec2-user/backup.log 2>&1
```

## 📊 모니터링 및 유지보수

### 1. 애플리케이션 모니터링

#### 헬스체크 스크립트

```bash
#!/bin/bash
# healthcheck.sh

URL="http://localhost:8501/_stcore/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $URL)

if [ $RESPONSE -eq 200 ]; then
    echo "$(date): Application is healthy"
    exit 0
else
    echo "$(date): Application is unhealthy (HTTP $RESPONSE)"
    # 서비스 재시작
    sudo systemctl restart strands-agent
    exit 1
fi
```

#### 모니터링 크론탭

```bash
# 5분마다 헬스체크
*/5 * * * * /home/ec2-user/healthcheck.sh >> /home/ec2-user/health.log 2>&1
```

### 2. 로그 분석

#### 로그 분석 스크립트

```bash
#!/bin/bash
# log_analysis.sh

LOG_FILE="/var/log/strands-agent/app.log"
DATE=$(date +%Y-%m-%d)

echo "=== Daily Log Summary for $DATE ==="
echo "Total requests: $(grep -c "$DATE" $LOG_FILE)"
echo "Errors: $(grep -c "ERROR" $LOG_FILE | grep "$DATE")"
echo "Warnings: $(grep -c "WARNING" $LOG_FILE | grep "$DATE")"
echo ""
echo "Top errors:"
grep "ERROR" $LOG_FILE | grep "$DATE" | cut -d' ' -f4- | sort | uniq -c | sort -nr | head -5
```

### 3. 성능 모니터링

#### 시스템 메트릭 수집

```bash
#!/bin/bash
# metrics.sh

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.2f", $3/$2 * 100.0)}')
DISK_USAGE=$(df -h / | awk 'NR==2{print $5}' | cut -d'%' -f1)

echo "$TIMESTAMP,CPU:$CPU_USAGE%,Memory:$MEMORY_USAGE%,Disk:$DISK_USAGE%" >> /home/ec2-user/metrics.log
```

### 4. 업데이트 및 배포

#### 무중단 배포 스크립트

```bash
#!/bin/bash
# deploy.sh

APP_DIR="/home/ec2-user/strands-agent-chatbot"
BACKUP_DIR="/home/ec2-user/backups"
DATE=$(date +%Y%m%d_%H%M%S)

cd $APP_DIR

# 현재 버전 백업
tar -czf $BACKUP_DIR/pre-deploy-$DATE.tar.gz .

# 새 코드 가져오기
git fetch origin
git checkout main
git pull origin main

# 의존성 업데이트
source venv/bin/activate
pip install -r requirements.txt

# 서비스 재시작
sudo systemctl restart strands-agent

# 헬스체크
sleep 10
if curl -f http://localhost:8501/_stcore/health; then
    echo "Deployment successful"
else
    echo "Deployment failed, rolling back..."
    tar -xzf $BACKUP_DIR/pre-deploy-$DATE.tar.gz
    sudo systemctl restart strands-agent
    exit 1
fi
```

## 🚨 문제 해결

### 일반적인 문제들

#### 1. 서비스가 시작되지 않음

```bash
# 서비스 상태 확인
sudo systemctl status strands-agent

# 로그 확인
sudo journalctl -u strands-agent -n 50

# 설정 파일 검증
sudo systemctl daemon-reload
```

#### 2. 포트 충돌

```bash
# 포트 사용 확인
sudo netstat -tlnp | grep 8501

# 프로세스 종료
sudo kill -9 <PID>
```

#### 3. 메모리 부족

```bash
# 메모리 사용량 확인
free -h
ps aux --sort=-%mem | head

# 스왑 파일 생성 (임시 해결책)
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 4. 디스크 공간 부족

```bash
# 디스크 사용량 확인
df -h
du -sh /home/ec2-user/* | sort -hr

# 로그 파일 정리
sudo find /var/log -name "*.log" -mtime +30 -delete
```

### 로그 레벨별 디버깅

```bash
# DEBUG 레벨로 실행
export LOG_LEVEL=DEBUG
sudo systemctl restart strands-agent

# 실시간 로그 모니터링
sudo journalctl -u strands-agent -f
```

## 📞 지원 및 문의

배포 과정에서 문제가 발생하면:

1. **로그 확인**: 상세한 에러 로그 수집
2. **환경 정보**: OS, Python 버전, 의존성 버전 확인
3. **네트워크 상태**: 방화벽, 보안 그룹 설정 확인
4. **리소스 상태**: CPU, 메모리, 디스크 사용량 확인

---

이 가이드를 따라 성공적으로 배포하시기 바랍니다! 🚀