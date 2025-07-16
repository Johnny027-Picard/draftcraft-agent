# DraftCraft Agent - Professional Freelance Proposal Generator

*Updated for Render deployment*

A production-ready Flask web application that generates professional freelance proposals using OpenAI's GPT models with comprehensive security, user management, and payment processing.

## 🚀 Features

### Core Functionality
- **AI-Powered Proposal Generation**: Uses GPT-3.5 Turbo (starter) and GPT-4 (premium)
- **User Authentication**: Secure registration, login, email verification
- **Tier System**: Starter (5 proposals/month) vs Premium (unlimited)
- **Payment Processing**: Stripe integration for premium upgrades
- **Proposal Management**: Save, view, and manage generated proposals

### Security Features
- **CSRF Protection**: Built-in CSRF token validation
- **Rate Limiting**: Configurable rate limits per user/IP
- **Input Sanitization**: XSS protection and input validation
- **Password Security**: Strong password requirements with bcrypt hashing
- **Security Headers**: Comprehensive security headers (HSTS, CSP, etc.)
- **Suspicious Activity Detection**: Automated detection and logging
- **HTTPS Enforcement**: Production HTTPS requirement

### Production Features
- **Error Tracking**: Sentry integration for error monitoring
- **Logging**: Comprehensive request and security logging
- **Database Migrations**: Flask-Migrate for schema management
- **Email System**: Async email sending with templates
- **API Endpoints**: RESTful API for proposal management
- **Responsive UI**: Mobile-friendly Bootstrap interface

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- PostgreSQL (production) or SQLite (development)
- Redis (for rate limiting and caching)
- SMTP server (Gmail, SendGrid, etc.)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd autoproposal
python -m venv venv
venv\Scripts\activate  # On Windows
source venv/bin/activate  # On Unix/Mac
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file:
```env
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-here
DATABASE_URL=postgresql://user:pass@localhost/proposifyai

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# Stripe Configuration
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PREMIUM_PRICE_ID=price_...

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Monitoring
SENTRY_DSN=https://your-sentry-dsn
```

### 4. Database Setup
```bash
# Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 5. Run the Application
```bash
# Development
python app.py

# Production (with Gunicorn)
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## 🔒 Security Considerations

### Production Security Checklist
- [ ] **Strong Secret Key**: Use a cryptographically secure random key
- [ ] **HTTPS Only**: Configure SSL/TLS certificates
- [ ] **Environment Variables**: Never commit secrets to version control
- [ ] **Database Security**: Use strong passwords and limit connections
- [ ] **Rate Limiting**: Configure appropriate limits for your use case
- [ ] **Input Validation**: All user inputs are sanitized and validated
- [ ] **Security Headers**: Comprehensive security headers enabled
- [ ] **Error Handling**: No sensitive information in error messages
- [ ] **Logging**: Security events are logged and monitored
- [ ] **Backup Strategy**: Regular database and file backups

### Security Features Implemented
- **CSRF Protection**: All forms protected against CSRF attacks
- **XSS Prevention**: Input sanitization and output encoding
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **Password Security**: bcrypt hashing with salt
- **Session Security**: Secure, HTTP-only cookies
- **Rate Limiting**: Per-user and per-IP rate limiting
- **Security Headers**: HSTS, CSP, X-Frame-Options, etc.

## 🚀 Deployment

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python -m flask db upgrade

EXPOSE 8000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
```

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd Service
```ini
[Unit]
Description=ProposifyAI
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/app
Environment=PATH=/path/to/venv/bin
ExecStart=/path/to/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

## 📊 Monitoring & Maintenance

### Health Checks
- Database connectivity
- OpenAI API availability
- Stripe webhook processing
- Email delivery status

### Logging
- Application logs: `/logs/proposifyai.log`
- Security events: Logged to Sentry
- Access logs: Nginx access logs

### Backup Strategy
```bash
# Database backup
pg_dump proposifyai > backup_$(date +%Y%m%d).sql

# File backup
tar -czf backup_$(date +%Y%m%d).tar.gz /path/to/app
```

## 🧪 Testing

### Run Tests
```bash
pytest test_app.py -v
pytest --cov=. --cov-report=html
```

### Test Coverage
- User authentication and authorization
- Proposal generation and validation
- Payment processing
- Security features
- API endpoints

## 📈 Performance Optimization

### Caching Strategy
- Redis for session storage
- Proposal content caching
- Static file caching

### Database Optimization
- Indexed queries for user lookups
- Connection pooling
- Query optimization

### CDN Integration
- Static assets served via CDN
- Image optimization
- Gzip compression

## 🔧 Configuration Options

### Rate Limiting
```python
# In config.py
RATELIMIT_DEFAULT = "200 per day;50 per hour;10 per minute"
```

### Usage Limits
```python
STARTER_MONTHLY_LIMIT = 5
PREMIUM_MONTHLY_LIMIT = 1000
```

### Security Headers
```python
SECURITY_HEADERS = {
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'SAMEORIGIN',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Content-Security-Policy': "..."
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review security advisories

---

**⚠️ Important Security Notes:**
- Never commit `.env` files or secrets to version control
- Regularly update dependencies for security patches
- Monitor logs for suspicious activity
- Use strong, unique passwords for all services
- Enable two-factor authentication where possible 