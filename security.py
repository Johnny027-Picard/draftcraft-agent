"""
Security middleware and utilities for DraftCraft Agent

# Security scanning: Run `bandit -r .` regularly to check for vulnerabilities.
"""
import re
import html
from functools import wraps
from flask import request, abort, current_app, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
import bleach
import secrets

# Initialize Flask extensions
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

csrf = CSRFProtect()

def init_security(app):
    """Initialize security extensions"""
    limiter.init_app(app)
    csrf.init_app(app)
    
    # Add security headers middleware
    @app.after_request
    def add_security_headers(response):
        if hasattr(current_app.config, 'SECURITY_HEADERS'):
            for header, value in current_app.config.SECURITY_HEADERS.items():
                response.headers[header] = value
        return response
    
    # Add request logging
    @app.before_request
    def log_request():
        if not request.endpoint:
            return
        
        g.request_id = secrets.token_hex(8)
        current_app.logger.info(
            f"Request {g.request_id}: {request.method} {request.path} "
            f"from {request.remote_addr}"
        )

def sanitize_input(value):
    """Sanitize user input to prevent XSS"""
    if not value:
        return value
    return bleach.clean(value, tags=[], attributes={}, protocols=[], strip=True)

def validate_email(email):
    """Validate email format"""
    if not email:
        return False, 'Email is required'
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return False, 'Invalid email format'
    return True, ''

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, 'Password must be at least 8 characters long'
    if not re.search(r'[A-Z]', password):
        return False, 'Password must contain at least one uppercase letter'
    if not re.search(r'[a-z]', password):
        return False, 'Password must contain at least one lowercase letter'
    if not re.search(r'\d', password):
        return False, 'Password must contain at least one number'
    if not re.search(r'[^a-zA-Z0-9]', password):
        return False, 'Password must contain at least one special character'
    return True, ''

def check_suspicious_activity(request_data):
    """Check for suspicious activity patterns"""
    suspicious_patterns = [
        r'<script',
        r'javascript:',
        r'data:text/html',
        r'vbscript:',
        r'onload=',
        r'onerror=',
        r'<iframe',
        r'<object',
        r'<embed'
    ]
    
    data_str = str(request_data).lower()
    for pattern in suspicious_patterns:
        if re.search(pattern, data_str):
            return True, f"Suspicious pattern detected: {pattern}"
    
    return False, None 