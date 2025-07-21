from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
import re
from sqlalchemy import event
from sqlalchemy.orm import validates

# Initialize SQLAlchemy in app.py
# db = SQLAlchemy(app)

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    is_premium = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), unique=True)
    reset_token = db.Column(db.String(100), unique=True)
    reset_token_expires = db.Column(db.DateTime)
    proposals_this_month = db.Column(db.Integer, default=0)
    last_reset = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    stripe_customer_id = db.Column(db.String(100), unique=True)
    subscription_id = db.Column(db.String(100), unique=True)
    subscription_status = db.Column(db.String(20), default='inactive')
    
    # Relationships
    proposals = db.relationship('Proposal', backref='user', lazy=True, cascade='all, delete-orphan')

    # Flask-Login integration
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)
    
    @validates('email')
    def validate_email(self, key, email):
        if not email:
            raise ValueError('Email is required')
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValueError('Invalid email format')
        return email.lower().strip()
    
    def set_password(self, password):
        """Set password with validation"""
        if len(password) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', password):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', password):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', password):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[^a-zA-Z0-9]', password):
            raise ValueError('Password must contain at least one special character')
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def reset_monthly_usage(self):
        """Reset monthly usage counter"""
        now = datetime.now(timezone.utc)
        if self.last_reset.month != now.month or self.last_reset.year != now.year:
            self.proposals_this_month = 0
            self.last_reset = now
            return True
        return False
    
    def can_generate_proposal(self, tier='starter'):
        """Check if user can generate a proposal"""
        self.reset_monthly_usage()
        
        if tier == 'premium' and not self.is_premium:
            return False, "Premium tier requires premium subscription"
        
        if tier == 'starter':
            limit = 5  # Starter limit
            if self.proposals_this_month >= limit:
                return False, f"Monthly limit of {limit} proposals reached"
        
        return True, "OK"
    
    def generate_verification_token(self):
        """Generate email verification token"""
        import secrets
        self.verification_token = secrets.token_urlsafe(32)
        return self.verification_token
    
    def generate_reset_token(self):
        """Generate password reset token"""
        import secrets
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        return self.reset_token
    
    def is_reset_token_valid(self):
        """Check if reset token is valid and not expired"""
        if not self.reset_token or not self.reset_token_expires:
            return False
        return datetime.now(timezone.utc) < self.reset_token_expires

class Proposal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    client_name = db.Column(db.String(200), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    skills = db.Column(db.Text, nullable=False)
    model_used = db.Column(db.String(50), nullable=False)  # 'gpt-3.5-turbo' or 'gpt-4'
    tokens_used = db.Column(db.Integer)
    cost = db.Column(db.Numeric(10, 4))  # Cost in USD
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    tier = db.Column(db.String(20), nullable=False)  # 'starter' or 'premium'
    is_favorite = db.Column(db.Boolean, default=False)
    
    @validates('client_name', 'job_description', 'skills')
    def validate_inputs(self, key, value):
        if not value or not value.strip():
            raise ValueError(f'{key.replace("_", " ").title()} is required')
        if len(value) > 10000:  # Reasonable limit
            raise ValueError(f'{key.replace("_", " ").title()} is too long')
        return value.strip()
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'client_name': self.client_name,
            'content': self.content,
            'model_used': self.model_used,
            'created_at': self.created_at.isoformat(),
            'tier': self.tier,
            'is_favorite': self.is_favorite
        }

class LoginHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(256))

# Event listeners for automatic actions
@event.listens_for(User, 'before_insert')
def set_user_defaults(mapper, connection, target):
    """Set default values for new users"""
    if not target.created_at:
        target.created_at = datetime.now(timezone.utc)

@event.listens_for(Proposal, 'before_insert')
def set_proposal_defaults(mapper, connection, target):
    """Set default values for new proposals"""
    if not target.created_at:
        target.created_at = datetime.now(timezone.utc) 