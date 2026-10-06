import os
import smtplib
from email.message import EmailMessage

EMAIL_FROM = os.environ.get("QCC_EMAIL_FROM")
EMAIL_PASSWORD = os.environ.get("QCC_EMAIL_PASSWORD")
EMAIL_TO = os.environ.get("QCC_EMAIL_TO")

msg = EmailMessage()
msg["Subject"] = "QCC Monitor - Gmail Test"
msg["From"] = EMAIL_FROM
msg["To"] = EMAIL_TO
msg.set_content(
    "This is a test message from your QCC Volume Monitor.\n\n"
    "If you received this email, Gmail SMTP is connected successfully."
)

try:
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)

    print("✅ Gmail connection successful!")
    print("📧 Test email sent to:", EMAIL_TO)

except Exception as e:
    print("❌ Gmail connection failed:")
    print(e)