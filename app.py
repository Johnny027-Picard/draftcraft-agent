"""
DraftCraft Agent - Production-ready Flask application
"""
import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, g
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from flask_mail import Mail
import stripe
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

# Import our modules
from config import get_config, get_openai_api_key
from models import db, User, Proposal
from security import init_security, sanitize_input, validate_email, validate_password, limiter, get_remote_address
from email_utils import mail, send_verification_email, send_welcome_email, send_password_reset_email
from gpt_utils import generate_proposal
from email_sender import EmailSender

# Initialize Sentry for error tracking
sentry_dsn = os.environ.get('SENTRY_DSN')
if sentry_dsn and '@' in sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.1,
        environment=os.environ.get('FLASK_ENV', 'development')
    )

def create_app(config_object=None):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    if config_object is not None:
        app.config.from_object(config_object)
    else:
        config_name = os.environ.get('FLASK_ENV', 'default')
    app.config.from_object(get_config())
    
    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)
    migrate = Migrate(app, db)
    
    # Initialize security
    init_security(app)
    
    # Initialize login manager
    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # Register blueprints and routes
    register_routes(app)
    
    # Initialize Stripe
    stripe.api_key = app.config.get('STRIPE_SECRET_KEY')
    
    # Production-specific setup
    if app.config.get('ENV') == 'production':
        get_config().init_app(app)
    
    return app

