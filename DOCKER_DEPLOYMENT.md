# TracKaMate Backend - Docker Deployment Guide

**Last Updated**: December 2025

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Deployment Options](#deployment-options)
5. [Production Setup](#production-setup)
6. [Troubleshooting](#troubleshooting)
7. [Maintenance](#maintenance)

---

## Prerequisites

### Required Software
- **Docker**: 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose**: 2.0+ (included with Docker Desktop)

### Check Installation
```bash
docker --version
docker-compose --version
```

Expected output:
```
Docker version 24.0.0+
Docker Compose version v2.20.0+
```

---

## Quick Start

### Option 1: Backend Only (Use External Database)

**Step 1**: Clone and navigate to project
```bash
cd C:\Homelab\trackamate_be
```

**Step 2**: Create `.env` file
```bash
cp .env.example .env
# Edit .env with your actual values
```

**Step 3**: Update DATABASE_URI in `.env`
```env
# Use your existing MySQL database
DATABASE_URI=mysql+pymysql://mrlhzq:abcd1234@172.31.176.1/trackamate_prod
```

**Step 4**: Build and run
```bash
docker-compose up -d backend
```

**Step 5**: Verify
```bash
curl http://localhost:5000/status
# Expected: "OK"
```

---

### Option 2: Backend + Containerized MySQL

**Step 1**: Update `.env` for containerized database
```env
# Use 'db' as hostname (docker service name)
DATABASE_URI=mysql+pymysql://mrlhzq:abcd1234@db:3306/trackamate_prod

# MySQL configuration
MYSQL_ROOT_PASSWORD=secure_root_password
MYSQL_DATABASE=trackamate_prod
MYSQL_USER=mrlhzq
MYSQL_PASSWORD=abcd1234
```

**Step 2**: Start all services
```bash
docker-compose up -d
```

This starts:
- **backend**: Flask API on port 5000
- **db**: MySQL 8.0 on port 3306

**Step 3**: Check services
```bash
docker-compose ps
```

**Step 4**: View logs
```bash
docker-compose logs -f backend
```

---

## Configuration

### Environment Variables

All configuration is done via `.env` file:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here-change-this
JWT_SECRET_KEY=your-jwt-secret-key-change-this

# Database (Option 1: External DB)
DATABASE_URI=mysql+pymysql://username:password@host:port/database

# Database (Option 2: Containerized DB)
DATABASE_URI=mysql+pymysql://mrlhzq:abcd1234@db:3306/trackamate_prod
MYSQL_ROOT_PASSWORD=root_password
MYSQL_DATABASE=trackamate_prod
MYSQL_USER=mrlhzq
MYSQL_PASSWORD=abcd1234

# OpenAI API
OPENAI_API_KEY=sk-proj-your-key-here

# Flask Environment
FLASK_ENV=production
```

### Volume Mounts

Data persisted in volumes:

| Volume | Container Path | Purpose |
|--------|---------------|---------|
| `./uploads` | `/app/uploads` | User uploaded images |
| `./logs` | `/app/logs` | Application logs |
| `mysql-data` | `/var/lib/mysql` | MySQL database files |

---

## Deployment Options

### Development Mode

Run with code hot-reloading:

```bash
# Override CMD in docker-compose
docker-compose run --rm -p 5000:5000 backend flask run --host=0.0.0.0 --debug
```

Or create `docker-compose.dev.yml`:
```yaml
version: '3.8'

services:
  backend:
    extends:
      file: docker-compose.yml
      service: backend
    environment:
      - FLASK_ENV=development
    volumes:
      - .:/app
    command: flask run --host=0.0.0.0 --debug
```

Run: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up`

---

### Production Mode

For production deployment with Nginx reverse proxy:

**Step 1**: Create Nginx config

Create `nginx/nginx.conf`:
```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:5000;
    }

    server {
        listen 80;
        server_name your-domain.com;

        location / {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Increase upload size limit
        client_max_body_size 10M;
    }
}
```

**Step 2**: Run with Nginx
```bash
docker-compose --profile production up -d
```

This starts:
- backend (port 5000)
- db (port 3306)
- nginx (port 80, 443)

---

## Production Setup

### Security Best Practices

#### 1. Use Strong Secrets
```bash
# Generate secure secrets
python -c "import secrets; print(secrets.token_hex(32))"
```

Update `.env`:
```env
SECRET_KEY=<generated-secret-1>
JWT_SECRET_KEY=<generated-secret-2>
```

#### 2. Run Database Migrations
```bash
# Access backend container
docker exec -it trackamate-backend bash

# Run migration
python migrations/add_meal_time_column.py upgrade
```

#### 3. Restrict Database Access

In `docker-compose.yml`, remove port exposure if not needed:
```yaml
db:
  # ports:
  #   - "3306:3306"  # Comment out to prevent external access
```

#### 4. Enable HTTPS (Production)

Add SSL certificates to `nginx/ssl/`:
```
nginx/ssl/
├── cert.pem
└── key.pem
```

Update `nginx/nginx.conf`:
```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    # ... rest of config
}
```

---

## Docker Commands Cheat Sheet

### Build & Start
```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Start specific service
docker-compose up -d backend

# Rebuild and start
docker-compose up -d --build
```

### Stop & Remove
```bash
# Stop services
docker-compose stop

# Stop and remove containers
docker-compose down

# Remove containers and volumes
docker-compose down -v
```

### Logs & Monitoring
```bash
# View all logs
docker-compose logs

# Follow logs
docker-compose logs -f backend

# View last 100 lines
docker-compose logs --tail=100 backend

# Check service status
docker-compose ps
```

### Execute Commands
```bash
# Open bash in container
docker exec -it trackamate-backend bash

# Run Python command
docker exec trackamate-backend python -c "print('Hello')"

# Run migration
docker exec trackamate-backend python migrations/add_meal_time_column.py upgrade
```

### Database Management
```bash
# Access MySQL CLI
docker exec -it trackamate-mysql mysql -u mrlhzq -p trackamate_prod

# Backup database
docker exec trackamate-mysql mysqldump -u root -p trackamate_prod > backup.sql

# Restore database
docker exec -i trackamate-mysql mysql -u root -p trackamate_prod < backup.sql
```

---

## Troubleshooting

### Backend Won't Start

**Check logs**:
```bash
docker-compose logs backend
```

**Common issues**:
1. **Database connection failed**: Verify DATABASE_URI in `.env`
2. **Port already in use**: Change port in docker-compose.yml
3. **Missing dependencies**: Rebuild image with `--no-cache`

```bash
docker-compose build --no-cache backend
docker-compose up -d backend
```

### Cannot Connect to Database

**From backend container**:
```bash
docker exec -it trackamate-backend bash
python -c "from app import db; db.session.execute('SELECT 1')"
```

**Check database is running**:
```bash
docker-compose ps db
docker-compose logs db
```

**Test connection manually**:
```bash
docker exec trackamate-mysql mysql -u mrlhzq -p -e "SHOW DATABASES;"
```

### Upload Directory Permissions

If uploads fail:
```bash
# Fix permissions
docker exec -u root trackamate-backend chown -R appuser:appuser /app/uploads
```

### Container Health Check Failing

Check health status:
```bash
docker inspect trackamate-backend | grep -A 10 Health
```

Test endpoint manually:
```bash
curl http://localhost:5000/status
```

---

## Maintenance

### Update Application Code

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build backend
```

### Database Backup

**Automated backup script** (`backup.sh`):
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec trackamate-mysql mysqldump -u root -p${MYSQL_ROOT_PASSWORD} trackamate_prod > backups/backup_${DATE}.sql
echo "Backup created: backup_${DATE}.sql"
```

Run:
```bash
chmod +x backup.sh
./backup.sh
```

### View Resource Usage

```bash
# Container stats
docker stats trackamate-backend trackamate-mysql

# Disk usage
docker system df
```

### Clean Up Old Images

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune
```

---

## Scaling

### Horizontal Scaling (Multiple Backend Instances)

Update `docker-compose.yml`:
```yaml
backend:
  # ... existing config
  deploy:
    replicas: 3
```

Or scale manually:
```bash
docker-compose up -d --scale backend=3
```

**Note**: Requires load balancer (Nginx) to distribute traffic.

---

## CI/CD Integration

### GitHub Actions Example

`.github/workflows/deploy.yml`:
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /path/to/trackamate_be
            git pull
            docker-compose up -d --build backend
```

---

## Environment-Specific Configs

### docker-compose.prod.yml
```yaml
version: '3.8'

services:
  backend:
    restart: always
    environment:
      - FLASK_ENV=production
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Run: `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

---

## Health Checks & Monitoring

### Built-in Health Check

Endpoint: `GET /status`

Returns: `"OK"` (200)

### Docker Health Status

```bash
# Check health
docker inspect trackamate-backend --format='{{.State.Health.Status}}'

# View health log
docker inspect trackamate-backend --format='{{json .State.Health}}' | jq
```

### External Monitoring

Use tools like:
- **Prometheus + Grafana**: Metrics and dashboards
- **Uptime Kuma**: Simple uptime monitoring
- **Datadog**: Full observability platform

---

## Summary

### Quick Commands Reference

| Task | Command |
|------|---------|
| Start all | `docker-compose up -d` |
| Start backend only | `docker-compose up -d backend` |
| View logs | `docker-compose logs -f backend` |
| Stop all | `docker-compose down` |
| Rebuild | `docker-compose up -d --build` |
| Shell access | `docker exec -it trackamate-backend bash` |
| Database backup | `docker exec trackamate-mysql mysqldump -u root -p trackamate_prod > backup.sql` |

---

**Need Help?**
- Check logs: `docker-compose logs backend`
- Review .env configuration
- Verify database connectivity
- Check port availability: `netstat -an | findstr 5000`

---

**Last Updated**: December 2025
**Docker Version**: Compose V2
**Python Version**: 3.13
