import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from threading import Thread

class EmailSender:
    @staticmethod
    def send(to_email, subject, html_content, plain_content=None):
        """
        Sends an email using SendGrid.
        Args:
            to_email (str): Recipient's email address.
            subject (str): Email subject.
            html_content (str): HTML content of the email.
            plain_content (str, optional): Plain text fallback content.
        Returns:
            int: Status code of the SendGrid response if successful.
        """
        api_key = os.getenv('SENDGRID_API_KEY')
        if not api_key:
            logging.error("SENDGRID_API_KEY environment variable not set.")
            return None
        message = Mail(
            from_email='noreply@draftcraftagent.com',
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
            plain_text_content=plain_content or ''
        )
        try:
            sg = SendGridAPIClient(api_key)
            response = sg.send(message)
            logging.info(f"Email sent to {to_email} with subject '{subject}' (status {response.status_code})")
            return response.status_code
        except Exception as e:
            logging.warning(f"Error sending email to {to_email}: {e}")
            return None

    @staticmethod
    def send_password_reset_email(to_email, reset_link):
        """
        Sends a password reset email with both HTML and plain-text content.
        Args:
            to_email (str): Recipient's email address.
            reset_link (str): Password reset link.
        Returns:
            int: Status code of the SendGrid response if successful.
        """
        subject = "Reset your DraftCraft Password"
        html_content = f"""
        <div style='font-family:sans-serif;max-width:600px;margin:auto;'>
            <h2 style='color:#2d7ff9;'>DraftCraft Password Reset</h2>
            <p>Hello,</p>
            <p>We received a request to reset your DraftCraft password. Click the button below to securely reset your password:</p>
            <p style='text-align:center;margin:2em 0;'>
                <a href='{reset_link}' style='background:#2d7ff9;color:#fff;padding:12px 28px;border-radius:5px;text-decoration:none;font-weight:bold;'>Reset Password</a>
            </p>
            <p>If you did not request this, you can safely ignore this email.</p>
            <hr style='margin:2em 0;'>
            <p style='font-size:12px;color:#888;'>This link will expire in 1 hour for your security.</p>
            <p style='font-size:12px;color:#888;'>If you have any questions, contact support@draftcraftagent.com</p>
        </div>
        """
        plain_content = f"""
DraftCraft Password Reset\n\nWe received a request to reset your DraftCraft password.\n\nReset your password: {reset_link}\n\nIf you did not request this, you can safely ignore this email.\n\nThis link will expire in 1 hour for your security.\nIf you have any questions, contact support@draftcraftagent.com
        """
        return EmailSender.send(to_email, subject, html_content, plain_content)

    @staticmethod
    def send_welcome_email(to_email):
        """
        Sends a welcome email to a new user with both HTML and plain-text content.
        Args:
            to_email (str): Recipient's email address.
        Returns:
            int: Status code of the SendGrid response if successful.
        """
        subject = "Welcome to DraftCraft"
        html_content = f"""
        <div style='font-family:sans-serif;max-width:600px;margin:auto;'>
            <h2 style='color:#2d7ff9;'>Welcome to DraftCraft!</h2>
            <p>Thank you for joining <b>DraftCraft</b>, your AI-powered freelance proposal generator.</p>
            <p>With the <b>Free Tier</b>, you can generate up to 5 professional proposals per month using our advanced AI. Simply log in, fill out the proposal form, and let DraftCraft do the rest!</p>
            <p>Want unlimited proposals, priority support, and access to the latest AI models? <a href='https://draftcraftagent.com/pricing' style='color:#2d7ff9;text-decoration:underline;'>Explore Premium Features</a> and upgrade anytime from your dashboard.</p>
            <hr style='margin:2em 0;'>
            <p style='font-size:12px;color:#888;'>If you have any questions, reply to this email or contact support@draftcraftagent.com</p>
        </div>
        """
        plain_content = (
            "Welcome to DraftCraft!\n\n"
            "Thank you for joining DraftCraft, your AI-powered freelance proposal generator.\n\n"
            "With the Free Tier, you can generate up to 5 professional proposals per month using our advanced AI. Log in, fill out the proposal form, and let DraftCraft do the rest!\n\n"
            "Want unlimited proposals, priority support, and access to the latest AI models? Explore Premium Features at https://draftcraftagent.com/pricing and upgrade anytime from your dashboard.\n\n"
            "If you have any questions, contact support@draftcraftagent.com"
        )
        return EmailSender.send(to_email, subject, html_content, plain_content) 