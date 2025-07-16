import os
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///proposifyai.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # Rate limiting
    RATELIMIT_DEFAULT = "200 per day;50 per hour;10 per minute"
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or "memory://"
    
    # Email settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Stripe settings
    STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
    STRIPE_PREMIUM_PRICE_ID = os.environ.get('STRIPE_PREMIUM_PRICE_ID')
    
    # OpenAI settings
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Security headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' https://js.stripe.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https:; connect-src 'self' https://api.openai.com https://api.stripe.com;"
    }
    
    # Usage limits
    STARTER_MONTHLY_LIMIT = 5
    PREMIUM_MONTHLY_LIMIT = 1000
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Sentry
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    
    # Redis for caching and sessions
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Domain settings
    DOMAIN = os.environ.get('DOMAIN', 'draftcraftagent.com')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SECURITY_HEADERS = {}

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
    @classmethod
    def init_app(cls, app):
        # Ensure HTTPS in production
        if not app.debug and not app.testing:
            import logging
            from logging.handlers import RotatingFileHandler
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = RotatingFileHandler('logs/proposifyai.log', maxBytes=10240, backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            app.logger.setLevel(logging.INFO)
            app.logger.info('ProposifyAI startup')

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_openai_api_key():
    """Get OpenAI API key with validation"""
    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        raise ValueError('OPENAI_API_KEY not found in environment variables. Please set it in your .env file.')
    return key

def get_config():
    """Get configuration based on environment"""
    config_name = os.environ.get('FLASK_ENV', 'default')
    return config.get(config_name, config['default'])
