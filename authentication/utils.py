import random
import string
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import OTPCode


def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))


def send_otp_email(email, otp_code, purpose='Email Verification'):
    subject = f'Fitness App - {purpose} Code'
    message = (
        f'Hi there!\n\n'
        f'Your verification code is: {otp_code}\n\n'
        f'This code will expire in 10 minutes.\n\n'
        f"If you didn't request this code, please ignore this email.\n\n"
        f'- Fitness App Team'
    )
    html_message = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 30px; background: #f9fafb; border-radius: 16px;">
        <div style="background: #0d9488; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 24px;">
            <h1 style="color: white; margin: 0; font-size: 24px;">Fitness App</h1>
        </div>
        <h2 style="color: #111827; text-align: center;">{purpose}</h2>
        <p style="color: #6b7280; text-align: center;">Your verification code is:</p>
        <div style="background: #f0fdfa; border: 2px solid #0d9488; border-radius: 12px; padding: 20px; text-align: center; margin: 20px 0;">
            <span style="font-size: 36px; font-weight: bold; color: #0d9488; letter-spacing: 8px;">{otp_code}</span>
        </div>
        <p style="color: #9ca3af; text-align: center; font-size: 14px;">
            This code expires in <strong>10 minutes</strong>.
        </p>
    </div>
    """

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER or 'noreply@fitness.local',
        recipient_list=[email],
        html_message=html_message,
        fail_silently=False,
    )


def create_and_send_otp(email, purpose='Email Verification'):
    OTPCode.objects.filter(email=email, is_used=False).update(is_used=True)
    code = generate_otp(6)
    otp = OTPCode.objects.create(
        email=email,
        code=code,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    send_otp_email(email, code, purpose=purpose)
    return otp