def register_routes(app):
    """Register all application routes"""
    
    @app.route('/')
    def index():
        """Landing page"""
        return render_template('index.html')
    
    @app.route('/form')
    @login_required
    def form():
        """Proposal generation form"""
        return render_template('form.html')
    
    @app.route('/generate', methods=['POST'])
    @login_required
    def generate():
        """Generate proposal with enhanced security"""
        try:
            # Sanitize and validate input
            client_name = sanitize_input(request.form.get('client_name', '').strip())
            job_description = sanitize_input(request.form.get('job_description', '').strip())
            skills = sanitize_input(request.form.get('skills', '').strip())
            tier = request.form.get('tier', 'starter')
            
            # Validate required fields
            if not all([client_name, job_description, skills]):
                flash('All fields are required.', 'error')
                return redirect(url_for('form'))
            
            # Check for suspicious activity
            from security import check_suspicious_activity
            is_suspicious, reason = check_suspicious_activity(request.form)
            if is_suspicious:
                log_security_event('suspicious_activity', current_user.id, reason)
                flash('Invalid input detected.', 'error')
                return redirect(url_for('form'))
            
            # Check user permissions and limits
            can_generate, message = current_user.can_generate_proposal(tier)
            if not can_generate:
                flash(message, 'error')
                return redirect(url_for('form'))
            
            # Generate proposal
            model = 'gpt-4' if tier == 'premium' else 'gpt-3.5-turbo'
            proposal_text = generate_proposal(client_name, job_description, skills, model)
            
            # Save proposal to database
            proposal = Proposal(
                user_id=current_user.id,
                content=proposal_text,
                client_name=client_name,
                job_description=job_description,
                skills=skills,
                model_used=model,
                tier=tier
            )
            
            db.session.add(proposal)
            
            # Update user usage
            if tier == 'starter':
                current_user.proposals_this_month += 1
            
            db.session.commit()
            
            # Log successful generation
            app.logger.info(f"Proposal generated for user {current_user.id} using {model}")
            
            return render_template('result.html', proposal=proposal_text, proposal_id=proposal.id)
            
        except Exception as e:
            app.logger.error(f"Error generating proposal: {e}")
            flash('An error occurred while generating your proposal. Please try again.', 'error')
            return redirect(url_for('form'))
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration with enhanced validation"""
        if current_user.is_authenticated:
            return redirect(url_for('form'))
        
        if request.method == 'POST':
            try:
                email = request.form['email'].strip().lower()
                password = request.form['password']
                confirm_password = request.form['confirm_password']
                
                # Validate input
                if not all([email, password, confirm_password]):
                    flash('All fields are required.', 'error')
                    return render_template('register.html')
                
                if not validate_email(email):
                    flash('Please enter a valid email address.', 'error')
                    return render_template('register.html')
                
                is_valid, message = validate_password(password)
                if not is_valid:
                    flash(message, 'error')
                    return render_template('register.html')
                
                if password != confirm_password:
                    flash('Passwords do not match.', 'error')
                    return render_template('register.html')
                
                # Check if user already exists
                if User.query.filter_by(email=email).first():
                    flash('Email already registered.', 'error')
                    return render_template('register.html')
                
                # Create new user
                user = User(email=email)
                user.set_password(password)
                
                db.session.add(user)
                db.session.commit()
                
                # Send verification email (keep as is)
                send_verification_email(user)
                
                # Send welcome email asynchronously, log but do not break flow
                from threading import Thread
                def send_welcome():
                    try:
                        EmailSender.send_welcome_email(user.email)
                    except Exception as e:
                        app.logger.warning(f"Failed to send welcome email: {e}")
                Thread(target=send_welcome).start()
                
                flash('Account created! Please check your email to verify your account.', 'success')
                return redirect(url_for('login'))
                
            except ValueError as e:
                flash(str(e), 'error')
                return render_template('register.html')
            except Exception as e:
                app.logger.error(f"Registration error: {e}")
                flash('An error occurred during registration. Please try again.', 'error')
                return render_template('register.html')
        
        return render_template('register.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    @limiter.limit("5 per minute", key_func=get_remote_address)
    def login():
        """User login with security logging"""
        if current_user.is_authenticated:
            return redirect(url_for('form'))
        
        if request.method == 'POST':
            email = request.form['email'].strip().lower()
            password = request.form['password']
            
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password):
                if not user.is_active:
                    flash('Account is deactivated. Please contact support.', 'error')
                    return render_template('login.html')
                
                login_user(user, remember=True)
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                app.logger.info(f"User {user.id} logged in successfully")
                flash('Logged in successfully.', 'success')
                return redirect(url_for('form'))
            else:
                # log_security_event('failed_login', None, f"Failed login attempt for {email}")
                flash('Invalid email or password.', 'error')
        
        return render_template('login.html')
    
    @app.route('/logout')
    @login_required
    def logout():
        """User logout"""
        app.logger.info(f"User {current_user.id} logged out")
        logout_user()
        flash('You have been logged out.', 'success')
        return redirect(url_for('login'))
    
    @app.route('/verify-email/<token>')
    def verify_email(token):
        """Email verification"""
        user = User.query.filter_by(verification_token=token).first()
        
        if user and not user.is_verified:
            user.is_verified = True
            user.verification_token = None
            db.session.commit()
            flash('Email verified successfully!', 'success')
        else:
            flash('Invalid or expired verification link.', 'error')
        
        return redirect(url_for('login'))
    
    @app.route('/forgot-password', methods=['GET', 'POST'])
    def forgot_password():
        """Password reset request"""
        if request.method == 'POST':
            email = request.form['email'].strip().lower()
            user = User.query.filter_by(email=email).first()
            
            if user:
                # Send password reset email asynchronously, log but do not break flow
                from threading import Thread
                def send_reset():
                    try:
                        reset_link = url_for('reset_password', token=user.generate_reset_token(), _external=True)
                        db.session.commit()  # Save token
                        EmailSender.send_password_reset_email(user.email, reset_link)
                    except Exception as e:
                        app.logger.warning(f"Failed to send password reset email: {e}")
                Thread(target=send_reset).start()
                flash('Password reset instructions sent to your email.', 'success')
            else:
                # Don't reveal if email exists
                flash('If an account with that email exists, reset instructions have been sent.', 'info')
            
            return redirect(url_for('login'))
        
        return render_template('forgot_password.html')
    
    @app.route('/reset-password/<token>', methods=['GET', 'POST'])
    def reset_password(token):
        """Password reset"""
        user = User.query.filter_by(reset_token=token).first()
        
        if not user or not user.is_reset_token_valid():
            flash('Invalid or expired reset link.', 'error')
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            
            is_valid, message = validate_password(password)
            if not is_valid:
                flash(message, 'error')
                return render_template('reset_password.html')
            
            if password != confirm_password:
                flash('Passwords do not match.', 'error')
                return render_template('reset_password.html')
            
            user.set_password(password)
            user.reset_token = None
            user.reset_token_expires = None
            db.session.commit()
            
            flash('Password reset successfully!', 'success')
            return redirect(url_for('login'))
        
        return render_template('reset_password.html')
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """User dashboard"""
        proposals = Proposal.query.filter_by(user_id=current_user.id).order_by(Proposal.created_at.desc()).limit(10).all()
        
        # Calculate usage statistics
        current_user.reset_monthly_usage()
        usage_percentage = (current_user.proposals_this_month / 5) * 100 if not current_user.is_premium else 0
        
        return render_template('dashboard.html', 
                             proposals=proposals, 
                             usage_percentage=usage_percentage,
                             usage=current_user.proposals_this_month,
                             is_premium=current_user.is_premium)
    
    @app.route('/pricing')
    def pricing():
        """Pricing page"""
        return render_template('pricing.html', 
                             stripe_public_key=app.config.get('STRIPE_PUBLIC_KEY'))
    
    @app.route('/create-checkout-session', methods=['POST'])
    @login_required
    def create_checkout_session():
        """Create Stripe checkout session"""
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': app.config.get('STRIPE_PREMIUM_PRICE_ID'),
                    'quantity': 1,
                }],
                mode='subscription',
                customer_email=current_user.email,
                success_url=url_for('dashboard', _external=True) + '?upgraded=1',
                cancel_url=url_for('pricing', _external=True),
                metadata={'user_id': current_user.id}
            )
            return jsonify({'id': session.id})
        except Exception as e:
            app.logger.error(f"Stripe checkout error: {e}")
            return jsonify({'error': 'Payment session creation failed'}), 500
    
    @app.route('/stripe/webhook', methods=['POST'])
    def stripe_webhook():
        """Handle Stripe webhooks"""
        payload = request.data
        sig_header = request.headers.get('stripe-signature')
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, app.config.get('STRIPE_WEBHOOK_SECRET')
            )
        except Exception as e:
            app.logger.error(f"Stripe webhook error: {e}")
            return '', 400
        
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = session['metadata'].get('user_id')
            user = User.query.get(int(user_id))
            
            if user:
                user.is_premium = True
                user.stripe_customer_id = session.get('customer')
                user.subscription_id = session.get('subscription')
                user.subscription_status = 'active'
                db.session.commit()
                
                app.logger.info(f"User {user.id} upgraded to premium")
        
        return '', 200
    
    @app.route('/api/proposals')
    @login_required
    @limiter.limit("30 per minute")
    def api_proposals():
        """API endpoint for user proposals"""
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 50)
        
        proposals = Proposal.query.filter_by(user_id=current_user.id)\
            .order_by(Proposal.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'proposals': [proposal.to_dict() for proposal in proposals.items],
            'total': proposals.total,
            'pages': proposals.pages,
            'current_page': page
        })
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html', error=error), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html', error=error), 500

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=app.config.get('DEBUG', False))
