# Deployment Guide

This guide covers deploying TracKaMate Backend to production environments.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Database Setup](#database-setup)
4. [Application Deployment](#application-deployment)
5. [Docker Deployment](#docker-deployment)
6. [Cloud Deployment](#cloud-deployment)
7. [Security Checklist](#security-checklist)
8. [Monitoring](#monitoring)

---

## Prerequisites

### Server Requirements

- **OS**: Ubuntu 20.04+ / Debian 11+ / RHEL 8+
- **Python**: 3.13+
- **Database**: MySQL 8.0+
- **Memory**: 2GB RAM minimum
- **Storage**: 20GB+ (for uploads)
- **Network**: HTTPS enabled

### Required Accounts

- MySQL database server
- OpenAI API account (for food tracking)
- Domain name (optional but recommended)
- SSL certificate (Let's Encrypt recommended)

---

## Environment Configuration

### 1. Create Production `.env` File

```env
# Flask Configuration
SECRET_KEY=<generate-strong-random-key-64-chars>
JWT_SECRET_KEY=<generate-strong-random-key-64-chars>
FLASK_ENV=production
FLASK_DEBUG=False

# Database
DATABASE_URI=mysql+pymysql://username:password@localhost:3306/trackamate_db

# OpenAI
OPENAI_API_KEY=sk-proj-your-production-key-here

# Upload Configuration
MAX_CONTENT_LENGTH=16777216  # 16MB in bytes
UPLOAD_FOLDER=/var/www/trackamate/uploads

# CORS (restrict to your frontend domain)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 2. Generate Strong Secret Keys

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Generate JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Database Setup

### 1. Create Production Database

```sql
CREATE DATABASE trackamate_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'trackamate_user'@'localhost' IDENTIFIED BY 'strong-password-here';

GRANT ALL PRIVILEGES ON trackamate_db.* TO 'trackamate_user'@'localhost';

FLUSH PRIVILEGES;
```

### 2. Run Database Migrations

```bash
python setup_db.py
```

### 3. Database Backups

Set up automated daily backups:

```bash
# Create backup script
cat > /usr/local/bin/backup_trackamate.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/trackamate"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
mysqldump -u trackamate_user -p'password' trackamate_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup uploads
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /var/www/trackamate/uploads

# Keep only last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete
EOF

chmod +x /usr/local/bin/backup_trackamate.sh
```

Add to crontab:
```bash
crontab -e
# Add line:
0 2 * * * /usr/local/bin/backup_trackamate.sh
```

---

## Application Deployment

### Option 1: Using Gunicorn (Recommended)

#### 1. Install Gunicorn

```bash
pip install gunicorn
```

#### 2. Create Gunicorn Configuration

`gunicorn_config.py`:
```python
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "/var/log/trackamate/access.log"
errorlog = "/var/log/trackamate/error.log"
loglevel = "info"

# Process naming
proc_name = "trackamate"
```

#### 3. Create Systemd Service

`/etc/systemd/system/trackamate.service`:
```ini
[Unit]
Description=TracKaMate Backend API
After=network.target mysql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/trackamate
Environment="PATH=/var/www/trackamate/venv/bin"
ExecStart=/var/www/trackamate/venv/bin/gunicorn -c gunicorn_config.py run:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 4. Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable trackamate
sudo systemctl start trackamate
sudo systemctl status trackamate
```

---

### Option 2: Using uWSGI

#### 1. Install uWSGI

```bash
pip install uwsgi
```

#### 2. Create uWSGI Configuration

`uwsgi.ini`:
```ini
[uwsgi]
module = run:app
master = true
processes = 4
threads = 2
socket = 127.0.0.1:8000
chmod-socket = 660
vacuum = true
die-on-term = true
```

#### 3. Create Systemd Service

Similar to Gunicorn, but use:
```ini
ExecStart=/var/www/trackamate/venv/bin/uwsgi --ini uwsgi.ini
```

---

## Nginx Configuration

### 1. Install Nginx

```bash
sudo apt update
sudo apt install nginx
```

### 2. Create Nginx Configuration

`/etc/nginx/sites-available/trackamate`:
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Upload size limit
    client_max_body_size 16M;

    # Logging
    access_log /var/log/nginx/trackamate_access.log;
    error_log /var/log/nginx/trackamate_error.log;

    # Static files (uploads)
    location /uploads/ {
        alias /var/www/trackamate/uploads/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Proxy to Flask app
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

### 3. Enable Site and Restart Nginx

```bash
sudo ln -s /etc/nginx/sites-available/trackamate /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Docker Deployment

### 1. Create Dockerfile

`Dockerfile`:
```dockerfile
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy application
COPY . .

# Create uploads directory
RUN mkdir -p uploads/burn uploads/invest uploads/commit uploads/food

# Expose port
EXPOSE 8000

# Run with gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8000", "-w", "4", "run:app"]
```

### 2. Create docker-compose.yml

`docker-compose.yml`:
```yaml
version: '3.8'

services:
  db:
    image: mysql:8.0
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: trackamate_db
      MYSQL_USER: trackamate_user
      MYSQL_PASSWORD: userpassword
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"

  app:
    build: .
    restart: always
    ports:
      - "8000:8000"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - DATABASE_URI=mysql+pymysql://trackamate_user:userpassword@db:3306/trackamate_db
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./uploads:/app/uploads
    depends_on:
      - db

volumes:
  mysql_data:
```

### 3. Deploy with Docker

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## Cloud Deployment

### AWS (Elastic Beanstalk)

1. Install EB CLI:
```bash
pip install awsebcli
```

2. Initialize EB:
```bash
eb init -p python-3.13 trackamate-backend
```

3. Create environment:
```bash
eb create trackamate-prod
```

4. Deploy:
```bash
eb deploy
```

---

### Google Cloud (App Engine)

1. Create `app.yaml`:
```yaml
runtime: python313
entrypoint: gunicorn -b :$PORT run:app

env_variables:
  SECRET_KEY: "your-secret-key"
  JWT_SECRET_KEY: "your-jwt-secret"
  DATABASE_URI: "mysql+pymysql://user:pass@/dbname?unix_socket=/cloudsql/project:region:instance"
  OPENAI_API_KEY: "your-openai-key"

automatic_scaling:
  min_instances: 1
  max_instances: 10
```

2. Deploy:
```bash
gcloud app deploy
```

---

### Heroku

1. Create `Procfile`:
```
web: gunicorn run:app
```

2. Deploy:
```bash
heroku create trackamate-backend
git push heroku main
heroku config:set SECRET_KEY="your-secret-key"
heroku config:set JWT_SECRET_KEY="your-jwt-secret"
heroku config:set DATABASE_URI="your-db-uri"
```

---

## Security Checklist

### Pre-Deployment

- [ ] Strong SECRET_KEY and JWT_SECRET_KEY generated
- [ ] Database credentials are strong and unique
- [ ] `.env` file is NOT in version control
- [ ] CORS origins restricted to frontend domain only
- [ ] Debug mode disabled (`FLASK_DEBUG=False`)
- [ ] All dependencies updated to latest versions
- [ ] SQL injection prevention verified (using ORM only)
- [ ] File upload validation enabled
- [ ] File size limits configured (16MB)

### Post-Deployment

- [ ] HTTPS/SSL enabled and enforced
- [ ] Security headers configured in Nginx
- [ ] Database backups automated
- [ ] Upload folder backups configured
- [ ] Firewall rules configured (only ports 80, 443 open)
- [ ] SSH access secured (key-based auth only)
- [ ] Rate limiting configured (optional)
- [ ] Monitoring and logging enabled
- [ ] Error pages don't expose sensitive info

---

## Monitoring

### 1. Application Logs

Monitor logs in real-time:
```bash
tail -f /var/log/trackamate/error.log
tail -f /var/log/nginx/trackamate_error.log
```

### 2. Health Check Endpoint

Add to `run.py`:
```python
@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200
```

### 3. Uptime Monitoring

Use services like:
- UptimeRobot (free)
- Pingdom
- StatusCake

Monitor: `https://api.yourdomain.com/health`

### 4. Performance Monitoring

Consider using:
- New Relic
- Datadog
- Sentry (for error tracking)

---

## Maintenance

### Update Application

```bash
cd /var/www/trackamate
source venv/bin/activate
git pull origin main
pip install -r requirements.txt
sudo systemctl restart trackamate
```

### Database Migrations

When models change:
```bash
python setup_db.py  # Creates new tables (doesn't drop existing)
```

For more complex migrations, use Alembic:
```bash
pip install alembic
alembic init migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
```

---

## Troubleshooting

### Application won't start

Check logs:
```bash
sudo journalctl -u trackamate -n 50
```

### Database connection fails

Test connection:
```bash
mysql -u trackamate_user -p trackamate_db
```

### Uploads not working

Check permissions:
```bash
sudo chown -R www-data:www-data /var/www/trackamate/uploads
sudo chmod -R 755 /var/www/trackamate/uploads
```

### High memory usage

Reduce Gunicorn workers in `gunicorn_config.py`

---

## Rollback Procedure

1. Stop application:
```bash
sudo systemctl stop trackamate
```

2. Restore database:
```bash
gunzip < /backups/trackamate/db_20241022_020000.sql.gz | mysql -u trackamate_user -p trackamate_db
```

3. Restore code:
```bash
cd /var/www/trackamate
git checkout previous-commit-hash
```

4. Restart:
```bash
sudo systemctl start trackamate
```

---

**Last Updated**: October 2025
**Version**: 1.0
