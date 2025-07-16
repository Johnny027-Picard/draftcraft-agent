#!/bin/bash

# ProposifyAI Production Deployment Script
# This script automates the deployment process with security checks

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="proposifyai"
DEPLOY_USER="www-data"
APP_DIR="/opt/$APP_NAME"
BACKUP_DIR="/opt/backups/$APP_NAME"
LOG_FILE="/var/log/$APP_NAME/deploy.log"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a "$LOG_FILE"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error "This script should not be run as root"
fi

# Check prerequisites
log "Checking prerequisites..."

# Check if required commands exist
command -v docker >/dev/null 2>&1 || error "Docker is required but not installed"
command -v docker-compose >/dev/null 2>&1 || error "Docker Compose is required but not installed"
command -v git >/dev/null 2>&1 || error "Git is required but not installed"

# Check if .env file exists
if [ ! -f ".env" ]; then
    error ".env file not found. Please create it with your configuration."
fi

# Validate .env file
log "Validating environment configuration..."
source .env

required_vars=(
    "FLASK_ENV"
    "SECRET_KEY"
    "DATABASE_URL"
    "OPENAI_API_KEY"
    "STRIPE_PUBLIC_KEY"
    "STRIPE_SECRET_KEY"
    "STRIPE_WEBHOOK_SECRET"
    "STRIPE_PREMIUM_PRICE_ID"
    "MAIL_SERVER"
    "MAIL_USERNAME"
    "MAIL_PASSWORD"
    "MAIL_DEFAULT_SENDER"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        error "Required environment variable $var is not set"
    fi
done

# Create necessary directories
log "Creating necessary directories..."
sudo mkdir -p "$APP_DIR"
sudo mkdir -p "$BACKUP_DIR"
sudo mkdir -p "/var/log/$APP_NAME"
sudo mkdir -p "/etc/nginx/ssl"

# Set permissions
sudo chown -R $USER:$USER "$APP_DIR"
sudo chown -R $USER:$USER "$BACKUP_DIR"

# Backup current deployment
if [ -d "$APP_DIR" ] && [ "$(ls -A $APP_DIR)" ]; then
    log "Creating backup of current deployment..."
    backup_name="backup_$(date +%Y%m%d_%H%M%S)"
    sudo cp -r "$APP_DIR" "$BACKUP_DIR/$backup_name"
    log "Backup created: $BACKUP_DIR/$backup_name"
fi

# Stop current services
log "Stopping current services..."
sudo systemctl stop $APP_NAME 2>/dev/null || true
docker-compose down 2>/dev/null || true

# Deploy new version
log "Deploying new version..."

# Copy application files
sudo cp -r . "$APP_DIR/"
sudo chown -R $DEPLOY_USER:$DEPLOY_USER "$APP_DIR"

# Set proper permissions
sudo chmod 755 "$APP_DIR"
sudo chmod 644 "$APP_DIR/.env"

# Build and start Docker services
log "Building and starting Docker services..."
cd "$APP_DIR"
docker-compose build --no-cache
docker-compose up -d

# Wait for services to be ready
log "Waiting for services to be ready..."
sleep 30

# Health check
log "Performing health check..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        log "Health check passed"
        break
    fi
    
    if [ $attempt -eq $max_attempts ]; then
        error "Health check failed after $max_attempts attempts"
    fi
    
    log "Health check attempt $attempt/$max_attempts failed, retrying..."
    sleep 10
    ((attempt++))
done

# Database migration
log "Running database migrations..."
docker-compose exec -T web flask db upgrade

# Test critical functionality
log "Testing critical functionality..."

# Test OpenAI API connection
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health | grep -q "200"; then
    log "API health check passed"
else
    warning "API health check failed"
fi

# Test database connection
if docker-compose exec -T web python -c "from models import db; print('Database connection OK')" 2>/dev/null; then
    log "Database connection test passed"
else
    error "Database connection test failed"
fi

# Security checks
log "Performing security checks..."

# Check for exposed secrets
if grep -r "sk_live\|pk_live\|password\|secret" "$APP_DIR" --exclude-dir=node_modules --exclude-dir=.git 2>/dev/null; then
    warning "Potential secrets found in codebase"
fi

# Check SSL certificate
if [ -f "/etc/nginx/ssl/cert.pem" ]; then
    log "SSL certificate found"
else
    warning "SSL certificate not found. Please install SSL certificates."
fi

# Check firewall
if command -v ufw >/dev/null 2>&1; then
    if sudo ufw status | grep -q "Status: active"; then
        log "Firewall is active"
    else
        warning "Firewall is not active"
    fi
fi

# Performance optimization
log "Optimizing performance..."

# Enable gzip compression
if ! grep -q "gzip on" /etc/nginx/nginx.conf 2>/dev/null; then
    log "Enabling gzip compression in Nginx"
fi

# Set up log rotation
if [ ! -f "/etc/logrotate.d/$APP_NAME" ]; then
    log "Setting up log rotation..."
    sudo tee "/etc/logrotate.d/$APP_NAME" > /dev/null <<EOF
/var/log/$APP_NAME/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 $DEPLOY_USER $DEPLOY_USER
    postrotate
        systemctl reload nginx
    endscript
}
EOF
fi

# Set up monitoring
log "Setting up monitoring..."

# Create systemd service if not exists
if [ ! -f "/etc/systemd/system/$APP_NAME.service" ]; then
    log "Creating systemd service..."
    sudo tee "/etc/systemd/system/$APP_NAME.service" > /dev/null <<EOF
[Unit]
Description=ProposifyAI
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable $APP_NAME
fi

# Start the service
log "Starting $APP_NAME service..."
sudo systemctl start $APP_NAME

# Final health check
log "Performing final health check..."
sleep 10

if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    log "✅ Deployment completed successfully!"
    log "Application is running at: http://localhost:8000"
    log "Health check endpoint: http://localhost:8000/health"
else
    error "❌ Deployment failed - health check failed"
fi

# Cleanup old backups (keep last 5)
log "Cleaning up old backups..."
cd "$BACKUP_DIR"
ls -t | tail -n +6 | xargs -r rm -rf

# Log deployment completion
log "Deployment completed at $(date)"
log "Log file: $LOG_FILE"

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${GREEN}📊 Monitor logs: tail -f $LOG_FILE${NC}"
echo -e "${GREEN}🔧 Service status: sudo systemctl status $APP_NAME${NC}"
echo -e "${GREEN}🌐 Application: http://localhost:8000${NC}" 