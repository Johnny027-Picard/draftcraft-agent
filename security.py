"""
Security middleware and utilities for DraftCraft Agent
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

def sanitize_input(text):
    """Sanitize user input to prevent XSS"""
    if not text:
        return ""
    
    # Remove potentially dangerous HTML tags
    allowed_tags = ['b', 'i', 'em', 'strong', 'p', 'br']
    allowed_attributes = {}
    
    cleaned = bleach.clean(
        text,
        tags=allowed_tags,
        attributes=allowed_attributes,
        strip=True
    )
    
    # Additional sanitization
    cleaned = html.escape(cleaned)
    return cleaned.strip()

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    return True, "Password is strong"

def rate_limit_by_user(f):
    """Decorator to rate limit by user ID"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if hasattr(g, 'user') and g.user:
            # Custom rate limiting for authenticated users
            user_id = g.user.id
            # Implementation would go here with Redis
            pass
        return f(*args, **kwargs)
    return decorated_function

def require_https(f):
    """Decorator to require HTTPS in production"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_app.debug and not request.is_secure:
            abort(400, description="HTTPS required")
        return f(*args, **kwargs)
    return decorated_function

def validate_json_schema(schema):
    """Decorator to validate JSON request schema"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                abort(400, description="JSON required")
            
            data = request.get_json()
            if not data:
                abort(400, description="Invalid JSON")
            
            # Basic schema validation
            for field in schema.get('required', []):
                if field not in data:
                    abort(400, description=f"Missing required field: {field}")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_security_event(event_type, user_id=None, details=None):
    """Log security events"""
    current_app.logger.warning(
        f"Security Event: {event_type} - User: {user_id} - Details: {details}"
    )

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

class SecurityMiddleware:
    """Security middleware for additional protection"""
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        # Check for suspicious headers
        if 'HTTP_X_FORWARDED_FOR' in environ:
            # Log proxy usage
            current_app.logger.info(f"Request via proxy: {environ['HTTP_X_FORWARDED_FOR']}")
        
        # Block requests with suspicious user agents
        user_agent = environ.get('HTTP_USER_AGENT', '')
        if self._is_suspicious_user_agent(user_agent):
            return self._block_request(start_response)
        
        return self.app(environ, start_response)
    
    def _is_suspicious_user_agent(self, user_agent):
        """Check for suspicious user agents"""
        suspicious_agents = [
            'bot', 'crawler', 'spider', 'scraper',
            'curl', 'wget', 'python-requests'
        ]
        
        user_agent_lower = user_agent.lower()
        return any(agent in user_agent_lower for agent in suspicious_agents)
    
    def _block_request(self, start_response):
        """Block suspicious requests"""
        status = '403 Forbidden'
        response_headers = [('Content-Type', 'text/plain')]
        start_response(status, response_headers)
        return [b'Access denied'] 