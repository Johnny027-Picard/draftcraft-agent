"""
Email utilities for DraftCraft Agent
"""
from flask import current_app, render_template, url_for
from flask_mail import Mail, Message
from threading import Thread
import logging

mail = Mail()

def send_async_email(app, msg):
    """Send email asynchronously"""
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            current_app.logger.error(f"Failed to send email: {e}")

def send_email(subject, recipients, template, **kwargs):
    """Send email using template"""
    try:
        msg = Message(
            subject=subject,
            recipients=recipients,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        # Render both HTML and text versions
        msg.html = render_template(f'emails/{template}.html', **kwargs)
        msg.body = render_template(f'emails/{template}.txt', **kwargs)
        
        # Send asynchronously
        Thread(
            target=send_async_email,
            args=(current_app._get_current_object(), msg)
        ).start()
        
        current_app.logger.info(f"Email sent to {recipients}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {e}")
        return False

def send_verification_email(user):
    """Send email verification email"""
    token = user.generate_verification_token()
    verify_url = url_for('verify_email', token=token, _external=True)
    
    return send_email(
        subject="Verify your DraftCraft Agent account",
        recipients=[user.email],
        template='verify_email',
        user=user,
        verify_url=verify_url
    )

def send_password_reset_email(user):
    """Send password reset email"""
    token = user.generate_reset_token()
    reset_url = url_for('reset_password', token=token, _external=True)
    
    return send_email(
        subject="Reset your DraftCraft Agent password",
        recipients=[user.email],
        template='reset_password',
        user=user,
        reset_url=reset_url
    )

def send_welcome_email(user):
    """Send welcome email to new users"""
    return send_email(
        subject="Welcome to DraftCraft Agent!",
        recipients=[user.email],
        template='welcome',
        user=user
    )

def send_upgrade_confirmation_email(user):
    """Send confirmation email for premium upgrade"""
    return send_email(
        subject="Welcome to DraftCraft Agent Premium!",
        recipients=[user.email],
        template='upgrade_confirmation',
        user=user
    )

def send_usage_alert_email(user, usage_percentage):
    """Send usage alert email"""
    return send_email(
        subject=f"DraftCraft Agent Usage Alert - {usage_percentage}% used",
        recipients=[user.email],
        template='usage_alert',
        user=user,
        usage_percentage=usage_percentage
    )

def send_monthly_report_email(user, stats):
    """Send monthly usage report"""
    return send_email(
        subject="Your DraftCraft Agent Monthly Report",
        recipients=[user.email],
        template='monthly_report',
        user=user,
        stats=stats
    ) 